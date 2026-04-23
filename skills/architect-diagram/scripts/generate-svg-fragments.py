#!/usr/bin/env python3
"""Generate generic SVG fragments from architecture artifacts.

Creates per-view SVG fragments under <output-root>/architecture/.out/diagram-svg
so the renderer can run in rich/demo mode without falling back to the
in-template layout path.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import yaml


RUNTIME_DIR = ".out"


@dataclass(frozen=True)
class Node:
    id: str
    name: str
    kind: str
    technology: str
    description: str
    responsibility: str
    external: bool
    parent_id: str | None
    synthetic: bool = False


@dataclass(frozen=True)
class Edge:
    id: str
    source_id: str
    target_id: str
    label: str


@dataclass
class Box:
    x: float
    y: float
    w: float
    h: float


@dataclass
class Boundary:
    x: float
    y: float
    w: float
    h: float
    label: str
    tone: str = "system"


@dataclass
class LayoutResult:
    width: float
    height: float
    boxes: Dict[str, Box]
    boundaries: List[Boundary]


VIEW_MARGIN_X = 64.0
VIEW_MARGIN_Y = 56.0
COMPACT_VIEW_MARGIN_X = 24.0
WIDE_LAYOUT_WIDTH_THRESHOLD = 1200.0
COLUMN_GAP = 68.0
ROW_GAP = 34.0
BOUNDARY_PAD = 28.0
CARD_MIN_W = 180.0
CARD_MAX_W = 320.0
NODE_HEADER_BAND_H = 19.0
NODE_HEADER_TEXT_NUDGE_Y = 0.75
EDGE_EGRESS_STUB = 18.0
ROUTING_EPSILON = 0.25
PORT_SLOT_INSET = 18.0
ROUTE_CLEARANCE = 12.0
ROUTE_GUTTER = 22.0
ROUTE_CLEARANCE_TARGET = 24.0
ROUTE_BUNDLE_SPACING = 10.0
ROUTE_BUNDLE_VARIANT_COUNT = 4
FRAGMENT_ROUTING_VERSION = "2"


def load_yaml(path: Path) -> Dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def validate_artifact_contract(output_root: Path) -> None:
    validator = Path(__file__).with_name("validate-feedback-update.py")
    if not validator.exists():
        raise SystemExit(f"Missing contract validator: {validator}")

    result = subprocess.run(
        [sys.executable, str(validator), "--output-root", str(output_root)],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return

    details = (result.stdout or "").strip()
    if not details:
        details = (result.stderr or "").strip()
    raise SystemExit(
        "Architecture artifacts failed contract validation before SVG generation.\n"
        f"{details or 'No validator output captured.'}"
    )


def compute_revision_id(output_root: Path) -> str:
    arch = output_root / "architecture"
    parts: List[bytes] = []
    views_dir = arch / "views"
    view_files = sorted(
        [path for path in views_dir.rglob("*") if path.is_file() and path.suffix in {".yaml", ".yml"}],
        key=lambda path: path.relative_to(arch).as_posix(),
    )
    for path in view_files:
        parts.append(path.relative_to(arch).as_posix().encode("utf-8"))
        parts.append(path.read_bytes())
    for name in ("manifest.yaml", "model.yaml", "summary.md", "diff.yaml"):
        path = arch / name
        if path.exists():
            parts.append(name.encode("utf-8"))
            parts.append(path.read_bytes())
    digest = hashlib.sha1(b"\n".join(parts)).hexdigest()[:12]
    return f"rev-{digest}"


def esc(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def normalize_kind(value: str) -> str:
    return str(value or "").strip().lower()


def is_system_like_kind(value: str) -> bool:
    return normalize_kind(value) in {"software_system", "system"}


def normalize_view_type(value: str) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def short_text(text: str, max_len: int = 38) -> str:
    cleaned = " ".join(str(text or "").replace("\n", " ").split())
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 1] + "…"


def wrap_text(text: str, max_chars: int, max_lines: int) -> List[str]:
    words = str(text or "").split()
    if not words:
        return []

    lines: List[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
            continue
        lines.append(current)
        current = word
        if len(lines) == max_lines - 1:
            break
    lines.append(current)

    remaining = words[len(" ".join(lines).split()) :]
    if remaining:
        last = lines[-1]
        lines[-1] = short_text(f"{last} {' '.join(remaining)}", max_chars)

    return lines[:max_lines]


def approx_text_width(text: str, font_size: float) -> float:
    return len(text) * font_size * 0.58


def type_header(kind: str, technology: str) -> str:
    k = normalize_kind(kind)

    if k == "person":
        return "Person"
    if k == "external_system":
        return "External System"
    if k in {"software_system", "system"}:
        return "Software System"
    if k == "component":
        return "Component"
    if k == "deployment_node":
        return "Deployment Node"
    if k == "database":
        return "Database"
    if k == "queue":
        return "Queue"
    if k == "cache":
        return "Cache"
    if k == "container":
        return "Container"
    return str(kind or "Element")


def node_subtitle(node: Node) -> str:
    if node.technology:
        return short_text(node.technology, 28)
    if node.kind == "person":
        return short_text(node.description or node.responsibility, 28)
    return short_text(node.responsibility or node.description, 28)


def stable_number(text: str) -> int:
    return sum(ord(c) for c in str(text))


def is_store_kind(kind: str) -> bool:
    return normalize_kind(kind) in {"database", "queue", "cache"}


def is_external_kind(kind: str) -> bool:
    return normalize_kind(kind) in {"person", "external_system"}


def is_internal_model_node(node: Node | None) -> bool:
    if node is None:
        return False
    return not node.external and normalize_kind(node.kind) not in {"person", "external_system"}


def synthetic_system_id(view_id: str) -> str:
    token = "".join(ch if ch.isalnum() else "-" for ch in str(view_id or "system-context")).strip("-")
    return f"synthetic-system--{token or 'system-context'}"


def build_synthetic_system_node(view_id: str, system_name: str) -> Node:
    return Node(
        id=synthetic_system_id(view_id),
        name=system_name,
        kind="software_system",
        technology="",
        description=f"System of interest for {system_name}.",
        responsibility="Represents the system of interest when the source view omitted an explicit software system node.",
        external=False,
        parent_id=None,
        synthetic=True,
    )


def is_component_kind(kind: str) -> bool:
    return normalize_kind(kind) == "component"


def kind_tone(kind: str) -> str:
    k = normalize_kind(kind)
    if k == "person":
        return "sage"
    if k in {"external_system", "external_actor", "actor"}:
        return "ochre"
    if k in {"database", "datastore"}:
        return "slate"
    if k == "queue":
        return "rose"
    if k == "cache":
        return "teal"
    if k in {"software_system", "system"}:
        return "indigo"
    if k == "container":
        return "plum"
    if k == "component":
        return "teal"
    return "slate"


def kind_colors(kind: str) -> Tuple[str, str, str]:
    tone = kind_tone(kind)
    return (
        f"var(--color-element-{tone}-fill)",
        f"var(--color-element-{tone})",
        tone,
    )


def boundary_style(tone: str) -> Tuple[str, str]:
    _ = tone
    return "var(--color-bg-sidebar)", "var(--color-border-default)"


def node_dimensions(node: Node, max_width: float = CARD_MAX_W) -> Tuple[float, float, List[str], List[str]]:
    subtitle = node_subtitle(node)
    header = type_header(node.kind, node.technology)
    name_lines = wrap_text(node.name, 24, 2)
    subtitle_lines = wrap_text(subtitle, 28, 2) if subtitle else []

    width_hint = max(
        approx_text_width(header, 9),
        max((approx_text_width(line, 14) for line in name_lines), default=0.0),
        max((approx_text_width(line, 11) for line in subtitle_lines), default=0.0),
    )
    width = clamp(width_hint + 56.0, CARD_MIN_W, max_width)

    body_lines = len(name_lines) + len(subtitle_lines)
    height = 36.0 + body_lines * 18.0 + 18.0
    if not subtitle_lines:
        height -= 8.0

    if normalize_kind(node.kind) in {"software_system", "system"}:
        width = clamp(width + 26.0, CARD_MIN_W + 30.0, max_width + 40.0)
        height += 10.0

    return width, height, name_lines, subtitle_lines


def place_vertical(
    ids: Sequence[str],
    sizes: Dict[str, Tuple[float, float]],
    x: float,
    start_y: float,
    gap_y: float = ROW_GAP,
) -> Tuple[Dict[str, Box], float]:
    boxes: Dict[str, Box] = {}
    y = start_y
    max_w = 0.0
    for nid in ids:
        w, h = sizes[nid]
        boxes[nid] = Box(x, y, w, h)
        y += h + gap_y
        max_w = max(max_w, w)
    return boxes, max_w


def place_grid(
    ids: Sequence[str],
    sizes: Dict[str, Tuple[float, float]],
    start_x: float,
    start_y: float,
    columns: int,
    gap_x: float = COLUMN_GAP,
    gap_y: float = ROW_GAP,
) -> Tuple[Dict[str, Box], float, float]:
    boxes: Dict[str, Box] = {}
    if not ids:
        return boxes, 0.0, 0.0

    col_widths = [0.0 for _ in range(columns)]
    rows: List[List[str]] = [[] for _ in range(columns)]
    for idx, nid in enumerate(ids):
        rows[idx % columns].append(nid)

    for col_idx, col_ids in enumerate(rows):
        col_widths[col_idx] = max((sizes[nid][0] for nid in col_ids), default=0.0)

    total_w = sum(col_widths) + gap_x * max(0, columns - 1)
    max_bottom = start_y
    x = start_x
    for col_idx, col_ids in enumerate(rows):
        y = start_y
        for nid in col_ids:
            w, h = sizes[nid]
            box_x = x + (col_widths[col_idx] - w) / 2.0
            boxes[nid] = Box(box_x, y, w, h)
            y += h + gap_y
            max_bottom = max(max_bottom, y - gap_y)
        x += col_widths[col_idx] + gap_x

    return boxes, total_w, max_bottom - start_y


def merge_boxes(*groups: Dict[str, Box]) -> Dict[str, Box]:
    merged: Dict[str, Box] = {}
    for group in groups:
        merged.update(group)
    return merged


def bounds_for_boxes(ids: Iterable[str], boxes: Dict[str, Box]) -> Tuple[float, float, float, float]:
    xs: List[float] = []
    ys: List[float] = []
    rights: List[float] = []
    bottoms: List[float] = []
    for nid in ids:
        box = boxes.get(nid)
        if not box:
            continue
        xs.append(box.x)
        ys.append(box.y)
        rights.append(box.x + box.w)
        bottoms.append(box.y + box.h)
    if not xs:
        return 0.0, 0.0, 0.0, 0.0
    return min(xs), min(ys), max(rights), max(bottoms)


def pick_system_boundary_label(nodes: Sequence[Node]) -> str:
    if len(nodes) == 1:
        return nodes[0].name
    if nodes:
        return f"{nodes[0].name} Boundary"
    return "System Boundary"


def format_boundary_label(base_label: str, suffix: str) -> str:
    base = " ".join(str(base_label or "").split())
    qualifier = " ".join(str(suffix or "").split())
    if not qualifier:
        return base

    base_lower = base.lower()
    qualifier_lower = qualifier.lower()
    bracketed_qualifier = f"[{qualifier_lower}]"

    if not base:
        return qualifier
    if base_lower == qualifier_lower or base_lower.endswith(bracketed_qualifier):
        return base
    return f"{base} [{qualifier}]"


def classify_component_role(node: Node) -> str:
    text = " ".join(
        [
            node.id,
            node.name,
            node.description,
            node.responsibility,
        ]
    ).lower()

    if any(tok in text for tok in ("api", "router", "gateway", "server", "rpc", "handler")):
        return "ingress"
    if any(tok in text for tok in ("assigner", "manager", "service", "controller", "orchestrator", "proposer")):
        return "coordination"
    if any(tok in text for tok in ("worker", "sender", "processor", "runner", "executor", "job")):
        return "worker"
    if any(tok in text for tok in ("store", "repo", "repository", "cache", "state", "db", "tracker", "mempool", "queue", "log")):
        return "state"
    return "general"


def collect_view_edges(view: Dict[str, Any], all_edges: Dict[str, Edge], visible_ids: set[str]) -> List[Edge]:
    explicit = [rid for rid in (view.get("relationship_ids") or []) if isinstance(rid, str)]
    if explicit:
        return [all_edges[rid] for rid in explicit if rid in all_edges]

    collected: List[Edge] = []
    for edge in all_edges.values():
        if edge.source_id in visible_ids and edge.target_id in visible_ids:
            collected.append(edge)
    return collected


def incident_edge_counts(edges: Sequence[Edge], visible_ids: set[str]) -> Dict[str, int]:
    counts: Dict[str, int] = defaultdict(int)
    for edge in edges:
        if edge.source_id in visible_ids:
            counts[edge.source_id] += 1
        if edge.target_id in visible_ids:
            counts[edge.target_id] += 1
    return counts


def container_spacing_boost(nodes: Sequence[Node], edges: Sequence[Edge]) -> float:
    visible_ids = {node.id for node in nodes}
    counts = incident_edge_counts(edges, visible_ids)
    max_incident = max(counts.values(), default=0)
    dense_nodes = sum(1 for value in counts.values() if value >= 4)
    if max_incident <= 3 and dense_nodes <= 1:
        return 0.0
    return min(28.0, max(0, max_incident - 3) * 3.0 + max(0, dense_nodes - 1) * 2.0)


def normalize_nodes(elements: Dict[str, Dict[str, Any]], ids: Sequence[str]) -> List[Node]:
    nodes: List[Node] = []
    for nid in ids:
        raw = elements.get(nid)
        if not raw:
            continue
        nodes.append(
            Node(
                id=nid,
                name=str(raw.get("name", nid)),
                kind=str(raw.get("kind", "")),
                technology=str(raw.get("technology", "")),
                description=str(raw.get("description", "")),
                responsibility=str(raw.get("responsibility", "")),
                external=bool(raw.get("external")),
                parent_id=str(raw.get("parent_id")) if raw.get("parent_id") else None,
                synthetic=bool(raw.get("synthetic")),
            )
        )
    return nodes


def system_context_layout(nodes: Sequence[Node]) -> LayoutResult:
    systems = [n for n in nodes if normalize_kind(n.kind) in {"software_system", "system"} and not n.external]
    actors = [n for n in nodes if normalize_kind(n.kind) == "person"]
    externals = [n for n in nodes if normalize_kind(n.kind) == "external_system"]
    internal_extra = [n for n in nodes if n not in systems and n not in actors and n not in externals]

    core_nodes = systems + internal_extra
    visible_nodes = actors + core_nodes + externals
    sizes = {n.id: node_dimensions(n)[:2] for n in visible_nodes}

    left_boxes, left_w = place_vertical([n.id for n in actors], sizes, VIEW_MARGIN_X, VIEW_MARGIN_Y + 24.0)
    center_start_x = VIEW_MARGIN_X + (left_w if left_boxes else 0.0) + (COLUMN_GAP if left_boxes and core_nodes else 0.0)
    center_boxes, center_w, center_h = place_grid(
        [n.id for n in core_nodes],
        sizes,
        center_start_x,
        VIEW_MARGIN_Y + 40.0,
        columns=2 if len(core_nodes) > 2 else 1,
    )
    right_start_x = center_start_x + center_w + (COLUMN_GAP if core_nodes and externals else 0.0)
    right_boxes, right_w = place_vertical([n.id for n in externals], sizes, right_start_x, VIEW_MARGIN_Y + 24.0)

    boxes = merge_boxes(left_boxes, center_boxes, right_boxes)
    width = VIEW_MARGIN_X + left_w + center_w + right_w
    width += COLUMN_GAP * max(0, int(bool(left_boxes and core_nodes)) + int(bool(core_nodes and right_boxes)))
    width += VIEW_MARGIN_X

    _, _, _, left_bottom = bounds_for_boxes(left_boxes.keys(), boxes)
    _, _, _, center_bottom = bounds_for_boxes(center_boxes.keys(), boxes)
    _, _, _, right_bottom = bounds_for_boxes(right_boxes.keys(), boxes)
    height = max(left_bottom, center_bottom, right_bottom, VIEW_MARGIN_Y + center_h) + VIEW_MARGIN_Y

    boundaries: List[Boundary] = []
    if core_nodes:
        x1, y1, x2, y2 = bounds_for_boxes([n.id for n in core_nodes], boxes)
        boundaries.append(
            Boundary(
                x=x1 - BOUNDARY_PAD,
                y=y1 - 28.0,
                w=(x2 - x1) + BOUNDARY_PAD * 2.0,
                h=(y2 - y1) + BOUNDARY_PAD * 2.0,
                label=pick_system_boundary_label(systems or core_nodes),
                tone="system",
            )
        )
        width = max(width, boundaries[-1].x + boundaries[-1].w + VIEW_MARGIN_X)
        height = max(height, boundaries[-1].y + boundaries[-1].h + VIEW_MARGIN_Y)

    return LayoutResult(width=width, height=height, boxes=boxes, boundaries=boundaries)


def container_layout(nodes: Sequence[Node], edges: Sequence[Edge] | None = None) -> LayoutResult:
    system_nodes = [n for n in nodes if normalize_kind(n.kind) in {"software_system", "system"} and not n.external]
    actors = [n for n in nodes if normalize_kind(n.kind) == "person"]
    stores = [n for n in nodes if is_store_kind(n.kind)]
    externals = [n for n in nodes if normalize_kind(n.kind) == "external_system"]
    core = [n for n in nodes if n not in system_nodes and n not in actors and n not in stores and n not in externals]

    visible_nodes = actors + core + stores + externals
    sizes = {n.id: node_dimensions(n)[:2] for n in visible_nodes}
    spacing_boost = container_spacing_boost(visible_nodes, edges or [])
    lane_gap = COLUMN_GAP + spacing_boost * 0.5
    core_gap_x = COLUMN_GAP + spacing_boost
    core_gap_y = 40.0 + spacing_boost * 0.5
    store_gap_x = 42.0 + spacing_boost * 0.5
    store_gap_y = 30.0 + spacing_boost * 0.35

    left_boxes, left_w = place_vertical([n.id for n in actors], sizes, VIEW_MARGIN_X, VIEW_MARGIN_Y + 74.0)

    boundary_start_x = VIEW_MARGIN_X + (left_w if actors else 0.0) + (lane_gap if actors and (core or stores) else 0.0)
    core_boxes, core_w, core_h = place_grid(
        [n.id for n in core],
        sizes,
        boundary_start_x + BOUNDARY_PAD,
        VIEW_MARGIN_Y + 104.0,
        columns=2 if len(core) > 3 else 1,
        gap_x=core_gap_x,
        gap_y=core_gap_y,
    )

    stores_start_y = VIEW_MARGIN_Y + 128.0 + core_h + spacing_boost * 0.4
    store_boxes, store_w, store_h = place_grid(
        [n.id for n in stores],
        sizes,
        boundary_start_x + BOUNDARY_PAD,
        stores_start_y,
        columns=min(max(len(stores), 1), 3),
        gap_x=store_gap_x,
        gap_y=store_gap_y,
    )

    internal_boxes = merge_boxes(core_boxes, store_boxes)
    internal_ids = [n.id for n in core + stores]
    x1, y1, x2, y2 = bounds_for_boxes(internal_ids, internal_boxes)
    boundary_w = max((x2 - x1) + BOUNDARY_PAD * 2.0, 420.0 if internal_ids else 0.0)
    boundary_h = max((y2 - y1) + BOUNDARY_PAD * 2.0 + 12.0, 260.0 if internal_ids else 0.0)

    if internal_ids:
        shift_x = boundary_start_x - (x1 - BOUNDARY_PAD)
        for box in internal_boxes.values():
            box.x += shift_x
        x1 += shift_x
        x2 += shift_x

    right_start_x = boundary_start_x + boundary_w + (lane_gap if externals else 0.0)
    right_boxes, right_w = place_vertical([n.id for n in externals], sizes, right_start_x, VIEW_MARGIN_Y + 140.0)

    boxes = merge_boxes(left_boxes, internal_boxes, right_boxes)
    width = right_start_x + right_w + VIEW_MARGIN_X if externals else boundary_start_x + boundary_w + VIEW_MARGIN_X
    height = max(
        VIEW_MARGIN_Y + boundary_h + VIEW_MARGIN_Y,
        max((box.y + box.h for box in left_boxes.values()), default=0.0) + VIEW_MARGIN_Y,
        max((box.y + box.h for box in right_boxes.values()), default=0.0) + VIEW_MARGIN_Y,
    )

    boundaries: List[Boundary] = []
    if internal_ids:
        boundary_label = system_nodes[0].name if system_nodes else "System Boundary"
        boundaries.append(
            Boundary(
                x=boundary_start_x,
                y=VIEW_MARGIN_Y + 74.0,
                w=boundary_w,
                h=max(boundary_h, max((box.y + box.h for box in internal_boxes.values()), default=0.0) - (VIEW_MARGIN_Y + 74.0) + BOUNDARY_PAD),
                label=format_boundary_label(boundary_label, "System Boundary"),
                tone="container",
            )
        )
        height = max(height, boundaries[-1].y + boundaries[-1].h + VIEW_MARGIN_Y)

    return LayoutResult(width=width, height=height, boxes=boxes, boundaries=boundaries)


def component_layout(nodes: Sequence[Node], parent_container_id: str | None, all_nodes: Dict[str, Node]) -> LayoutResult:
    parent = all_nodes.get(parent_container_id or "")
    components = [n for n in nodes if is_component_kind(n.kind)]
    peers = [n for n in nodes if not is_component_kind(n.kind)]
    external_peers = [n for n in peers if normalize_kind(n.kind) in {"person", "external_system"}]
    container_peers = [n for n in peers if normalize_kind(n.kind) in {"container", "database", "queue", "cache", "software_system", "system"}]

    sizes = {n.id: node_dimensions(n)[:2] for n in components + peers}

    left_boxes, left_w = place_vertical([n.id for n in external_peers if normalize_kind(n.kind) == "person"], sizes, VIEW_MARGIN_X, VIEW_MARGIN_Y + 88.0)

    role_buckets = {"ingress": [], "coordination": [], "general": [], "worker": [], "state": []}
    for node in components:
        role_buckets[classify_component_role(node)].append(node.id)

    boundary_x = VIEW_MARGIN_X + (left_w if left_boxes else 0.0) + (COLUMN_GAP if left_boxes and components else 0.0)
    interior_x = boundary_x + BOUNDARY_PAD
    top_y = VIEW_MARGIN_Y + 98.0

    top_ids = role_buckets["ingress"] + role_buckets["coordination"] + role_buckets["worker"] + role_buckets["general"]
    top_columns = 3 if len(top_ids) >= 5 else 2 if len(top_ids) >= 3 else 1
    top_boxes, top_w, top_h = place_grid(top_ids, sizes, interior_x, top_y, top_columns, gap_x=42.0, gap_y=30.0)

    state_boxes: Dict[str, Box] = {}
    state_ids = role_buckets["state"]
    state_y = top_y + top_h + (38.0 if top_ids and state_ids else 0.0)
    if state_ids:
        state_boxes, state_w, state_h = place_grid(
            state_ids,
            sizes,
            interior_x,
            state_y,
            columns=min(max(len(state_ids), 1), 3),
            gap_x=36.0,
            gap_y=26.0,
        )
    else:
        state_w, state_h = 0.0, 0.0

    internal_boxes = merge_boxes(top_boxes, state_boxes)
    internal_ids = [node.id for node in components]
    x1, y1, x2, y2 = bounds_for_boxes(internal_ids, internal_boxes)
    boundary_w = max((x2 - x1) + BOUNDARY_PAD * 2.0, 420.0 if internal_ids else 0.0)
    boundary_h = max((y2 - y1) + BOUNDARY_PAD * 2.0 + 16.0, 240.0 if internal_ids else 0.0)
    if internal_ids:
        shift_x = boundary_x - (x1 - BOUNDARY_PAD)
        for box in internal_boxes.values():
            box.x += shift_x

    right_start_x = boundary_x + boundary_w + (COLUMN_GAP if container_peers else 0.0)
    right_boxes, right_w = place_vertical([n.id for n in container_peers], sizes, right_start_x, VIEW_MARGIN_Y + 120.0)

    lower_peer_ids = [n.id for n in external_peers if normalize_kind(n.kind) != "person"]
    bottom_boxes, bottom_w, _ = place_grid(
        lower_peer_ids,
        sizes,
        boundary_x + 12.0,
        VIEW_MARGIN_Y + boundary_h + 92.0,
        columns=min(max(len(lower_peer_ids), 1), 3),
        gap_x=36.0,
        gap_y=28.0,
    ) if lower_peer_ids else ({}, 0.0, 0.0)

    boxes = merge_boxes(left_boxes, internal_boxes, right_boxes, bottom_boxes)
    width = max(
        boundary_x + boundary_w + VIEW_MARGIN_X,
        right_start_x + right_w + VIEW_MARGIN_X if right_boxes else 0.0,
        boundary_x + bottom_w + VIEW_MARGIN_X if bottom_boxes else 0.0,
    )
    height = max(
        VIEW_MARGIN_Y + boundary_h + VIEW_MARGIN_Y,
        max((box.y + box.h for box in left_boxes.values()), default=0.0) + VIEW_MARGIN_Y,
        max((box.y + box.h for box in right_boxes.values()), default=0.0) + VIEW_MARGIN_Y,
        max((box.y + box.h for box in bottom_boxes.values()), default=0.0) + VIEW_MARGIN_Y,
    )

    boundary_label = parent.name if parent else "Parent Container"
    boundaries = [
        Boundary(
            x=boundary_x,
            y=VIEW_MARGIN_Y + 74.0,
            w=boundary_w,
            h=boundary_h,
            label=format_boundary_label(boundary_label, "Container Boundary"),
            tone="container",
        )
    ] if internal_ids else []

    return LayoutResult(width=width, height=height, boxes=boxes, boundaries=boundaries)


def deployment_layout(nodes: Sequence[Node], view: Dict[str, Any], all_nodes: Dict[str, Node]) -> LayoutResult:
    deployment_node_ids = [nid for nid in (view.get("deployment_node_ids") or []) if isinstance(nid, str)]
    placements = [p for p in (view.get("placement") or []) if isinstance(p, dict)]
    sizes = {n.id: node_dimensions(n, max_width=260.0)[:2] for n in nodes}

    boundary_start_x = VIEW_MARGIN_X
    boundaries: List[Boundary] = []
    boxes: Dict[str, Box] = {}
    max_height = 0.0

    unplaced = {n.id for n in nodes}
    for node_id in deployment_node_ids:
        placed_ids = [p.get("element_id") for p in placements if p.get("node_id") == node_id and isinstance(p.get("element_id"), str)]
        placed_ids = [eid for eid in placed_ids if eid in sizes]
        for eid in placed_ids:
            unplaced.discard(eid)

        inner_boxes, inner_w, inner_h = place_grid(
            placed_ids,
            sizes,
            boundary_start_x + BOUNDARY_PAD,
            VIEW_MARGIN_Y + 74.0,
            columns=2 if len(placed_ids) > 3 else 1,
            gap_x=32.0,
            gap_y=28.0,
        )
        boxes.update(inner_boxes)

        node_label = all_nodes.get(node_id).name if node_id in all_nodes else node_id.replace("-", " ").title()
        boundary_w = max(inner_w + BOUNDARY_PAD * 2.0, 320.0)
        boundary_h = max(inner_h + BOUNDARY_PAD * 2.0 + 12.0, 240.0)
        boundaries.append(
            Boundary(
                x=boundary_start_x,
                y=VIEW_MARGIN_Y + 24.0,
                w=boundary_w,
                h=boundary_h,
                label=node_label,
                tone="deployment",
            )
        )
        boundary_start_x += boundary_w + COLUMN_GAP
        max_height = max(max_height, boundary_h)

    if unplaced:
        trailing_boxes, trailing_w, trailing_h = place_vertical(
            sorted(unplaced),
            sizes,
            boundary_start_x,
            VIEW_MARGIN_Y + 88.0,
        )
        boxes.update(trailing_boxes)
        boundary_start_x += trailing_w
        max_height = max(max_height, trailing_h + 110.0)

    width = boundary_start_x + VIEW_MARGIN_X
    height = VIEW_MARGIN_Y + max_height + VIEW_MARGIN_Y
    return LayoutResult(width=width, height=height, boxes=boxes, boundaries=boundaries)


def generic_layout(nodes: Sequence[Node]) -> LayoutResult:
    sizes = {n.id: node_dimensions(n)[:2] for n in nodes}
    boxes, total_w, total_h = place_grid(
        [n.id for n in nodes],
        sizes,
        VIEW_MARGIN_X,
        VIEW_MARGIN_Y,
        columns=2 if len(nodes) > 4 else 1,
    )
    return LayoutResult(
        width=VIEW_MARGIN_X + total_w + VIEW_MARGIN_X,
        height=VIEW_MARGIN_Y + total_h + VIEW_MARGIN_Y,
        boxes=boxes,
        boundaries=[],
    )


def choose_layout(
    view: Dict[str, Any],
    nodes: Sequence[Node],
    all_nodes: Dict[str, Node],
    edges: Sequence[Edge] | None = None,
) -> LayoutResult:
    view_type = normalize_view_type(str(view.get("type", "")))
    if view_type == "system_context":
        return system_context_layout(nodes)
    if view_type == "container":
        return container_layout(nodes, edges)
    if view_type == "component":
        return component_layout(nodes, view.get("parent_container_id"), all_nodes)
    if view_type == "deployment":
        return deployment_layout(nodes, view, all_nodes)
    return generic_layout(nodes)


def trim_horizontal_layout_padding(layout: LayoutResult) -> LayoutResult:
    if layout.width < WIDE_LAYOUT_WIDTH_THRESHOLD:
        return layout

    left_edges = [box.x for box in layout.boxes.values()]
    right_edges = [box.x + box.w for box in layout.boxes.values()]
    left_edges.extend(boundary.x for boundary in layout.boundaries)
    right_edges.extend(boundary.x + boundary.w for boundary in layout.boundaries)
    if not left_edges or not right_edges:
        return layout

    current_left = min(left_edges)
    current_right = layout.width - max(right_edges)
    trim_left = max(0.0, current_left - COMPACT_VIEW_MARGIN_X)
    trim_right = max(0.0, current_right - COMPACT_VIEW_MARGIN_X)
    if trim_left <= ROUTING_EPSILON and trim_right <= ROUTING_EPSILON:
        return layout

    shifted_boxes = {
        nid: Box(
            x=box.x - trim_left,
            y=box.y,
            w=box.w,
            h=box.h,
        )
        for nid, box in layout.boxes.items()
    }
    shifted_boundaries = [
        Boundary(
            x=boundary.x - trim_left,
            y=boundary.y,
            w=boundary.w,
            h=boundary.h,
            label=boundary.label,
            tone=boundary.tone,
        )
        for boundary in layout.boundaries
    ]
    return LayoutResult(
        width=layout.width - trim_left - trim_right,
        height=layout.height,
        boxes=shifted_boxes,
        boundaries=shifted_boundaries,
    )


def box_center(box: Box) -> Tuple[float, float]:
    return box.x + box.w / 2.0, box.y + box.h / 2.0


def preferred_port_side(src: Box, dst: Box) -> str:
    src_cx, src_cy = box_center(src)
    dst_cx, dst_cy = box_center(dst)

    gap_east = dst.x - (src.x + src.w)
    gap_west = src.x - (dst.x + dst.w)
    gap_south = dst.y - (src.y + src.h)
    gap_north = src.y - (dst.y + dst.h)

    horizontal_gap = max(gap_east, gap_west, 0.0)
    vertical_gap = max(gap_south, gap_north, 0.0)

    if horizontal_gap <= ROUTING_EPSILON and vertical_gap <= ROUTING_EPSILON:
        dx = dst_cx - src_cx
        dy = dst_cy - src_cy
        if abs(dx) >= abs(dy):
            return "east" if dx >= 0 else "west"
        return "south" if dy >= 0 else "north"

    if horizontal_gap >= vertical_gap:
        return "east" if dst_cx >= src_cx else "west"
    return "south" if dst_cy >= src_cy else "north"


def anchor_point(box: Box, side: str) -> Tuple[float, float]:
    cx, cy = box_center(box)
    if side == "north":
        return cx, box.y
    if side == "south":
        return cx, box.y + box.h
    if side == "west":
        return box.x, cy
    return box.x + box.w, cy


def slot_anchor_point(box: Box, side: str, slot_index: int, slot_count: int) -> Tuple[float, float]:
    if slot_count <= 1:
        return anchor_point(box, side)

    if side in {"east", "west"}:
        inset = min(PORT_SLOT_INSET, box.h / 3.0)
        top = box.y + inset
        bottom = box.y + box.h - inset
        if bottom - top <= ROUTING_EPSILON:
            return anchor_point(box, side)
        ratio = (slot_index + 1) / (slot_count + 1)
        y = top + (bottom - top) * ratio
        return (box.x if side == "west" else box.x + box.w, y)

    inset = min(PORT_SLOT_INSET, box.w / 3.0)
    left = box.x + inset
    right = box.x + box.w - inset
    if right - left <= ROUTING_EPSILON:
        return anchor_point(box, side)
    ratio = (slot_index + 1) / (slot_count + 1)
    x = left + (right - left) * ratio
    return (x, box.y if side == "north" else box.y + box.h)


def offset_point(point: Tuple[float, float], side: str, distance: float) -> Tuple[float, float]:
    x, y = point
    if side == "north":
        return x, y - distance
    if side == "south":
        return x, y + distance
    if side == "west":
        return x - distance, y
    return x + distance, y


def cross_axis_coordinate(box: Box, side: str) -> float:
    cx, cy = box_center(box)
    return cy if side in {"east", "west"} else cx


def side_load_key(node_id: str, side: str) -> tuple[str, str]:
    return str(node_id or ""), str(side or "")


def side_load_count(loads: Dict[tuple[str, str], int], node_id: str, side: str) -> int:
    return loads.get(side_load_key(node_id, side), 0)


def port_side_soft_cap(node_id: str, incident_counts: Dict[str, int]) -> int:
    total = incident_counts.get(node_id, 0)
    return max(1, math.ceil(total / 4.0))


def select_edge_sides(
    rel_id: str,
    src_id: str,
    dst_id: str,
    src_box: Box,
    dst_box: Box,
    all_boxes: Dict[str, Box],
    canvas_w: float,
    canvas_h: float,
    side_loads: Dict[tuple[str, str], int] | None = None,
    incident_counts: Dict[str, int] | None = None,
) -> Tuple[str, str]:
    preferred_src = preferred_port_side(src_box, dst_box)
    preferred_dst = preferred_port_side(dst_box, src_box)
    source_soft_cap = port_side_soft_cap(src_id, incident_counts or {})
    target_soft_cap = port_side_soft_cap(dst_id, incident_counts or {})
    side_order = ["north", "south", "east", "west"]
    src_candidates = [preferred_src] + [side for side in side_order if side != preferred_src]
    dst_candidates = [preferred_dst] + [side for side in side_order if side != preferred_dst]

    best_sides = (preferred_src, preferred_dst)
    best_score: Tuple[float, ...] | None = None
    for src_side in src_candidates:
        for dst_side in dst_candidates:
            start = anchor_point(src_box, src_side)
            end = anchor_point(dst_box, dst_side)
            _, blockers, clearance, length, endpoint_penalty, _ = best_route_points(
                rel_id,
                src_id,
                dst_id,
                start,
                end,
                src_side,
                dst_side,
                all_boxes,
                canvas_w,
                canvas_h,
            )
            source_load = side_load_count(side_loads or {}, src_id, src_side)
            target_load = side_load_count(side_loads or {}, dst_id, dst_side)
            score = (
                float(len(blockers)),
                float(endpoint_penalty),
                max(0.0, ROUTE_CLEARANCE_TARGET - clearance),
                float(max(0, target_load + 1 - target_soft_cap)),
                float(max(0, source_load + 1 - source_soft_cap)),
                float(target_load),
                float(source_load),
                float(int(src_side != preferred_src) + int(dst_side != preferred_dst)),
                length,
            )
            if best_score is None or score < best_score:
                best_score = score
                best_sides = (src_side, dst_side)
    return best_sides


def assign_edge_ports(
    edges: Sequence[Edge],
    boxes: Dict[str, Box],
    canvas_w: float,
    canvas_h: float,
) -> Dict[str, Dict[str, Any]]:
    port_map: Dict[str, Dict[str, Any]] = {}
    grouped: Dict[Tuple[str, str], List[Tuple[str, str, float]]] = defaultdict(list)
    side_loads: Dict[Tuple[str, str], int] = {}
    incident_counts = incident_edge_counts(edges, set(boxes.keys()))

    sorted_edges = sorted(
        edges,
        key=lambda edge: (
            -max(incident_counts.get(edge.source_id, 0), incident_counts.get(edge.target_id, 0)),
            -(incident_counts.get(edge.source_id, 0) + incident_counts.get(edge.target_id, 0)),
            edge.id,
        ),
    )

    for edge in sorted_edges:
        src_box = boxes.get(edge.source_id)
        dst_box = boxes.get(edge.target_id)
        if not src_box or not dst_box:
            continue
        src_side, dst_side = select_edge_sides(
            edge.id,
            edge.source_id,
            edge.target_id,
            src_box,
            dst_box,
            boxes,
            canvas_w,
            canvas_h,
            side_loads,
            incident_counts,
        )
        port_map[edge.id] = {
            "source_side": src_side,
            "target_side": dst_side,
        }
        side_loads[side_load_key(edge.source_id, src_side)] = side_load_count(side_loads, edge.source_id, src_side) + 1
        side_loads[side_load_key(edge.target_id, dst_side)] = side_load_count(side_loads, edge.target_id, dst_side) + 1
        grouped[(edge.source_id, src_side)].append((edge.id, "source", cross_axis_coordinate(dst_box, src_side)))
        grouped[(edge.target_id, dst_side)].append((edge.id, "target", cross_axis_coordinate(src_box, dst_side)))

    for (node_id, side), records in grouped.items():
        box = boxes.get(node_id)
        if not box:
            continue
        sorted_records = sorted(records, key=lambda item: (item[2], item[0], item[1]))
        slot_count = len(sorted_records)
        for slot_index, (edge_id, role, _) in enumerate(sorted_records):
            anchor = slot_anchor_point(box, side, slot_index, slot_count)
            key = "source_anchor" if role == "source" else "target_anchor"
            port_map.setdefault(edge_id, {})[key] = anchor
            lane_bias_key = "source_lane_bias" if role == "source" else "target_lane_bias"
            port_map.setdefault(edge_id, {})[lane_bias_key] = (slot_index - (slot_count - 1) / 2.0) * ROUTE_BUNDLE_SPACING

    return port_map


def collapse_orthogonal_points(points: Sequence[Tuple[float, float]]) -> List[Tuple[float, float]]:
    deduped: List[Tuple[float, float]] = []
    for x, y in points:
        if deduped and math.hypot(x - deduped[-1][0], y - deduped[-1][1]) <= ROUTING_EPSILON:
            continue
        deduped.append((x, y))

    if len(deduped) <= 2:
        return deduped

    collapsed: List[Tuple[float, float]] = [deduped[0]]
    for idx in range(1, len(deduped) - 1):
        px, py = collapsed[-1]
        cx, cy = deduped[idx]
        nx, ny = deduped[idx + 1]
        same_x = abs(px - cx) <= ROUTING_EPSILON and abs(cx - nx) <= ROUTING_EPSILON
        same_y = abs(py - cy) <= ROUTING_EPSILON and abs(cy - ny) <= ROUTING_EPSILON
        if same_x or same_y:
            in_dx = cx - px
            in_dy = cy - py
            out_dx = nx - cx
            out_dy = ny - cy
            same_direction = (in_dx * out_dx + in_dy * out_dy) > ROUTING_EPSILON
            if same_direction:
                continue
        collapsed.append((cx, cy))
    collapsed.append(deduped[-1])
    return collapsed


def route_mode(src_side: str, dst_side: str) -> str:
    if src_side in {"east", "west"} and dst_side in {"east", "west"}:
        return "mid_x"
    if src_side in {"north", "south"} and dst_side in {"north", "south"}:
        return "mid_y"
    if src_side in {"east", "west"}:
        return "mid_y"
    return "mid_x"


def build_route_points(
    start: Tuple[float, float],
    start_stub: Tuple[float, float],
    end_stub: Tuple[float, float],
    end: Tuple[float, float],
    lane_value: float,
    mode: str,
) -> List[Tuple[float, float]]:
    if mode == "mid_x":
        return [start, start_stub, (lane_value, start_stub[1]), (lane_value, end_stub[1]), end_stub, end]
    return [start, start_stub, (start_stub[0], lane_value), (end_stub[0], lane_value), end_stub, end]


def build_detour_route_points(
    start: Tuple[float, float],
    start_stub: Tuple[float, float],
    end_stub: Tuple[float, float],
    end: Tuple[float, float],
    lane_value: float,
    detour_value: float,
    mode: str,
) -> List[Tuple[float, float]]:
    if mode == "mid_x":
        return [
            start,
            start_stub,
            (lane_value, start_stub[1]),
            (lane_value, detour_value),
            (end_stub[0], detour_value),
            end_stub,
            end,
        ]
    return [
        start,
        start_stub,
        (detour_value, start_stub[1]),
        (detour_value, end_stub[1]),
        end_stub,
        end,
    ]


def expand_box(box: Box, padding: float) -> Box:
    return Box(
        x=box.x - padding,
        y=box.y - padding,
        w=box.w + padding * 2.0,
        h=box.h + padding * 2.0,
    )


def segment_intersects_box(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    box: Box,
) -> bool:
    if math.hypot(p2[0] - p1[0], p2[1] - p1[1]) <= ROUTING_EPSILON:
        return False

    if abs(p1[0] - p2[0]) <= ROUTING_EPSILON:
        x = p1[0]
        y1, y2 = sorted((p1[1], p2[1]))
        return box.x < x < box.x + box.w and y2 > box.y and y1 < box.y + box.h

    if abs(p1[1] - p2[1]) <= ROUTING_EPSILON:
        y = p1[1]
        x1, x2 = sorted((p1[0], p2[0]))
        return box.y < y < box.y + box.h and x2 > box.x and x1 < box.x + box.w

    return False


def segment_box_distance(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    box: Box,
) -> float:
    if abs(p1[0] - p2[0]) <= ROUTING_EPSILON:
        x = p1[0]
        y1, y2 = sorted((p1[1], p2[1]))
        dx = 0.0 if box.x <= x <= box.x + box.w else min(abs(x - box.x), abs(x - (box.x + box.w)))
        if y2 < box.y:
            dy = box.y - y2
        elif y1 > box.y + box.h:
            dy = y1 - (box.y + box.h)
        else:
            dy = 0.0
        return math.hypot(dx, dy)

    if abs(p1[1] - p2[1]) <= ROUTING_EPSILON:
        y = p1[1]
        x1, x2 = sorted((p1[0], p2[0]))
        dy = 0.0 if box.y <= y <= box.y + box.h else min(abs(y - box.y), abs(y - (box.y + box.h)))
        if x2 < box.x:
            dx = box.x - x2
        elif x1 > box.x + box.w:
            dx = x1 - (box.x + box.w)
        else:
            dx = 0.0
        return math.hypot(dx, dy)

    return float("inf")


def route_blockers(
    points: Sequence[Tuple[float, float]],
    boxes: Dict[str, Box],
    ignore_ids: set[str],
) -> set[str]:
    blockers: set[str] = set()
    padded_boxes = {
        node_id: expand_box(box, ROUTE_CLEARANCE)
        for node_id, box in boxes.items()
        if node_id not in ignore_ids
    }
    for idx in range(len(points) - 1):
        segment_start = points[idx]
        segment_end = points[idx + 1]
        for node_id, box in padded_boxes.items():
            if segment_intersects_box(segment_start, segment_end, box):
                blockers.add(node_id)
    return blockers


def approximate_route_length(points: Sequence[Tuple[float, float]]) -> float:
    length = 0.0
    for idx in range(len(points) - 1):
        length += math.hypot(points[idx + 1][0] - points[idx][0], points[idx + 1][1] - points[idx][1])
    return length


def route_min_clearance(
    points: Sequence[Tuple[float, float]],
    boxes: Dict[str, Box],
    ignore_ids: set[str],
) -> float:
    min_distance = float("inf")
    for idx in range(len(points) - 1):
        segment_start = points[idx]
        segment_end = points[idx + 1]
        for node_id, box in boxes.items():
            if node_id in ignore_ids:
                continue
            min_distance = min(min_distance, segment_box_distance(segment_start, segment_end, box))
            if min_distance <= ROUTING_EPSILON:
                return 0.0
    return min_distance


def route_endpoint_interior_penalty(
    points: Sequence[Tuple[float, float]],
    src_box: Box | None,
    dst_box: Box | None,
) -> int:
    if len(points) < 2:
        return 0

    penalty = 0
    for idx in range(len(points) - 1):
        p1 = points[idx]
        p2 = points[idx + 1]
        if src_box is not None and idx > 0 and segment_intersects_box(p1, p2, src_box):
            penalty += 1
        if dst_box is not None and idx < len(points) - 2 and segment_intersects_box(p1, p2, dst_box):
            penalty += 1
    return penalty


def lane_excursion_penalty(
    mode: str,
    lane_value: float,
    start_stub: Tuple[float, float],
    end_stub: Tuple[float, float],
) -> float:
    start_axis = start_stub[0] if mode == "mid_x" else start_stub[1]
    end_axis = end_stub[0] if mode == "mid_x" else end_stub[1]
    low = min(start_axis, end_axis)
    high = max(start_axis, end_axis)
    if lane_value < low:
        return low - lane_value
    if lane_value > high:
        return lane_value - high
    return 0.0


def detour_baseline_coordinate(
    mode: str,
    start_stub: Tuple[float, float],
    end_stub: Tuple[float, float],
) -> float:
    if mode == "mid_x":
        return (start_stub[1] + end_stub[1]) / 2.0
    return (start_stub[0] + end_stub[0]) / 2.0


def detour_excursion_penalty(
    mode: str,
    detour_value: float,
    start_stub: Tuple[float, float],
    end_stub: Tuple[float, float],
) -> float:
    start_axis = start_stub[1] if mode == "mid_x" else start_stub[0]
    end_axis = end_stub[1] if mode == "mid_x" else end_stub[0]
    low = min(start_axis, end_axis)
    high = max(start_axis, end_axis)
    if detour_value < low:
        return low - detour_value
    if detour_value > high:
        return detour_value - high
    return 0.0


def route_bundle_key(
    src_id: str,
    dst_id: str,
    src_side: str,
    dst_side: str,
    mode: str,
    port_info: Dict[str, Any] | None = None,
) -> str:
    source_lane_bias = float(port_info.get("source_lane_bias", 0.0)) if port_info else 0.0
    target_lane_bias = float(port_info.get("target_lane_bias", 0.0)) if port_info else 0.0
    if abs(target_lane_bias) > ROUTING_EPSILON:
        return f"target::{dst_id}::{dst_side}::{mode}"
    if abs(source_lane_bias) > ROUTING_EPSILON:
        return f"source::{src_id}::{src_side}::{mode}"
    return f"target::{dst_id}::{dst_side}::{mode}"


def route_lane_reuse_penalty(used_lanes: Sequence[float], lane_value: float) -> float:
    return sum(max(0.0, ROUTE_BUNDLE_SPACING - abs(lane_value - used_lane)) for used_lane in used_lanes)


def remember_route_lane(lane_usage: Dict[str, List[float]] | None, bundle_key: str, lane_value: float) -> None:
    if lane_usage is None or not bundle_key or not math.isfinite(lane_value):
        return
    lane_usage.setdefault(bundle_key, []).append(lane_value)


def dedupe_lane_values(values: Sequence[float]) -> List[float]:
    deduped: List[float] = []
    for value in values:
        if any(abs(value - existing) <= ROUTING_EPSILON for existing in deduped):
            continue
        deduped.append(value)
    return deduped


def expand_lane_bundle_candidates(values: Sequence[float], min_value: float, max_value: float) -> List[float]:
    expanded: List[float] = []
    for value in values:
        for slot in range(-ROUTE_BUNDLE_VARIANT_COUNT, ROUTE_BUNDLE_VARIANT_COUNT + 1):
            candidate = value + slot * ROUTE_BUNDLE_SPACING
            if candidate < min_value - ROUTING_EPSILON or candidate > max_value + ROUTING_EPSILON:
                continue
            expanded.append(candidate)
    return dedupe_lane_values(expanded)


def gap_midpoints(intervals: Sequence[Tuple[float, float]]) -> List[float]:
    if not intervals:
        return []

    sorted_intervals = sorted(intervals, key=lambda item: (item[0], item[1]))
    merged: List[Tuple[float, float]] = []
    for start, end in sorted_intervals:
        if not merged:
            merged.append((start, end))
            continue
        prev_start, prev_end = merged[-1]
        if start <= prev_end + ROUTING_EPSILON:
            merged[-1] = (prev_start, max(prev_end, end))
            continue
        merged.append((start, end))

    values: List[float] = []
    for idx in range(len(merged) - 1):
        left_end = merged[idx][1]
        right_start = merged[idx + 1][0]
        if right_start - left_end <= ROUTE_CLEARANCE * 2.0:
            continue
        values.append((left_end + right_start) / 2.0)
    return values


def detour_axis_values(
    mode: str,
    blocker_ids: Sequence[str],
    boxes: Dict[str, Box],
    canvas_w: float,
    canvas_h: float,
    start_stub: Tuple[float, float],
    end_stub: Tuple[float, float],
) -> List[float]:
    values: List[float] = [detour_baseline_coordinate(mode, start_stub, end_stub)]
    min_axis = 8.0
    max_axis = canvas_h - 8.0 if mode == "mid_x" else canvas_w - 8.0
    if boxes:
        min_x = min(box.x for box in boxes.values())
        max_x = max(box.x + box.w for box in boxes.values())
        min_y = min(box.y for box in boxes.values())
        max_y = max(box.y + box.h for box in boxes.values())
        if mode == "mid_x":
            for box in boxes.values():
                values.append(max(8.0, box.y - ROUTE_GUTTER))
                values.append(min(canvas_h - 8.0, box.y + box.h + ROUTE_GUTTER))
            values.extend(gap_midpoints([(box.y, box.y + box.h) for box in boxes.values()]))
            values.extend([max(8.0, min_y - ROUTE_GUTTER), min(canvas_h - 8.0, max_y + ROUTE_GUTTER)])
        else:
            for box in boxes.values():
                values.append(max(8.0, box.x - ROUTE_GUTTER))
                values.append(min(canvas_w - 8.0, box.x + box.w + ROUTE_GUTTER))
            values.extend(gap_midpoints([(box.x, box.x + box.w) for box in boxes.values()]))
            values.extend([max(8.0, min_x - ROUTE_GUTTER), min(canvas_w - 8.0, max_x + ROUTE_GUTTER)])

    for blocker_id in blocker_ids:
        box = boxes.get(blocker_id)
        if not box:
            continue
        if mode == "mid_x":
            values.append(max(8.0, box.y - ROUTE_GUTTER))
            values.append(min(canvas_h - 8.0, box.y + box.h + ROUTE_GUTTER))
        else:
            values.append(max(8.0, box.x - ROUTE_GUTTER))
            values.append(min(canvas_w - 8.0, box.x + box.w + ROUTE_GUTTER))

    baseline = detour_baseline_coordinate(mode, start_stub, end_stub)
    deduped = expand_lane_bundle_candidates(values, min_axis, max_axis)
    return sorted(
        deduped,
        key=lambda value: (
            detour_excursion_penalty(mode, value, start_stub, end_stub),
            abs(value - baseline),
            value,
        ),
    )


def candidate_lane_values(
    mode: str,
    default_lane: float,
    boxes: Dict[str, Box],
    canvas_w: float,
    canvas_h: float,
    start_stub: Tuple[float, float],
    end_stub: Tuple[float, float],
) -> List[float]:
    values: List[float] = [default_lane]
    min_axis = 8.0
    max_axis = canvas_w - 8.0 if mode == "mid_x" else canvas_h - 8.0
    if not boxes:
        return values

    min_x = min(box.x for box in boxes.values())
    max_x = max(box.x + box.w for box in boxes.values())
    min_y = min(box.y for box in boxes.values())
    max_y = max(box.y + box.h for box in boxes.values())

    if mode == "mid_x":
        for box in boxes.values():
            values.append(max(8.0, box.x - ROUTE_GUTTER))
            values.append(min(canvas_w - 8.0, box.x + box.w + ROUTE_GUTTER))
        values.extend(gap_midpoints([(box.x, box.x + box.w) for box in boxes.values()]))
        values.extend(
            [
                max(8.0, min_x - ROUTE_GUTTER),
                min(canvas_w - 8.0, max_x + ROUTE_GUTTER),
            ]
        )
    else:
        for box in boxes.values():
            values.append(max(8.0, box.y - ROUTE_GUTTER))
            values.append(min(canvas_h - 8.0, box.y + box.h + ROUTE_GUTTER))
        values.extend(gap_midpoints([(box.y, box.y + box.h) for box in boxes.values()]))
        values.extend(
            [
                max(8.0, min_y - ROUTE_GUTTER),
                min(canvas_h - 8.0, max_y + ROUTE_GUTTER),
            ]
        )

    deduped = expand_lane_bundle_candidates(values, min_axis, max_axis)
    return sorted(
        deduped,
        key=lambda value: (
            lane_excursion_penalty(mode, value, start_stub, end_stub),
            abs(value - default_lane),
            value,
        ),
    )


def best_route_points(
    rel_id: str,
    src_id: str,
    dst_id: str,
    start: Tuple[float, float],
    end: Tuple[float, float],
    src_side: str,
    dst_side: str,
    all_boxes: Dict[str, Box],
    canvas_w: float,
    canvas_h: float,
    port_info: Dict[str, Any] | None = None,
    used_bundle_lanes: Sequence[float] | None = None,
) -> Tuple[List[Tuple[float, float]], set[str], float, float, int, float]:
    src_box = all_boxes.get(src_id)
    dst_box = all_boxes.get(dst_id)
    start_stub = offset_point(start, src_side, EDGE_EGRESS_STUB)
    end_stub = offset_point(end, dst_side, EDGE_EGRESS_STUB)
    source_lane_bias = float(port_info.get("source_lane_bias", 0.0)) if port_info else 0.0
    target_lane_bias = float(port_info.get("target_lane_bias", 0.0)) if port_info else 0.0
    offset = target_lane_bias if abs(target_lane_bias) > ROUTING_EPSILON else 0.0
    if abs(offset) <= ROUTING_EPSILON and abs(source_lane_bias) > ROUTING_EPSILON:
        offset = source_lane_bias
    if abs(offset) <= ROUTING_EPSILON:
        offset = ((stable_number(rel_id) % 5) - 2) * ROUTE_BUNDLE_SPACING
    mode = route_mode(src_side, dst_side)
    default_lane = (
        (start_stub[0] + end_stub[0]) / 2.0 + offset
        if mode == "mid_x"
        else (start_stub[1] + end_stub[1]) / 2.0 + offset
    )
    ignore_ids = {src_id, dst_id}
    lane_candidates = candidate_lane_values(mode, default_lane, all_boxes, canvas_w, canvas_h, start_stub, end_stub)

    best_points: List[Tuple[float, float]] = []
    best_score: Tuple[float, ...] | None = None
    best_blockers: set[str] = set()
    best_clearance = 0.0
    best_endpoint_penalty = 0
    best_lane = default_lane
    for lane_value in lane_candidates:
        candidate = collapse_orthogonal_points(build_route_points(start, start_stub, end_stub, end, lane_value, mode))
        blockers = route_blockers(candidate, all_boxes, ignore_ids)
        endpoint_penalty = route_endpoint_interior_penalty(candidate, src_box, dst_box)
        clearance = route_min_clearance(candidate, all_boxes, ignore_ids)
        score = (
            len(blockers),
            float(endpoint_penalty),
            max(0.0, ROUTE_CLEARANCE_TARGET - clearance),
            route_lane_reuse_penalty(used_bundle_lanes or [], lane_value),
            lane_excursion_penalty(mode, lane_value, start_stub, end_stub),
            approximate_route_length(candidate),
            abs(lane_value - default_lane),
            0.0,
        )
        if best_score is None or score < best_score:
            best_score = score
            best_points = candidate
            best_blockers = blockers
            best_clearance = clearance
            best_endpoint_penalty = endpoint_penalty
            best_lane = lane_value
            if not blockers and endpoint_penalty == 0 and clearance >= ROUTE_CLEARANCE_TARGET:
                break

    if best_blockers or best_endpoint_penalty > 0 or best_clearance < ROUTE_CLEARANCE_TARGET:
        detour_values = detour_axis_values(mode, sorted(best_blockers), all_boxes, canvas_w, canvas_h, start_stub, end_stub)
        lane_trials = dedupe_lane_values([best_lane, default_lane] + lane_candidates[:8])
        for lane_value in lane_trials:
            for detour_value in detour_values:
                candidate = collapse_orthogonal_points(
                    build_detour_route_points(start, start_stub, end_stub, end, lane_value, detour_value, mode)
                )
                blockers = route_blockers(candidate, all_boxes, ignore_ids)
                endpoint_penalty = route_endpoint_interior_penalty(candidate, src_box, dst_box)
                clearance = route_min_clearance(candidate, all_boxes, ignore_ids)
                score = (
                    len(blockers),
                    float(endpoint_penalty),
                    max(0.0, ROUTE_CLEARANCE_TARGET - clearance),
                    route_lane_reuse_penalty(used_bundle_lanes or [], lane_value),
                    lane_excursion_penalty(mode, lane_value, start_stub, end_stub),
                    detour_excursion_penalty(mode, detour_value, start_stub, end_stub),
                    approximate_route_length(candidate),
                    abs(lane_value - default_lane),
                    abs(detour_value - detour_baseline_coordinate(mode, start_stub, end_stub)),
                )
                if best_score is None or score < best_score:
                    best_score = score
                    best_points = candidate
                    best_blockers = blockers
                    best_clearance = clearance
                    best_endpoint_penalty = endpoint_penalty
                    best_lane = lane_value
                    if not blockers and endpoint_penalty == 0 and clearance >= ROUTE_CLEARANCE_TARGET:
                        return best_points, best_blockers, best_clearance, approximate_route_length(best_points), best_endpoint_penalty, lane_value

    fallback = best_points or collapse_orthogonal_points(build_route_points(start, start_stub, end_stub, end, default_lane, mode))
    fallback_blockers = best_blockers if best_points else route_blockers(fallback, all_boxes, ignore_ids)
    fallback_clearance = best_clearance if best_points else route_min_clearance(fallback, all_boxes, ignore_ids)
    fallback_endpoint_penalty = best_endpoint_penalty if best_points else route_endpoint_interior_penalty(fallback, src_box, dst_box)
    return fallback, fallback_blockers, fallback_clearance, approximate_route_length(fallback), fallback_endpoint_penalty, best_lane if best_points else default_lane


def orthogonal_points(
    rel_id: str,
    src_id: str,
    dst_id: str,
    src: Box,
    dst: Box,
    all_boxes: Dict[str, Box],
    canvas_w: float,
    canvas_h: float,
    edge_ports: Dict[str, Dict[str, Any]] | None = None,
    lane_usage: Dict[str, List[float]] | None = None,
) -> List[Tuple[float, float]]:
    port_info = edge_ports.get(rel_id, {}) if edge_ports else {}
    src_side = str(port_info.get("source_side") or preferred_port_side(src, dst))
    dst_side = str(port_info.get("target_side") or preferred_port_side(dst, src))
    start = tuple(port_info.get("source_anchor") or anchor_point(src, src_side))
    end = tuple(port_info.get("target_anchor") or anchor_point(dst, dst_side))
    mode = route_mode(src_side, dst_side)
    bundle_key = route_bundle_key(src_id, dst_id, src_side, dst_side, mode, port_info)
    points, _, _, _, _, lane_value = best_route_points(
        rel_id,
        src_id,
        dst_id,
        start,
        end,
        src_side,
        dst_side,
        all_boxes,
        canvas_w,
        canvas_h,
        port_info,
        lane_usage.get(bundle_key, []) if lane_usage else [],
    )
    remember_route_lane(lane_usage, bundle_key, lane_value)
    return points


def rounded_polyline(points: Sequence[Tuple[float, float]], radius: float = 10.0) -> str:
    if len(points) < 2:
        return ""

    path = [f"M {points[0][0]:.1f} {points[0][1]:.1f}"]
    for idx in range(1, len(points) - 1):
        px, py = points[idx - 1]
        cx, cy = points[idx]
        nx, ny = points[idx + 1]

        in_dx = cx - px
        in_dy = cy - py
        out_dx = nx - cx
        out_dy = ny - cy
        in_len = math.hypot(in_dx, in_dy) or 1.0
        out_len = math.hypot(out_dx, out_dy) or 1.0
        r = min(radius, in_len / 2.0, out_len / 2.0)

        sx = cx - in_dx / in_len * r
        sy = cy - in_dy / in_len * r
        ex = cx + out_dx / out_len * r
        ey = cy + out_dy / out_len * r

        path.append(f"L {sx:.1f} {sy:.1f}")
        path.append(f"Q {cx:.1f} {cy:.1f} {ex:.1f} {ey:.1f}")

    last_x, last_y = points[-1]
    path.append(f"L {last_x:.1f} {last_y:.1f}")
    return " ".join(path)


def label_for_polyline(points: Sequence[Tuple[float, float]]) -> Tuple[float, float, float]:
    if len(points) < 2:
        return 0.0, 0.0, 0.0

    segments = []
    for idx in range(len(points) - 1):
        x1, y1 = points[idx]
        x2, y2 = points[idx + 1]
        length = math.hypot(x2 - x1, y2 - y1)
        segments.append((length, x1, y1, x2, y2))

    _, x1, y1, x2, y2 = max(segments, key=lambda item: item[0])
    lx = (x1 + x2) / 2.0
    ly = (y1 + y2) / 2.0
    angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
    if angle > 90:
        angle -= 180
    elif angle < -90:
        angle += 180

    length = math.hypot(x2 - x1, y2 - y1) or 1.0
    nx = -(y2 - y1) / length
    ny = (x2 - x1) / length
    return lx + nx * 8.0, ly + ny * 8.0, angle


def normalize_edge_label(text: str) -> str:
    return " ".join(str(text or "").split())


def wrap_edge_label_lines(text: str) -> List[str]:
    normalized = normalize_edge_label(text)
    if not normalized:
        return []
    if len(normalized) <= 26 or " " not in normalized:
        return [normalized]

    words = normalized.split(" ")
    best_lines: Optional[List[str]] = None
    best_score: Optional[Tuple[int, int, int]] = None
    for idx in range(1, len(words)):
        left = " ".join(words[:idx])
        right = " ".join(words[idx:])
        max_len = max(len(left), len(right))
        diff = abs(len(left) - len(right))
        overage = max(0, max_len - 30)
        score = (overage, max_len, diff)
        if best_score is None or score < best_score:
            best_score = score
            best_lines = [left, right]

    return best_lines or [normalized]


def draw_edge(
    edge: Edge,
    src_box: Box,
    dst_box: Box,
    view_id: str,
    all_boxes: Dict[str, Box],
    canvas_w: float,
    canvas_h: float,
    edge_ports: Dict[str, Dict[str, Any]] | None = None,
    lane_usage: Dict[str, List[float]] | None = None,
    color: str = "var(--color-border-strong)",
) -> str:
    points = orthogonal_points(
        edge.id,
        edge.source_id,
        edge.target_id,
        src_box,
        dst_box,
        all_boxes,
        canvas_w,
        canvas_h,
        edge_ports,
        lane_usage,
    )
    path_data = rounded_polyline(points)
    return (
        f"<g data-relationship-id=\"{esc(edge.id)}\" data-view-id=\"{esc(view_id)}\" "
        f"data-target-label=\"{esc(edge.label or edge.id)}\">\n"
        f"    <path d=\"{path_data}\" stroke=\"{color}\" stroke-width=\"1.5\" fill=\"none\" marker-end=\"url(#arrow)\" />\n"
        f"    <path d=\"{path_data}\" stroke=\"transparent\" stroke-width=\"14\" fill=\"none\" />\n"
        f"  </g>"
    )


def top_header_band_path(x: float, y: float, width: float, height: float, radius: float = 12.0) -> str:
    usable_height = max(height, 0.0)
    usable_radius = min(radius, width / 2.0, usable_height)
    return (
        f"M {x + usable_radius:.1f} {y:.1f} "
        f"H {x + width - usable_radius:.1f} "
        f"Q {x + width:.1f} {y:.1f} {x + width:.1f} {y + usable_radius:.1f} "
        f"V {y + usable_height:.1f} "
        f"H {x:.1f} "
        f"V {y + usable_radius:.1f} "
        f"Q {x:.1f} {y:.1f} {x + usable_radius:.1f} {y:.1f} Z"
    )


def draw_node(node: Node, box: Box, view_id: str) -> str:
    fill, stroke, tone = kind_colors(node.kind)
    width, height, name_lines, subtitle_lines = node_dimensions(node)
    _ = width, height

    x, y, w, h = box.x, box.y, box.w, box.h
    header_h = NODE_HEADER_BAND_H
    lines: List[str] = []
    synthetic_attr = ' data-synthetic="true"' if node.synthetic else ""
    lines.append(
        f"<g class=\"diagram-node\" data-element=\"{tone}\" data-element-id=\"{esc(node.id)}\" "
        f"data-view-id=\"{esc(view_id)}\" data-target-label=\"{esc(node.name)}\"{synthetic_attr}>"
    )
    lines.append(
        f"  <rect x=\"{x:.1f}\" y=\"{y:.1f}\" width=\"{w:.1f}\" height=\"{h:.1f}\" rx=\"12\" fill=\"{fill}\" "
        f"stroke=\"{stroke}\" stroke-width=\"2\" />"
    )
    lines.append(
        f"  <path d=\"{top_header_band_path(x, y, w, header_h)}\" data-node-header=\"true\" fill=\"{stroke}\" fill-opacity=\"0.18\" />"
    )
    lines.append(
        f"  <text x=\"{x + w/2:.1f}\" y=\"{y + header_h/2.0 + NODE_HEADER_TEXT_NUDGE_Y:.1f}\" text-anchor=\"middle\" dominant-baseline=\"middle\" font-size=\"9\" font-weight=\"600\" "
        f"fill=\"var(--color-text-primary)\">{esc(type_header(node.kind, node.technology))}</text>"
    )

    line_y = y + 52.0
    for text in name_lines:
        lines.append(
            f"  <text x=\"{x + w/2:.1f}\" y=\"{line_y:.1f}\" text-anchor=\"middle\" font-size=\"14\" font-weight=\"600\" "
            f"fill=\"var(--color-text-primary)\">{esc(text)}</text>"
        )
        line_y += 18.0
    for text in subtitle_lines:
        lines.append(
            f"  <text x=\"{x + w/2:.1f}\" y=\"{line_y:.1f}\" text-anchor=\"middle\" font-size=\"11\" "
            f"fill=\"var(--color-text-secondary)\">{esc(text)}</text>"
        )
        line_y += 15.0

    lines.append("</g>")
    return "\n  ".join(lines)


def draw_boundary(boundary: Boundary) -> str:
    fill, stroke = boundary_style(boundary.tone)
    x, y, w, h = boundary.x, boundary.y, boundary.w, boundary.h
    return (
        f"<rect x=\"{x:.1f}\" y=\"{y:.1f}\" width=\"{w:.1f}\" height=\"{h:.1f}\" rx=\"14\" fill=\"{fill}\" "
        f"stroke=\"{stroke}\" stroke-width=\"1\" stroke-dasharray=\"4 4\" />\n"
        f"  <text x=\"{x + 16:.1f}\" y=\"{y + 22:.1f}\" font-size=\"11\" fill=\"var(--color-text-tertiary)\" "
        f"font-weight=\"700\" letter-spacing=\"0.08em\">{esc(boundary.label)}</text>"
    )


def render_view_fragment(
    view: Dict[str, Any],
    model_elements: Dict[str, Node],
    model_edges: Dict[str, Edge],
    out_file: Path,
    system_name: str,
) -> None:
    element_ids = [eid for eid in (view.get("element_ids") or []) if isinstance(eid, str)]
    nodes = normalize_nodes({nid: node.__dict__ for nid, node in model_elements.items()}, element_ids)
    render_order_ids = list(element_ids)
    system_anchor: Node | None = None
    if normalize_view_type(str(view.get("type", ""))) == "system_context":
        system_nodes = [node for node in nodes if is_system_like_kind(node.kind)]
        system_anchor = system_nodes[0] if system_nodes else build_synthetic_system_node(str(view.get("id", "")), system_name)
        if not system_nodes:
            nodes.append(system_anchor)
            render_order_ids.append(system_anchor.id)

    node_map = {node.id: node for node in nodes}
    visible_ids = set(node_map)

    if not nodes:
        return

    raw_edges = collect_view_edges(view, model_edges, visible_ids)
    layout = trim_horizontal_layout_padding(choose_layout(view, nodes, model_elements, raw_edges))
    edges: List[Edge] = []
    for edge in raw_edges:
        source_id = edge.source_id
        target_id = edge.target_id
        if system_anchor and source_id not in visible_ids and is_internal_model_node(model_elements.get(source_id)):
            source_id = system_anchor.id
        if system_anchor and target_id not in visible_ids and is_internal_model_node(model_elements.get(target_id)):
            target_id = system_anchor.id
        if source_id not in layout.boxes or target_id not in layout.boxes or source_id == target_id:
            continue
        edges.append(
            Edge(
                id=edge.id,
                source_id=source_id,
                target_id=target_id,
                label=edge.label,
            )
        )

    edge_ports = assign_edge_ports(edges, layout.boxes, layout.width, layout.height)
    lane_usage: Dict[str, List[float]] = {}
    edge_markup: List[str] = []
    seen_pairs: set[Tuple[str, str, str]] = set()
    for edge in edges:
        dedupe_key = (edge.source_id, edge.target_id, edge.label)
        if dedupe_key in seen_pairs:
            continue
        seen_pairs.add(dedupe_key)
        edge_markup.append(
            draw_edge(
                edge,
                layout.boxes[edge.source_id],
                layout.boxes[edge.target_id],
                str(view.get("id", "view")),
                layout.boxes,
                layout.width,
                layout.height,
                edge_ports,
                lane_usage,
            )
        )

    node_markup = [
        draw_node(node_map[nid], layout.boxes[nid], str(view.get("id", "view")))
        for nid in render_order_ids
        if nid in node_map and nid in layout.boxes
    ]
    boundary_markup = [draw_boundary(boundary) for boundary in layout.boundaries]

    boundary_text = "\n  ".join(boundary_markup)
    edge_text = "\n  ".join(edge_markup)
    node_text = "\n  ".join(node_markup)

    svg = f"""<svg viewBox=\"0 0 {layout.width:.0f} {layout.height:.0f}\" width=\"{layout.width:.0f}\" height=\"{layout.height:.0f}\" xmlns=\"http://www.w3.org/2000/svg\" data-routing-version=\"{FRAGMENT_ROUTING_VERSION}\">
  <defs>
    <marker id=\"arrow\" markerWidth=\"10\" markerHeight=\"10\" refX=\"8\" refY=\"5\" orient=\"auto\">
      <path d=\"M0,0 L10,5 L0,10 z\" fill=\"var(--color-border-strong)\" />
    </marker>
  </defs>
  {boundary_text}
  {edge_text}
  {node_text}
</svg>
"""

    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(svg, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate SVG fragments from architecture artifacts")
    ap.add_argument("--output-root", required=True)
    args = ap.parse_args()

    root = Path(args.output_root).expanduser().resolve()
    validate_artifact_contract(root)
    arch = root / "architecture"
    manifest = load_yaml(arch / "manifest.yaml")
    model = load_yaml(arch / "model.yaml")
    system_name = str(manifest.get("system_name") or model.get("system_name") or "Architecture")
    views_dir = arch / "views"
    out_dir = root / "architecture" / RUNTIME_DIR / "diagram-svg"
    out_dir.mkdir(parents=True, exist_ok=True)

    elements: Dict[str, Node] = {}
    for raw in (model.get("elements") or []):
        if not isinstance(raw, dict) or not raw.get("id"):
            continue
        node = Node(
            id=str(raw["id"]),
            name=str(raw.get("name", raw["id"])),
            kind=str(raw.get("kind", "")),
            technology=str(raw.get("technology", "")),
            description=str(raw.get("description", "")),
            responsibility=str(raw.get("responsibility", "")),
            external=bool(raw.get("external")),
            parent_id=str(raw.get("parent_id")) if raw.get("parent_id") else None,
        )
        elements[node.id] = node

    rels: Dict[str, Edge] = {}
    for raw in (model.get("relationships") or []):
        if not isinstance(raw, dict) or not raw.get("id"):
            continue
        if not raw.get("source_id") or not raw.get("target_id"):
            continue
        edge = Edge(
            id=str(raw["id"]),
            source_id=str(raw["source_id"]),
            target_id=str(raw["target_id"]),
            label=str(raw.get("label", "")),
        )
        rels[edge.id] = edge

    for vf in sorted(
        [path for path in views_dir.rglob("*") if path.is_file() and path.suffix in {".yaml", ".yml"}],
        key=lambda path: path.relative_to(views_dir).as_posix(),
    ):
        view = load_yaml(vf)
        if normalize_view_type(str(view.get("type", ""))) == "sequence":
            continue
        view["id"] = view.get("id") or vf.stem
        render_view_fragment(view, elements, rels, out_dir / f"{view['id']}.svg", system_name)

    (out_dir / "_metadata.json").write_text(
        json.dumps(
            {
                "revision_id": compute_revision_id(root),
                "svg_dir": out_dir.name,
            },
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    print(str(out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
