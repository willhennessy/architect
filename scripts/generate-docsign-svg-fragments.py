#!/usr/bin/env python3
"""Generate SVG fragments for DocSign test runs.

Creates per-view SVG fragments under <output-root>/architecture/.out/diagram-svg
so the renderer can run in --demo-mode without fallback.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml


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


def short_tech(tech: str, max_len: int = 24) -> str:
    t = " ".join(str(tech or "").replace("\n", " ").split())
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def type_header(kind: str, technology: str) -> str:
    k = (kind or "").lower()
    tech = short_tech(technology)

    if k == "person":
        return "[Person]"
    if k == "external_system":
        return "[External System]"
    if k in {"software_system", "system"}:
        return "[Software System]"
    if k == "database":
        return "[Container: Database]"
    if k in {"queue", "cache"}:
        return "[Container: Cache/Queue]"
    if k == "container" and tech:
        return f"[Container: {tech}]"
    return "[Container]"


def anchor_point(src: Dict[str, float], dst: Dict[str, float]) -> Tuple[float, float]:
    sx, sy, sw, sh = src["x"], src["y"], src["w"], src["h"]
    cx, cy = sx + sw / 2.0, sy + sh / 2.0
    dx, dy = dst["x"] + dst["w"] / 2.0 - cx, dst["y"] + dst["h"] / 2.0 - cy

    if dx == 0 and dy == 0:
        return cx, cy

    tx = (sw / 2.0) / abs(dx) if dx != 0 else float("inf")
    ty = (sh / 2.0) / abs(dy) if dy != 0 else float("inf")
    t = min(tx, ty)
    return cx + dx * t, cy + dy * t


def draw_edge(
    rel_id: str,
    label: str,
    src_box: Dict[str, float],
    dst_box: Dict[str, float],
    view_id: str,
    color: str = "#8098bf",
) -> str:
    x1, y1 = anchor_point(src_box, dst_box)
    x2, y2 = anchor_point(dst_box, src_box)

    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy) or 1.0

    # Graceful curved edge with deterministic side selection.
    nx, ny = (-(dy) / length, dx / length)
    side = -1 if (sum(ord(c) for c in rel_id) % 2) else 1
    curve = min(110.0, max(28.0, length * 0.16)) * side
    cx, cy = (x1 + x2) / 2.0 + nx * curve, (y1 + y2) / 2.0 + ny * curve

    # Label near bezier midpoint.
    t = 0.56
    omt = 1.0 - t
    lx = omt * omt * x1 + 2 * omt * t * cx + t * t * x2
    ly = omt * omt * y1 + 2 * omt * t * cy + t * t * y2

    tx = 2 * omt * (cx - x1) + 2 * t * (x2 - cx)
    ty = 2 * omt * (cy - y1) + 2 * t * (y2 - cy)
    tlen = math.hypot(tx, ty) or 1.0
    tnx, tny = -ty / tlen, tx / tlen
    lx += tnx * 7.0
    ly += tny * 7.0

    angle = math.degrees(math.atan2(ty, tx))
    if angle > 90:
        angle -= 180
    elif angle < -90:
        angle += 180

    short = label if len(label) <= 34 else label[:33] + "…"

    return f"""
  <path d=\"M {x1:.1f} {y1:.1f} Q {cx:.1f} {cy:.1f} {x2:.1f} {y2:.1f}\" stroke=\"{color}\" stroke-width=\"1.8\" fill=\"none\" marker-end=\"url(#arrow)\" />
  <path d=\"M {x1:.1f} {y1:.1f} Q {cx:.1f} {cy:.1f} {x2:.1f} {y2:.1f}\" stroke=\"transparent\" stroke-width=\"14\" fill=\"none\"
        data-relationship-id=\"{esc(rel_id)}\" data-view-id=\"{esc(view_id)}\" data-target-label=\"{esc(label or rel_id)}\" />
  <text x=\"{lx:.1f}\" y=\"{ly:.1f}\" transform=\"rotate({angle:.1f} {lx:.1f} {ly:.1f})\" text-anchor=\"middle\"
        font-size=\"9\" fill=\"#95a9c9\">{esc(short)}</text>
""".rstrip()


def draw_node(
    node_id: str,
    name: str,
    subtitle: str,
    kind: str,
    technology: str,
    box: Dict[str, float],
    view_id: str,
    fill: str,
    stroke: str,
    header_fill: str,
) -> str:
    x, y, w, h = box["x"], box["y"], box["w"], box["h"]
    hh = 22
    header = type_header(kind, technology)

    lines = []
    lines.append(
        f"<rect x=\"{x}\" y=\"{y}\" width=\"{w}\" height=\"{h}\" rx=\"12\" fill=\"{fill}\" stroke=\"{stroke}\" stroke-width=\"1.2\" "
        f"data-element-id=\"{esc(node_id)}\" data-view-id=\"{esc(view_id)}\" data-target-label=\"{esc(name)}\" />"
    )
    lines.append(
        f"<path d=\"M {x+1} {y+hh} L {x+1} {y+12} Q {x+1} {y+1} {x+12} {y+1} L {x+w-12} {y+1} Q {x+w-1} {y+1} {x+w-1} {y+12} L {x+w-1} {y+hh} Z\" fill=\"{header_fill}\" />"
    )
    lines.append(
        f"<text x=\"{x + w/2:.1f}\" y=\"{y + 15:.1f}\" text-anchor=\"middle\" font-size=\"9\" font-weight=\"700\" fill=\"#c7d8f2\">{esc(header)}</text>"
    )
    if subtitle:
        name_y = y + h / 2 + 2
    else:
        body_h = h - hh
        # vertically center single-line title inside body when subtitle is absent
        name_y = y + hh + body_h / 2 + 6

    lines.append(
        f"<text x=\"{x + w/2:.1f}\" y=\"{name_y:.1f}\" text-anchor=\"middle\" font-size=\"16\" font-weight=\"700\" fill=\"#e8f0ff\">{esc(name)}</text>"
    )
    if subtitle:
        lines.append(
            f"<text x=\"{x + w/2:.1f}\" y=\"{y + h/2 + 24:.1f}\" text-anchor=\"middle\" font-size=\"11\" fill=\"#c5d3e8\">{esc(short_tech(subtitle, 30))}</text>"
        )
    return "\n  ".join(lines)


def element_label(e: Dict[str, Any]) -> Tuple[str, str]:
    name = str(e.get("name", e.get("id", "")))
    tech = str(e.get("technology", ""))
    return name, tech


def find(elements: Dict[str, Dict[str, Any]], key: str) -> str:
    if key in elements:
        return key
    key_l = key.lower()
    for eid, e in elements.items():
        n = str(e.get("name", "")).lower()
        if key_l in eid.lower() or key_l in n:
            return eid
    raise KeyError(f"Missing element for key: {key}")


def is_external_element(e: Dict[str, Any]) -> bool:
    if bool(e.get("external")):
        return True
    kind = str(e.get("kind", "")).lower()
    return kind in {"person", "external_system", "external_actor"}


def context_label(rel_id: str, source_id: str, target_id: str, raw_label: str) -> str:
    rid = rel_id.lower()
    sid = source_id.lower()
    tid = target_id.lower()

    if "doc-sender" in sid:
        return "creates & sends documents"
    if "document-signer" in sid:
        return "signs via magic link"
    if "platform-admin" in sid:
        return "views admin analytics dashboard"
    if "webhook" in tid:
        return "delivers webhooks (async)"
    if "email" in tid:
        return "sends emails via provider"
    if "storage" in tid or "s3" in tid:
        return "stores/retrieves PDFs"
    if "magic-link" in raw_label.lower():
        return "signs via magic link"

    return raw_label


def map_context_endpoint(eid: str, boxes: Dict[str, Dict[str, float]], model_elements: Dict[str, Dict[str, Any]], system_id: str) -> str:
    if eid in boxes:
        return eid
    e = model_elements.get(eid)
    if not e:
        return eid
    if not is_external_element(e):
        return system_id
    return eid


def kind_colors(kind: str) -> Tuple[str, str, str]:
    k = (kind or "").lower()
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
    return "#295164", "#6ea2bb", "#33667e"


def render_view_fragment(
    view: Dict[str, Any],
    model_elements: Dict[str, Dict[str, Any]],
    rels: Dict[str, Dict[str, Any]],
    out_file: Path,
) -> None:
    vid = str(view.get("id", "view"))

    if vid == "system-context":
        boxes = {
            find(model_elements, "person-doc-sender"): {"x": 80, "y": 70, "w": 220, "h": 80},
            find(model_elements, "person-document-signer"): {"x": 80, "y": 220, "w": 220, "h": 80},
            find(model_elements, "person-platform-admin"): {"x": 80, "y": 370, "w": 220, "h": 80},
            find(model_elements, "sys-docsign-platform"): {"x": 480, "y": 170, "w": 440, "h": 170},
            find(model_elements, "ext-customer-webhook-endpoint"): {"x": 1080, "y": 90, "w": 270, "h": 82},
            find(model_elements, "ext-email-provider"): {"x": 1080, "y": 230, "w": 270, "h": 82},
            find(model_elements, "ext-object-storage"): {"x": 1080, "y": 370, "w": 270, "h": 82},
        }
        width, height = 1440, 520
        boundary = (
            '<rect x="450" y="145" width="500" height="220" rx="14" fill="rgba(24,34,58,0.25)" stroke="#4f617f" stroke-dasharray="5 4" />\n'
            '  <text x="466" y="167" font-size="11" fill="#9bb0ce" font-weight="700">DocSign Platform</text>'
        )
    elif vid == "container":
        boxes = {
            find(model_elements, "person-doc-sender"): {"x": 60, "y": 120, "w": 200, "h": 76},
            find(model_elements, "person-document-signer"): {"x": 60, "y": 260, "w": 200, "h": 76},
            find(model_elements, "person-platform-admin"): {"x": 60, "y": 400, "w": 200, "h": 76},
            find(model_elements, "container-web-application"): {"x": 340, "y": 180, "w": 290, "h": 100},
            find(model_elements, "container-platform-api"): {"x": 730, "y": 180, "w": 290, "h": 100},
            find(model_elements, "container-signing-service"): {"x": 320, "y": 360, "w": 220, "h": 92},
            find(model_elements, "container-notification-service"): {"x": 590, "y": 360, "w": 220, "h": 92},
            find(model_elements, "container-webhook-service"): {"x": 860, "y": 360, "w": 220, "h": 92},
            find(model_elements, "container-audit-service"): {"x": 1130, "y": 360, "w": 220, "h": 92},
            find(model_elements, "database-postgres-primary"): {"x": 390, "y": 560, "w": 240, "h": 92},
            find(model_elements, "queue-message-queue"): {"x": 690, "y": 560, "w": 240, "h": 92},
            find(model_elements, "database-audit-log"): {"x": 990, "y": 560, "w": 240, "h": 92},
            find(model_elements, "ext-customer-webhook-endpoint"): {"x": 1410, "y": 250, "w": 250, "h": 84},
            find(model_elements, "ext-email-provider"): {"x": 1410, "y": 390, "w": 250, "h": 84},
            find(model_elements, "ext-object-storage"): {"x": 1410, "y": 530, "w": 250, "h": 84},
        }
        width, height = 1720, 760
        boundary = (
            '<rect x="300" y="150" width="1090" height="540" rx="14" fill="rgba(20,31,54,0.26)" stroke="#506385" stroke-dasharray="5 4" />\n'
            '  <text x="316" y="172" font-size="11" fill="#99aecb" font-weight="700">DocSign Platform [System Boundary]</text>'
        )
    else:
        return

    element_ids = [eid for eid in (view.get("element_ids") or []) if isinstance(eid, str)]
    relationship_ids = [rid for rid in (view.get("relationship_ids") or []) if isinstance(rid, str)]

    edges: List[str] = []
    seen: set[Tuple[str, str, str]] = set()

    for rid in relationship_ids:
        rel = rels.get(rid)
        if not rel:
            continue

        sid = rel.get("source_id")
        tid = rel.get("target_id")
        if not isinstance(sid, str) or not isinstance(tid, str):
            continue

        if vid == "system-context":
            system_id = find(model_elements, "sys-docsign-platform")
            sid = map_context_endpoint(sid, boxes, model_elements, system_id)
            tid = map_context_endpoint(tid, boxes, model_elements, system_id)

        if sid not in boxes or tid not in boxes or sid == tid:
            continue

        label = str(rel.get("label", ""))
        if vid == "system-context":
            label = context_label(rid, sid, tid, label)

        key = (sid, tid, label)
        if key in seen:
            continue
        seen.add(key)

        edges.append(draw_edge(rid, label, boxes[sid], boxes[tid], vid))

    nodes: List[str] = []
    for eid in element_ids:
        if eid not in boxes:
            continue
        e = model_elements.get(eid)
        if not e:
            continue

        name, subtitle = element_label(e)
        kind = str(e.get("kind", ""))
        fill, stroke, header_fill = kind_colors(kind)
        nodes.append(
            draw_node(
                node_id=eid,
                name=name,
                subtitle=subtitle,
                kind=kind,
                technology=str(e.get("technology", "")),
                box=boxes[eid],
                view_id=vid,
                fill=fill,
                stroke=stroke,
                header_fill=header_fill,
            )
        )

    svg = f"""<svg viewBox=\"0 0 {width} {height}\" width=\"{width}\" height=\"{height}\" xmlns=\"http://www.w3.org/2000/svg\">
  <defs>
    <marker id=\"arrow\" markerWidth=\"10\" markerHeight=\"10\" refX=\"8\" refY=\"5\" orient=\"auto\">
      <path d=\"M0,0 L10,5 L0,10 z\" fill=\"#90a7cf\" />
    </marker>
  </defs>
  <rect x=\"0\" y=\"0\" width=\"{width}\" height=\"{height}\" fill=\"#0b1020\" />
  {boundary}
  {'\n  '.join(edges)}
  {'\n  '.join(nodes)}
</svg>
"""

    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(svg, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-root", required=True)
    args = ap.parse_args()

    root = Path(args.output_root).expanduser().resolve()
    arch = root / "architecture"
    model = load_yaml(arch / "model.yaml")
    views_dir = arch / "views"
    out_dir = root / "architecture" / ".out" / "diagram-svg"
    out_dir.mkdir(parents=True, exist_ok=True)

    elements = {
        e.get("id"): e
        for e in (model.get("elements") or [])
        if isinstance(e, dict) and e.get("id")
    }
    rels = {
        r.get("id"): r
        for r in (model.get("relationships") or [])
        if isinstance(r, dict) and r.get("id")
    }

    for vf in sorted(views_dir.glob("*.y*ml")):
        view = load_yaml(vf)
        if str(view.get("type", "")).lower() == "sequence":
            # Optional: sequence can use built-in renderer.
            continue
        vid = view.get("id") or vf.stem
        view["id"] = vid
        render_view_fragment(view, elements, rels, out_dir / f"{vid}.svg")

    print(str(out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
