#!/usr/bin/env python3
"""Deterministic architecture HTML renderer.

Renders diagram.html from architecture artifacts using a fixed HTML template.
This keeps HTML generation cost predictable and low.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Set

import yaml


VIEW_PRIORITY = {
    "system_context": 0,
    "container": 1,
    "component": 2,
    "deployment": 3,
    "sequence": 4,
}


class RenderError(RuntimeError):
    pass


def read_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise RenderError(f"Missing required file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise RenderError(f"Expected YAML mapping at: {path}")
    return data


def list_view_files(views_dir: Path) -> List[Path]:
    if not views_dir.exists() or not views_dir.is_dir():
        raise RenderError(f"Missing views directory: {views_dir}")
    return sorted([p for p in views_dir.iterdir() if p.suffix in {".yaml", ".yml"}])


def canon_view_type(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower().replace("-", "_")


def extract_refs(items: Any) -> List[str]:
    refs: List[str] = []
    if not isinstance(items, list):
        return refs
    for it in items:
        if isinstance(it, str):
            refs.append(it)
        elif isinstance(it, dict):
            ref = it.get("ref") or it.get("id")
            if isinstance(ref, str) and ref:
                refs.append(ref)
    return refs


def normalize_element(el: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": el.get("id"),
        "name": el.get("name") or el.get("id"),
        "kind": el.get("kind") or "container",
        "description": el.get("description") or "",
        "technology": el.get("technology") or "",
        "confidence": el.get("confidence") or "",
        "tags": el.get("tags") or [],
        "parent_id": el.get("parent_id") or None,
    }


def normalize_relationship(rel: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": rel.get("id"),
        "source_id": rel.get("source_id"),
        "target_id": rel.get("target_id"),
        "label": rel.get("label") or "",
        "protocol": rel.get("protocol") or "",
    }


def normalize_view(data: Dict[str, Any], source_path: Path) -> Dict[str, Any]:
    vtype = canon_view_type(data.get("type") or data.get("view_type"))
    vid = data.get("id") or source_path.stem

    element_ids = data.get("element_ids")
    if not isinstance(element_ids, list):
        element_ids = extract_refs(data.get("elements"))

    relationship_ids = data.get("relationship_ids")
    if not isinstance(relationship_ids, list):
        relationship_ids = extract_refs(data.get("relationships"))

    participant_ids = data.get("participant_ids")
    if not isinstance(participant_ids, list):
        participant_ids = extract_refs(data.get("participants"))

    steps: List[Dict[str, Any]] = []
    for st in (data.get("steps") or []):
        if not isinstance(st, dict):
            continue
        steps.append(
            {
                "order": st.get("order") if st.get("order") is not None else st.get("seq") if st.get("seq") is not None else st.get("step"),
                "source_id": st.get("source_id") or st.get("source"),
                "target_id": st.get("target_id") or st.get("target"),
                "label": st.get("label") or "",
            }
        )

    return {
        "id": vid,
        "type": vtype,
        "title": data.get("title") or vid,
        "element_ids": element_ids,
        "relationship_ids": relationship_ids,
        "participant_ids": participant_ids,
        "steps": steps,
        "parent_container_id": data.get("parent_container_id") or data.get("parent_container") or None,
    }


def choose_views(all_views: List[Dict[str, Any]], mode: str) -> List[Dict[str, Any]]:
    candidates = [v for v in all_views if v.get("type")]
    candidates.sort(key=lambda v: (VIEW_PRIORITY.get(v.get("type"), 99), v.get("title") or v.get("id") or ""))

    if mode == "fast":
        allowed = {"system_context", "container"}
        chosen = [v for v in candidates if v.get("type") in allowed]
        if not chosen:
            chosen = [v for v in candidates if v.get("type") != "sequence"][:1]
        return chosen

    chosen: List[Dict[str, Any]] = []
    for v in candidates:
        t = v.get("type")
        if t in {"system_context", "container", "component", "sequence"}:
            chosen.append(v)
    if not chosen:
        chosen = candidates[:]
    return chosen


def relationships_for_view(
    view: Dict[str, Any],
    relationships_by_id: Dict[str, Dict[str, Any]],
    relationships: List[Dict[str, Any]],
    element_ids: Set[str],
) -> List[Dict[str, Any]]:
    rel_ids = view.get("relationship_ids") or []
    selected: List[Dict[str, Any]] = []

    if rel_ids:
        for rid in rel_ids:
            rel = relationships_by_id.get(rid)
            if rel:
                selected.append(rel)
        return selected

    for rel in relationships:
        if rel.get("source_id") in element_ids and rel.get("target_id") in element_ids:
            selected.append(rel)
    return selected


def build_payload(
    manifest: Dict[str, Any],
    model: Dict[str, Any],
    views: List[Dict[str, Any]],
    mode: str,
) -> Dict[str, Any]:
    all_elements = [normalize_element(e) for e in (model.get("elements") or []) if isinstance(e, dict)]
    all_relationships = [normalize_relationship(r) for r in (model.get("relationships") or []) if isinstance(r, dict)]

    elements_by_id = {e["id"]: e for e in all_elements if e.get("id")}
    rels_by_id = {r["id"]: r for r in all_relationships if r.get("id")}

    chosen_views = choose_views(views, mode)
    if not chosen_views:
        raise RenderError("No usable views found to render.")

    payload_views: List[Dict[str, Any]] = []
    used_element_ids: Set[str] = set()

    for view in chosen_views:
        vtype = view.get("type")
        view_id = view.get("id") or f"view-{len(payload_views)+1}"
        title = view.get("title") or view_id

        if vtype == "sequence":
            steps = []
            for st in (view.get("steps") or []):
                if not isinstance(st, dict):
                    continue
                steps.append(
                    {
                        "order": st.get("order") if isinstance(st.get("order"), int) else 10**9,
                        "source_id": st.get("source_id"),
                        "target_id": st.get("target_id"),
                        "label": st.get("label") or "",
                    }
                )
                if st.get("source_id") in elements_by_id:
                    used_element_ids.add(st.get("source_id"))
                if st.get("target_id") in elements_by_id:
                    used_element_ids.add(st.get("target_id"))
            for pid in (view.get("participant_ids") or []):
                if pid in elements_by_id:
                    used_element_ids.add(pid)
            payload_views.append(
                {
                    "id": view_id,
                    "type": vtype,
                    "title": title,
                    "kind": "sequence",
                    "steps": sorted(steps, key=lambda s: s.get("order", 10**9)),
                }
            )
            continue

        element_ids = set([eid for eid in (view.get("element_ids") or []) if isinstance(eid, str)])
        nodes = [elements_by_id[eid] for eid in element_ids if eid in elements_by_id]

        # Graceful fallback for sparse/empty view files
        if not nodes:
            if vtype == "system_context":
                nodes = [e for e in all_elements if e.get("c4_level") == "context"]
            elif vtype == "container":
                nodes = [e for e in all_elements if e.get("c4_level") in {"context", "container"}]
            elif vtype == "component":
                parent_id = view.get("parent_container_id")
                nodes = [e for e in all_elements if e.get("parent_id") == parent_id] if parent_id else [e for e in all_elements if e.get("c4_level") == "component"]

        used_element_ids.update([n["id"] for n in nodes if n.get("id")])
        node_ids = {n["id"] for n in nodes if n.get("id")}

        rels = relationships_for_view(view, rels_by_id, all_relationships, node_ids)
        edges = []
        for r in rels:
            if not (r.get("source_id") and r.get("target_id")):
                continue
            edges.append(
                {
                    "id": r.get("id") or f"rel-{len(edges)+1}",
                    "source_id": r.get("source_id"),
                    "target_id": r.get("target_id"),
                    "label": r.get("label") or "",
                    "protocol": r.get("protocol") or "",
                }
            )

        payload_views.append(
            {
                "id": view_id,
                "type": vtype,
                "title": title,
                "kind": "diagram",
                "nodes": sorted(nodes, key=lambda n: (n.get("name") or n.get("id") or "")),
                "edges": edges,
                "parent_container_id": view.get("parent_container_id") or None,
            }
        )

    drill_map: Dict[str, str] = {}

    system_context = next((v for v in payload_views if v.get("type") == "system_context" and v.get("kind") == "diagram"), None)
    container_view = next((v for v in payload_views if v.get("type") == "container" and v.get("kind") == "diagram"), None)
    if system_context and container_view:
        system_like = [n for n in (system_context.get("nodes") or []) if n.get("kind") in {"software_system", "system"}]
        if system_like:
            drill_map[system_like[0]["id"]] = container_view["id"]

    for v in payload_views:
        if v.get("type") == "component" and v.get("parent_container_id"):
            drill_map.setdefault(v["parent_container_id"], v["id"])

    initial_view_id = None
    for preferred in ("system_context", "container"):
        for v in payload_views:
            if v.get("type") == preferred:
                initial_view_id = v["id"]
                break
        if initial_view_id:
            break
    if not initial_view_id:
        initial_view_id = payload_views[0]["id"]

    used_element_ids.update(drill_map.keys())
    payload_elements = [elements_by_id[eid] for eid in sorted(used_element_ids) if eid in elements_by_id]

    system_name = manifest.get("system_name") or model.get("system_name") or "Architecture"

    return {
        "system_name": system_name,
        "initial_view_id": initial_view_id,
        "views": payload_views,
        "elements": payload_elements,
        "drill_map": drill_map,
    }


def load_views(views_dir: Path) -> List[Dict[str, Any]]:
    raw: List[Dict[str, Any]] = []
    for vf in list_view_files(views_dir):
        data = read_yaml(vf)
        raw.append(normalize_view(data, vf))
    return raw


def render_html(template_path: Path, payload: Dict[str, Any], mode: str) -> str:
    template = template_path.read_text(encoding="utf-8")
    html = template.replace("__DIAGRAM_DATA_JSON__", json.dumps(payload, ensure_ascii=False))
    html = html.replace("__DIAGRAM_MODE__", mode)
    return html


def main() -> int:
    ap = argparse.ArgumentParser(description="Render deterministic diagram.html from architecture artifacts")
    ap.add_argument("--output-root", required=True, help="Folder containing architecture/")
    ap.add_argument("--mode", choices=["fast", "rich"], default="fast", help="Rendering mode")
    ap.add_argument("--write-data-json", action="store_true", help="Also write diagram-data.json for debugging")
    args = ap.parse_args()

    output_root = Path(args.output_root).expanduser().resolve()
    arch_dir = output_root / "architecture"

    manifest = read_yaml(arch_dir / "manifest.yaml")
    model = read_yaml(arch_dir / "model.yaml")
    views = load_views(arch_dir / "views")

    payload = build_payload(manifest, model, views, args.mode)

    template_path = Path(__file__).resolve().parents[1] / "templates" / "diagram-app.html"
    if not template_path.exists():
        raise RenderError(f"Template missing: {template_path}")

    html = render_html(template_path, payload, args.mode)
    out_html = output_root / "diagram.html"
    out_html.write_text(html, encoding="utf-8")

    if args.write_data_json:
        (output_root / "diagram-data.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {out_html}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RenderError as err:
        print(f"ERROR: {err}", flush=True)
        raise SystemExit(1)
