#!/usr/bin/env python3
"""Generate generic SVG fragments from architecture artifacts.

Creates per-view SVG fragments under <output-root>/diagram-svg so the renderer
can run in rich/demo mode without falling back to the in-template layout path.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple
import xml.etree.ElementTree as ET

import yaml


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
COLUMN_GAP = 68.0
ROW_GAP = 34.0
BOUNDARY_PAD = 28.0
CARD_MIN_W = 180.0
CARD_MAX_W = 320.0


def load_yaml(path: Path) -> Dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


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
    tech = short_text(technology, 20)

    if k == "person":
        return "[Person]"
    if k == "external_system":
        return "[External System]"
    if k in {"software_system", "system"}:
        return "[Software System]"
    if k == "component":
        return "[Component]"
    if k == "deployment_node":
        return "[Deployment Node]"
    if k == "database":
        return "[Container: Database]"
    if k in {"queue", "cache"}:
        return "[Container: Cache/Queue]"
    if k == "container" and tech:
        return f"[Container: {tech}]"
    if k == "container":
        return "[Container]"
    return f"[{kind or 'Element'}]"


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


def is_component_kind(kind: str) -> bool:
    return normalize_kind(kind) == "component"


def kind_colors(kind: str) -> Tuple[str, str, str]:
    k = normalize_kind(kind)
    if k == "person":
        return "#31466b", "#7d98c2", "#3a527c"
    if k == "external_system":
        return "#3d4556", "#8b98ae", "#4a556a"
    if k in {"database", "queue", "cache"}:
        if k == "queue":
            return "#363345", "#8b7ca8", "#443d58"
        return "#2d3445", "#73839e", "#39455b"
    if k in {"software_system", "system"}:
        return "#2c4c78", "#73a0d8", "#365f95"
    if k == "component":
        return "#244c57", "#72aeb6", "#2c5d69"
    return "#295164", "#6ea2bb", "#33667e"


def boundary_style(tone: str) -> Tuple[str, str]:
    if tone == "deployment":
        return "rgba(26, 34, 48, 0.38)", "#5e7396"
    if tone == "container":
        return "rgba(20, 31, 54, 0.26)", "#506385"
    return "rgba(24, 34, 58, 0.25)", "#4f617f"


def node_dimensions(node: Node, max_width: float = CARD_MAX_W) -> Tuple[float, float, List[str], List[str]]:
    subtitle = node_subtitle(node)
    header = type_header(node.kind, node.technology)
    name_lines = wrap_text(node.name, 24, 2)
    subtitle_lines = wrap_text(subtitle, 28, 2) if subtitle else []

    width_hint = max(
        approx_text_width(header, 9),
        max((approx_text_width(line, 16) for line in name_lines), default=0.0),
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


def container_layout(nodes: Sequence[Node]) -> LayoutResult:
    system_nodes = [n for n in nodes if normalize_kind(n.kind) in {"software_system", "system"} and not n.external]
    actors = [n for n in nodes if normalize_kind(n.kind) == "person"]
    stores = [n for n in nodes if is_store_kind(n.kind)]
    externals = [n for n in nodes if normalize_kind(n.kind) == "external_system"]
    core = [n for n in nodes if n not in system_nodes and n not in actors and n not in stores and n not in externals]

    visible_nodes = actors + core + stores + externals
    sizes = {n.id: node_dimensions(n)[:2] for n in visible_nodes}

    left_boxes, left_w = place_vertical([n.id for n in actors], sizes, VIEW_MARGIN_X, VIEW_MARGIN_Y + 74.0)

    boundary_start_x = VIEW_MARGIN_X + (left_w if actors else 0.0) + (COLUMN_GAP if actors and (core or stores) else 0.0)
    core_boxes, core_w, core_h = place_grid(
        [n.id for n in core],
        sizes,
        boundary_start_x + BOUNDARY_PAD,
        VIEW_MARGIN_Y + 104.0,
        columns=2 if len(core) > 3 else 1,
        gap_y=40.0,
    )

    stores_start_y = VIEW_MARGIN_Y + 128.0 + core_h
    store_boxes, store_w, store_h = place_grid(
        [n.id for n in stores],
        sizes,
        boundary_start_x + BOUNDARY_PAD,
        stores_start_y,
        columns=min(max(len(stores), 1), 3),
        gap_x=42.0,
        gap_y=30.0,
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

    right_start_x = boundary_start_x + boundary_w + (COLUMN_GAP if externals else 0.0)
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
                label=f"{boundary_label} [System Boundary]",
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
            label=f"{boundary_label} [Container Boundary]",
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
) -> LayoutResult:
    view_type = normalize_view_type(str(view.get("type", "")))
    if view_type == "system_context":
        return system_context_layout(nodes)
    if view_type == "container":
        return container_layout(nodes)
    if view_type == "component":
        return component_layout(nodes, view.get("parent_container_id"), all_nodes)
    if view_type == "deployment":
        return deployment_layout(nodes, view, all_nodes)
    return generic_layout(nodes)


def anchor_point(src: Box, dst: Box) -> Tuple[float, float]:
    cx = src.x + src.w / 2.0
    cy = src.y + src.h / 2.0
    dx = dst.x + dst.w / 2.0 - cx
    dy = dst.y + dst.h / 2.0 - cy

    if dx == 0 and dy == 0:
        return cx, cy

    tx = (src.w / 2.0) / abs(dx) if dx != 0 else float("inf")
    ty = (src.h / 2.0) / abs(dy) if dy != 0 else float("inf")
    t = min(tx, ty)
    return cx + dx * t, cy + dy * t


def orthogonal_points(rel_id: str, src: Box, dst: Box) -> List[Tuple[float, float]]:
    x1, y1 = anchor_point(src, dst)
    x2, y2 = anchor_point(dst, src)
    dx = x2 - x1
    dy = y2 - y1
    offset = ((stable_number(rel_id) % 5) - 2) * 10.0

    if abs(dx) >= abs(dy):
        mid_x = (x1 + x2) / 2.0 + offset
        return [(x1, y1), (mid_x, y1), (mid_x, y2), (x2, y2)]

    mid_y = (y1 + y2) / 2.0 + offset
    return [(x1, y1), (x1, mid_y), (x2, mid_y), (x2, y2)]


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


def draw_edge(edge: Edge, src_box: Box, dst_box: Box, view_id: str, color: str = "#90a7cf") -> str:
    points = orthogonal_points(edge.id, src_box, dst_box)
    path_data = rounded_polyline(points)
    lx, ly, angle = label_for_polyline(points)
    short = short_text(edge.label or edge.id, 36)
    return f"""
  <g data-relationship-id=\"{esc(edge.id)}\" data-view-id=\"{esc(view_id)}\" data-target-label=\"{esc(edge.label or edge.id)}\">
    <path d=\"{path_data}\" stroke=\"{color}\" stroke-width=\"1.15\" fill=\"none\" marker-end=\"url(#arrow)\" data-relationship-surface=\"visible\" />
    <path d=\"{path_data}\" stroke=\"transparent\" stroke-width=\"14\" fill=\"none\" data-relationship-surface=\"hit\" />
    <text x=\"{lx:.1f}\" y=\"{ly:.1f}\" transform=\"rotate({angle:.1f} {lx:.1f} {ly:.1f})\" text-anchor=\"middle\"
          font-size=\"9\" fill=\"#95a9c9\" data-relationship-text-role=\"label\">{esc(short)}</text>
  </g>
""".rstrip()


def draw_node(node: Node, box: Box, view_id: str) -> str:
    fill, stroke, header_fill = kind_colors(node.kind)
    width, height, name_lines, subtitle_lines = node_dimensions(node)
    _ = width, height

    x, y, w, h = box.x, box.y, box.w, box.h
    header_h = 22.0
    lines: List[str] = []
    lines.append(
        f"<g data-element-id=\"{esc(node.id)}\" data-view-id=\"{esc(view_id)}\" data-target-label=\"{esc(node.name)}\" data-node-layout=\"card\">"
    )
    lines.append(
        f"  <rect x=\"{x:.1f}\" y=\"{y:.1f}\" width=\"{w:.1f}\" height=\"{h:.1f}\" rx=\"12\" fill=\"{fill}\" stroke=\"{stroke}\" stroke-width=\"1.2\" data-node-surface=\"body\" />"
    )
    lines.append(
        f"  <path d=\"M {x+1:.1f} {y+header_h:.1f} L {x+1:.1f} {y+12:.1f} Q {x+1:.1f} {y+1:.1f} {x+12:.1f} {y+1:.1f} "
        f"L {x+w-12:.1f} {y+1:.1f} Q {x+w-1:.1f} {y+1:.1f} {x+w-1:.1f} {y+12:.1f} L {x+w-1:.1f} {y+header_h:.1f} Z\" fill=\"{header_fill}\" data-node-surface=\"header\" />"
    )
    lines.append(
        f"  <text x=\"{x + w/2:.1f}\" y=\"{y + 15:.1f}\" text-anchor=\"middle\" font-size=\"9\" font-weight=\"700\" fill=\"#c7d8f2\" pointer-events=\"none\" data-node-text-role=\"kind\">{esc(type_header(node.kind, node.technology))}</text>"
    )

    line_y = y + header_h + 26.0
    for text in name_lines:
        lines.append(
            f"  <text x=\"{x + w/2:.1f}\" y=\"{line_y:.1f}\" text-anchor=\"middle\" font-size=\"16\" font-weight=\"700\" fill=\"#e8f0ff\" pointer-events=\"none\" data-node-text-role=\"title\">{esc(text)}</text>"
        )
        line_y += 18.0
    for text in subtitle_lines:
        lines.append(
            f"  <text x=\"{x + w/2:.1f}\" y=\"{line_y:.1f}\" text-anchor=\"middle\" font-size=\"11\" fill=\"#c5d3e8\" pointer-events=\"none\" data-node-text-role=\"subtitle\">{esc(text)}</text>"
        )
        line_y += 15.0

    lines.append("</g>")
    return "\n  ".join(lines)


def draw_boundary(boundary: Boundary) -> str:
    fill, stroke = boundary_style(boundary.tone)
    x, y, w, h = boundary.x, boundary.y, boundary.w, boundary.h
    return (
        f"<rect x=\"{x:.1f}\" y=\"{y:.1f}\" width=\"{w:.1f}\" height=\"{h:.1f}\" rx=\"14\" fill=\"{fill}\" "
        f"stroke=\"{stroke}\" stroke-dasharray=\"5 4\" />\n"
        f"  <text x=\"{x + 16:.1f}\" y=\"{y + 22:.1f}\" font-size=\"11\" fill=\"#99aecb\" font-weight=\"700\">{esc(boundary.label)}</text>"
    )


def render_view_fragment(
    view: Dict[str, Any],
    model_elements: Dict[str, Node],
    model_edges: Dict[str, Edge],
    out_file: Path,
) -> None:
    element_ids = [eid for eid in (view.get("element_ids") or []) if isinstance(eid, str)]
    nodes = normalize_nodes({nid: node.__dict__ for nid, node in model_elements.items()}, element_ids)
    node_map = {node.id: node for node in nodes}
    visible_ids = set(node_map)

    if not nodes:
        return

    layout = choose_layout(view, nodes, model_elements)
    edges = collect_view_edges(view, model_edges, visible_ids)

    edge_markup: List[str] = []
    seen_pairs: set[Tuple[str, str, str]] = set()
    for edge in edges:
        if edge.source_id not in layout.boxes or edge.target_id not in layout.boxes:
            continue
        if edge.source_id == edge.target_id:
            continue
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
            )
        )

    node_markup = [
        draw_node(node_map[nid], layout.boxes[nid], str(view.get("id", "view")))
        for nid in element_ids
        if nid in node_map and nid in layout.boxes
    ]
    boundary_markup = [draw_boundary(boundary) for boundary in layout.boundaries]

    boundary_text = "\n  ".join(boundary_markup)
    edge_text = "\n  ".join(edge_markup)
    node_text = "\n  ".join(node_markup)

    svg = f"""<svg viewBox=\"0 0 {layout.width:.0f} {layout.height:.0f}\" width=\"{layout.width:.0f}\" height=\"{layout.height:.0f}\" xmlns=\"http://www.w3.org/2000/svg\">
  <defs>
    <marker id=\"arrow\" markerWidth=\"10\" markerHeight=\"10\" refX=\"8\" refY=\"5\" orient=\"auto\">
      <path d=\"M0,0 L10,5 L0,10 z\" fill=\"#90a7cf\" />
    </marker>
  </defs>
  <rect x=\"0\" y=\"0\" width=\"{layout.width:.0f}\" height=\"{layout.height:.0f}\" fill=\"#0b1020\" />
  {boundary_text}
  {edge_text}
  {node_text}
</svg>
"""

    out_file.parent.mkdir(parents=True, exist_ok=True)
    validate_interactive_targets(svg, str(view.get("id", out_file.stem)))
    out_file.write_text(svg, encoding="utf-8")


def local_tag(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def has_descendant_with_attr(el: ET.Element, attr: str, value: str | None = None) -> bool:
    for child in el.iter():
        if child is el:
            continue
        if attr not in child.attrib:
            continue
        if value is None or child.attrib.get(attr) == value:
            return True
    return False


def validate_interactive_targets(svg_text: str, view_id: str) -> None:
    try:
        root = ET.fromstring(svg_text)
    except ET.ParseError as exc:
        raise ValueError(f"{view_id}: generated SVG fragment is invalid XML: {exc}") from exc

    for el in root.iter():
        element_id = el.attrib.get("data-element-id")
        if element_id:
            if local_tag(el.tag) != "g":
                raise ValueError(
                    f"{view_id}: interactive node target {element_id!r} must be a <g> so the full card resolves to one element"
                )
            if not has_descendant_with_attr(el, "data-node-surface", "body"):
                raise ValueError(
                    f"{view_id}: interactive node target {element_id!r} is missing its card body surface"
                )

        relationship_id = el.attrib.get("data-relationship-id")
        if relationship_id:
            if local_tag(el.tag) != "g":
                raise ValueError(
                    f"{view_id}: interactive relationship target {relationship_id!r} must be a <g> so labels resolve to the edge"
                )
            if not has_descendant_with_attr(el, "data-relationship-surface", "hit"):
                raise ValueError(
                    f"{view_id}: interactive relationship target {relationship_id!r} is missing its enlarged hit surface"
                )


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate SVG fragments from architecture artifacts")
    ap.add_argument("--output-root", required=True)
    args = ap.parse_args()

    root = Path(args.output_root).expanduser().resolve()
    arch = root / "architecture"
    model = load_yaml(arch / "model.yaml")
    views_dir = arch / "views"
    out_dir = root / "diagram-svg"
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

    for vf in sorted(views_dir.glob("*.y*ml")):
        view = load_yaml(vf)
        if normalize_view_type(str(view.get("type", ""))) == "sequence":
            continue
        view["id"] = view.get("id") or vf.stem
        render_view_fragment(view, elements, rels, out_dir / f"{view['id']}.svg")

    print(str(out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
