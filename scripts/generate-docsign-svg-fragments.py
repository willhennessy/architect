#!/usr/bin/env python3
"""Generate SVG fragments for DocSign test runs.

This creates per-view SVG fragments under <output-root>/diagram-svg so the renderer
can run in --demo-mode without fallback.
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


def anchor_point(src: Dict[str, float], dst: Dict[str, float]) -> Tuple[float, float]:
    # perimeter anchor from src rect toward dst center
    sx, sy, sw, sh = src["x"], src["y"], src["w"], src["h"]
    cx, cy = sx + sw / 2.0, sy + sh / 2.0
    dx, dy = dst["x"] + dst["w"] / 2.0 - cx, dst["y"] + dst["h"] / 2.0 - cy

    if dx == 0 and dy == 0:
        return cx, cy

    # scale vector to hit rectangle border
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
    color: str = "#8ea2c8",
) -> str:
    x1, y1 = anchor_point(src_box, dst_box)
    x2, y2 = anchor_point(dst_box, src_box)

    angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
    mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    # small perpendicular offset
    length = math.hypot(x2 - x1, y2 - y1)
    nx, ny = (-(y2 - y1) / length, (x2 - x1) / length) if length > 0 else (0.0, 0.0)
    lx, ly = mx + nx * 8.0, my + ny * 8.0

    short = label if len(label) <= 48 else label[:47] + "…"

    return f"""
  <line x1=\"{x1:.1f}\" y1=\"{y1:.1f}\" x2=\"{x2:.1f}\" y2=\"{y2:.1f}\" stroke=\"{color}\" stroke-width=\"1.8\" marker-end=\"url(#arrow)\" />
  <line x1=\"{x1:.1f}\" y1=\"{y1:.1f}\" x2=\"{x2:.1f}\" y2=\"{y2:.1f}\" stroke=\"transparent\" stroke-width=\"14\" fill=\"none\"
        data-relationship-id=\"{esc(rel_id)}\" data-view-id=\"{esc(view_id)}\" data-target-label=\"{esc(label or rel_id)}\" />
  <text x=\"{lx:.1f}\" y=\"{ly:.1f}\" transform=\"rotate({angle:.1f} {lx:.1f} {ly:.1f})\" text-anchor=\"middle\"
        font-size=\"10\" fill=\"#9eb3d8\">{esc(short)}</text>
""".rstrip()


def draw_node(node_id: str, name: str, subtitle: str, box: Dict[str, float], view_id: str, fill: str, stroke: str = "#c7d7ff") -> str:
    x, y, w, h = box["x"], box["y"], box["w"], box["h"]
    lines = []
    lines.append(
        f"<rect x=\"{x}\" y=\"{y}\" width=\"{w}\" height=\"{h}\" rx=\"12\" fill=\"{fill}\" stroke=\"{stroke}\" stroke-width=\"1.2\" "
        f"data-element-id=\"{esc(node_id)}\" data-view-id=\"{esc(view_id)}\" data-target-label=\"{esc(name)}\" />"
    )
    lines.append(
        f"<text x=\"{x + w/2:.1f}\" y=\"{y + h/2 - 6:.1f}\" text-anchor=\"middle\" font-size=\"16\" font-weight=\"700\" fill=\"#f6fbff\">{esc(name)}</text>"
    )
    if subtitle:
        lines.append(
            f"<text x=\"{x + w/2:.1f}\" y=\"{y + h/2 + 16:.1f}\" text-anchor=\"middle\" font-size=\"11\" fill=\"#d8e8ff\">{esc(subtitle)}</text>"
        )
    return "\n  ".join(lines)


def element_label(e: Dict[str, Any]) -> Tuple[str, str]:
    name = str(e.get("name", e.get("id", "")))
    kind = str(e.get("kind", ""))
    tech = str(e.get("technology", ""))
    if kind == "person":
        return name, "[Person]"
    if kind == "external_system":
        return name, tech
    return name, tech


def find(elements: Dict[str, Dict[str, Any]], key: str) -> str:
    if key in elements:
        return key
    for eid, e in elements.items():
        n = str(e.get("name", "")).lower()
        if key.lower() in eid.lower() or key.lower() in n:
            return eid
    raise KeyError(f"Missing element for key: {key}")


def render_view_fragment(
    view: Dict[str, Any],
    model_elements: Dict[str, Dict[str, Any]],
    rels: Dict[str, Dict[str, Any]],
    out_file: Path,
) -> None:
    vid = str(view.get("id", "view"))

    # Manual placements tuned for DocSign prompt artifacts
    if vid == "system-context":
        boxes = {
            find(model_elements, "person-doc-sender"): {"x": 80, "y": 120, "w": 240, "h": 90},
            find(model_elements, "person-document-signer"): {"x": 360, "y": 120, "w": 240, "h": 90},
            find(model_elements, "person-platform-admin"): {"x": 640, "y": 120, "w": 240, "h": 90},
            find(model_elements, "sys-docsign-platform"): {"x": 360, "y": 320, "w": 460, "h": 220},
            find(model_elements, "ext-customer-webhook-endpoint"): {"x": 1020, "y": 250, "w": 300, "h": 90},
            find(model_elements, "ext-email-provider"): {"x": 1020, "y": 360, "w": 300, "h": 90},
            find(model_elements, "ext-object-storage"): {"x": 1020, "y": 470, "w": 300, "h": 90},
        }
        width, height = 1380, 700
        boundary = '<rect x="330" y="290" width="550" height="280" rx="14" fill="rgba(32,44,74,0.22)" stroke="#5d7198" stroke-dasharray="5 4" />\n  <text x="344" y="312" font-size="11" fill="#9cb4dd" font-weight="700">DocSign Platform</text>'
    elif vid == "container":
        boxes = {
            find(model_elements, "person-doc-sender"): {"x": 60, "y": 80, "w": 220, "h": 80},
            find(model_elements, "person-document-signer"): {"x": 320, "y": 80, "w": 220, "h": 80},
            find(model_elements, "person-platform-admin"): {"x": 580, "y": 80, "w": 220, "h": 80},
            find(model_elements, "container-web-application"): {"x": 120, "y": 250, "w": 300, "h": 110},
            find(model_elements, "container-platform-api"): {"x": 460, "y": 250, "w": 300, "h": 110},
            find(model_elements, "container-signing-service"): {"x": 120, "y": 390, "w": 220, "h": 100},
            find(model_elements, "container-notification-service"): {"x": 360, "y": 390, "w": 220, "h": 100},
            find(model_elements, "container-webhook-service"): {"x": 600, "y": 390, "w": 220, "h": 100},
            find(model_elements, "container-audit-service"): {"x": 840, "y": 390, "w": 220, "h": 100},
            find(model_elements, "database-postgres-primary"): {"x": 120, "y": 560, "w": 250, "h": 100},
            find(model_elements, "queue-message-queue"): {"x": 400, "y": 560, "w": 250, "h": 100},
            find(model_elements, "database-audit-log"): {"x": 680, "y": 560, "w": 250, "h": 100},
            find(model_elements, "ext-customer-webhook-endpoint"): {"x": 1140, "y": 320, "w": 260, "h": 90},
            find(model_elements, "ext-email-provider"): {"x": 1140, "y": 440, "w": 260, "h": 90},
            find(model_elements, "ext-object-storage"): {"x": 1140, "y": 560, "w": 260, "h": 90},
        }
        width, height = 1460, 760
        boundary = (
            '<rect x="90" y="220" width="1010" height="470" rx="14" fill="rgba(28,40,72,0.20)" stroke="#60749c" stroke-dasharray="5 4" />\n'
            '  <text x="106" y="242" font-size="11" fill="#9cb4dd" font-weight="700">DocSign Platform [System Boundary]</text>'
        )
    else:
        return

    element_ids = [eid for eid in (view.get("element_ids") or []) if isinstance(eid, str)]
    relationship_ids = [rid for rid in (view.get("relationship_ids") or []) if isinstance(rid, str)]

    lines: List[str] = []
    for rid in relationship_ids:
        rel = rels.get(rid)
        if not rel:
            continue
        sid, tid = rel.get("source_id"), rel.get("target_id")
        if sid not in boxes or tid not in boxes:
            continue
        lines.append(draw_edge(rid, str(rel.get("label", "")), boxes[sid], boxes[tid], vid))

    nodes: List[str] = []
    for eid in element_ids:
        if eid not in boxes:
            continue
        e = model_elements.get(eid)
        if not e:
            continue
        name, subtitle = element_label(e)
        kind = str(e.get("kind", ""))
        if kind == "person":
            fill = "#3b82f6"
        elif kind == "external_system":
            fill = "#f97316"
        elif kind in {"database", "queue", "cache"}:
            fill = "#334155"
        else:
            fill = "#16a34a"
        nodes.append(draw_node(eid, name, subtitle, boxes[eid], vid, fill))

    svg = f"""<svg viewBox=\"0 0 {width} {height}\" width=\"{width}\" height=\"{height}\" xmlns=\"http://www.w3.org/2000/svg\">
  <defs>
    <marker id=\"arrow\" markerWidth=\"10\" markerHeight=\"10\" refX=\"8\" refY=\"5\" orient=\"auto\">
      <path d=\"M0,0 L10,5 L0,10 z\" fill=\"#8ea2c8\" />
    </marker>
  </defs>
  <rect x=\"0\" y=\"0\" width=\"{width}\" height=\"{height}\" fill=\"#0f1a30\" />
  {boundary}
  {'\n  '.join(lines)}
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
    out_dir = root / "diagram-svg"
    out_dir.mkdir(parents=True, exist_ok=True)

    elements = {e.get("id"): e for e in (model.get("elements") or []) if isinstance(e, dict) and e.get("id")}
    rels = {r.get("id"): r for r in (model.get("relationships") or []) if isinstance(r, dict) and r.get("id")}

    for vf in sorted(views_dir.glob("*.y*ml")):
        view = load_yaml(vf)
        vid = view.get("id") or vf.stem
        if str(view.get("type", "")).lower() == "sequence":
            # Optional: leave sequence to built-in renderer.
            continue
        render_view_fragment(view, elements, rels, out_dir / f"{vid}.svg")

    print(str(out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
