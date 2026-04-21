#!/usr/bin/env python3
"""Render diagram.html frame from architecture artifacts.

Behavior:
- inject per-view SVG fragments when present
- fallback to in-template renderer when fragments missing
- sequence views are disabled by default and included only with --include-sequence
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Set

import yaml


VIEW_PRIORITY = {
    "system_context": 0,
    "container": 1,
    "component": 2,
    "deployment": 3,
    "sequence": 4,
}

SVG_FRAGMENT_METADATA = "_metadata.json"
RUNTIME_DIR = ".out"


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


def architecture_dir(output_root: Path) -> Path:
    return output_root / "architecture"


def runtime_dir(output_root: Path) -> Path:
    return architecture_dir(output_root) / RUNTIME_DIR


def feedback_jobs_dir(output_root: Path) -> Path:
    return runtime_dir(output_root) / "feedback-jobs"


def diagram_html_path(output_root: Path) -> Path:
    return architecture_dir(output_root) / "diagram.html"


def diagram_data_path(output_root: Path) -> Path:
    return runtime_dir(output_root) / "diagram-data.json"


def list_view_files(views_dir: Path) -> List[Path]:
    if not views_dir.exists() or not views_dir.is_dir():
        raise RenderError(f"Missing views directory: {views_dir}")
    return sorted(
        [p for p in views_dir.rglob("*") if p.is_file() and p.suffix in {".yaml", ".yml"}],
        key=lambda path: path.relative_to(views_dir).as_posix(),
    )


def normalize_svg_fragment(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        t = "\n".join(lines).strip()

    # defensive strip of script blocks
    while True:
        low = t.lower()
        start = low.find("<script")
        if start == -1:
            break
        end = low.find("</script>", start)
        if end == -1:
            t = t[:start]
            break
        t = t[:start] + t[end + len("</script>") :]
    return t.strip()


def load_svg_fragments(output_root: Path, views: List[Dict[str, Any]], svg_dir_name: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    svg_dir = output_root / svg_dir_name
    if not svg_dir.exists() or not svg_dir.is_dir():
        return out

    current_revision = compute_revision_id(output_root)
    metadata_path = svg_dir / SVG_FRAGMENT_METADATA
    if not metadata_path.exists():
        return out
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return out
    if not isinstance(metadata, dict):
        return out
    if str(metadata.get("revision_id") or "") != current_revision:
        return out

    for view in views:
        vid = view.get("id")
        if not isinstance(vid, str) or not vid:
            continue
        fp = svg_dir / f"{vid}.svg"
        if fp.exists() and fp.is_file():
            out[vid] = normalize_svg_fragment(fp.read_text(encoding="utf-8", errors="ignore"))
    return out


def compute_revision_id(output_root: Path) -> str:
    arch = architecture_dir(output_root)
    parts: List[bytes] = []
    views_dir = arch / "views"
    for path in list_view_files(views_dir):
        parts.append(path.relative_to(arch).as_posix().encode("utf-8"))
        parts.append(path.read_bytes())
    for name in ("manifest.yaml", "model.yaml", "summary.md", "diff.yaml"):
        path = arch / name
        if path.exists():
            parts.append(name.encode("utf-8"))
            parts.append(path.read_bytes())
    digest = hashlib.sha1(b"\n".join(parts)).hexdigest()[:12]
    return f"rev-{digest}"


def load_latest_feedback_pointer(output_root: Path) -> Dict[str, Any] | None:
    latest_path = feedback_jobs_dir(output_root) / "latest.json"
    if not latest_path.exists():
        return None
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    return latest if isinstance(latest, dict) else None


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
        "c4_level": el.get("c4_level") or "",
    }


def normalize_string_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    items: List[str] = []
    for item in value:
        text = str(item or "").strip()
        if text:
            items.append(text)
    return items


def is_informative_value(value: Any) -> bool:
    normalized = str(value or "").strip().lower()
    return normalized not in {"", "n_a", "blank", "none", "unknown", "null"}


def relationship_has_sidebar_details(rel: Dict[str, Any]) -> bool:
    return any(
        [
            is_informative_value(rel.get("interaction_type")),
            is_informative_value(rel.get("directionality")),
            is_informative_value(rel.get("sync_async")),
            is_informative_value(rel.get("protocol")),
            bool(normalize_string_list(rel.get("data_objects"))),
        ]
    )


def normalize_relationship(rel: Dict[str, Any]) -> Dict[str, Any]:
    normalized = {
        "id": rel.get("id"),
        "source_id": rel.get("source_id"),
        "target_id": rel.get("target_id"),
        "label": rel.get("label") or "",
        "interaction_type": rel.get("interaction_type") or "",
        "directionality": rel.get("directionality") or "",
        "sync_async": rel.get("sync_async") or "",
        "protocol": rel.get("protocol") or "",
        "data_objects": normalize_string_list(rel.get("data_objects")),
        "confidence": rel.get("confidence") or "",
    }
    normalized["detailable"] = relationship_has_sidebar_details(normalized)
    return normalized


def normalize_view(data: Dict[str, Any], source_path: Path, views_root: Path) -> Dict[str, Any]:
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
        "source_relpath": source_path.relative_to(views_root).as_posix(),
    }


def normalize_source_relpath(relpath: Any) -> str:
    return str(relpath or "").strip().replace("\\", "/").strip("/")


def singularize_path_segment(segment: str) -> str:
    token = str(segment or "").strip()
    if len(token) <= 1:
        return token
    if token.endswith("ies") and len(token) > 3:
        return token[:-3] + "y"
    if token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def candidate_parent_view_paths(source_relpath: str) -> List[str]:
    normalized = normalize_source_relpath(source_relpath)
    if not normalized:
        return []

    path = PurePosixPath(normalized)
    dir_parts = list(path.parts[:-1])
    if not dir_parts:
        return []

    candidates: List[str] = []
    seen: Set[str] = set()

    for depth in range(len(dir_parts), 0, -1):
        ancestor_parts = dir_parts[:depth]
        parent_dir_parts = ancestor_parts[:-1]
        dir_name = ancestor_parts[-1]
        base_names = [dir_name]
        singular_name = singularize_path_segment(dir_name)
        if singular_name and singular_name not in base_names:
            base_names.append(singular_name)

        for base_name in base_names:
            for suffix in (".yaml", ".yml"):
                candidate = PurePosixPath(*parent_dir_parts, f"{base_name}{suffix}").as_posix()
                if candidate not in seen:
                    seen.add(candidate)
                    candidates.append(candidate)

        for index_name in ("index.yaml", "index.yml"):
            candidate = PurePosixPath(*ancestor_parts, index_name).as_posix()
            if candidate not in seen:
                seen.add(candidate)
                candidates.append(candidate)

    return candidates


def find_path_parent_view_id(
    view: Dict[str, Any],
    view_id_by_source_relpath: Dict[str, str],
) -> str | None:
    view_id = str(view.get("id") or "")
    for candidate in candidate_parent_view_paths(str(view.get("source_relpath") or "")):
        parent_id = view_id_by_source_relpath.get(candidate.lower())
        if parent_id and parent_id != view_id:
            return parent_id
    return None


def build_view_hierarchy(payload_views: List[Dict[str, Any]], drill_map: Dict[str, str]) -> Dict[str, Any]:
    ordered_view_ids = [str(view.get("id") or "") for view in payload_views if str(view.get("id") or "")]
    view_id_set = set(ordered_view_ids)
    children_by_view_id: Dict[str, List[str]] = {view_id: [] for view_id in ordered_view_ids}
    parent_by_view_id: Dict[str, str] = {}

    def link_parent_child(parent_id: str, child_id: str) -> bool:
        if not parent_id or not child_id or parent_id == child_id:
            return False
        if parent_id not in view_id_set or child_id not in view_id_set:
            return False
        existing_parent = parent_by_view_id.get(child_id)
        if existing_parent and existing_parent != parent_id:
            return False
        parent_by_view_id[child_id] = parent_id
        children = children_by_view_id.setdefault(parent_id, [])
        if child_id not in children:
            children.append(child_id)
        return True

    view_id_by_source_relpath: Dict[str, str] = {}
    for view in payload_views:
        view_id = str(view.get("id") or "")
        relpath = normalize_source_relpath(view.get("source_relpath"))
        if view_id and relpath and relpath.lower() not in view_id_by_source_relpath:
            view_id_by_source_relpath[relpath.lower()] = view_id

    for view in payload_views:
        view_id = str(view.get("id") or "")
        parent_id = find_path_parent_view_id(view, view_id_by_source_relpath)
        if parent_id:
            link_parent_child(parent_id, view_id)

    for view in payload_views:
        view_id = str(view.get("id") or "")
        if not view_id or view_id in parent_by_view_id:
            continue
        seen_child_ids: Set[str] = set()
        for node in (view.get("nodes") or []):
            if not isinstance(node, dict):
                continue
            child_id = drill_map.get(str(node.get("id") or ""))
            if not child_id or child_id == view_id or child_id in seen_child_ids:
                continue
            seen_child_ids.add(child_id)
            link_parent_child(view_id, child_id)

    items: List[Dict[str, Any]] = []
    visited: Set[str] = set()

    def visit(view_id: str, depth: int) -> None:
        if not view_id or view_id in visited or view_id not in view_id_set:
            return
        visited.add(view_id)
        items.append({"view_id": view_id, "depth": depth})
        for child_id in children_by_view_id.get(view_id, []):
            visit(child_id, depth + 1)

    for view_id in ordered_view_ids:
        if view_id not in parent_by_view_id:
            visit(view_id, 0)

    orphan_ids: List[str] = []
    for view_id in ordered_view_ids:
        if view_id in visited:
            continue
        orphan_ids.append(view_id)
        visit(view_id, 0)

    depth_by_view_id = {entry["view_id"]: entry["depth"] for entry in items}
    return {
        "items": items,
        "children_by_view_id": children_by_view_id,
        "parent_by_view_id": parent_by_view_id,
        "depth_by_view_id": depth_by_view_id,
        "orphan_ids": orphan_ids,
    }


def choose_views(all_views: List[Dict[str, Any]], mode: str, include_sequence: bool) -> List[Dict[str, Any]]:
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
        if t in {"system_context", "container", "component"}:
            chosen.append(v)
        elif t == "sequence" and include_sequence:
            chosen.append(v)
    if not chosen:
        chosen = [v for v in candidates if v.get("type") != "sequence"] or candidates[:1]
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
    chosen_views: List[Dict[str, Any]],
    svg_fragments: Dict[str, str],
    output_root: Path,
    feedback_bridge_url: str,
) -> Dict[str, Any]:
    all_elements = [normalize_element(e) for e in (model.get("elements") or []) if isinstance(e, dict)]
    all_relationships = [normalize_relationship(r) for r in (model.get("relationships") or []) if isinstance(r, dict)]

    elements_by_id = {e["id"]: e for e in all_elements if e.get("id")}
    rels_by_id = {r["id"]: r for r in all_relationships if r.get("id")}

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
                    "svg_fragment": svg_fragments.get(view_id),
                    "source_relpath": view.get("source_relpath") or "",
                }
            )
            continue

        element_ids = set([eid for eid in (view.get("element_ids") or []) if isinstance(eid, str)])
        nodes = [elements_by_id[eid] for eid in element_ids if eid in elements_by_id]

        # graceful fallback for sparse views
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
                    "interaction_type": r.get("interaction_type") or "",
                    "directionality": r.get("directionality") or "",
                    "sync_async": r.get("sync_async") or "",
                    "protocol": r.get("protocol") or "",
                    "data_objects": r.get("data_objects") or [],
                    "confidence": r.get("confidence") or "",
                    "detailable": bool(r.get("detailable")),
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
                "svg_fragment": svg_fragments.get(view_id),
                "source_relpath": view.get("source_relpath") or "",
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
    system_subtitle = str(manifest.get("overall_summary") or system_name)
    view_hierarchy = build_view_hierarchy(payload_views, drill_map)

    return {
        "system_name": system_name,
        "system_subtitle": system_subtitle,
        "initial_view_id": initial_view_id,
        "views": payload_views,
        "elements": payload_elements,
        "drill_map": drill_map,
        "view_hierarchy": view_hierarchy,
        "comment_handoff": {
            "bridge_url": feedback_bridge_url,
            "output_root": str(output_root),
            "diagram_path": str(diagram_html_path(output_root)),
            "diagram_revision_id": compute_revision_id(output_root),
            "latest_job_id": (load_latest_feedback_pointer(output_root) or {}).get("job_id"),
        },
    }


def load_views(views_dir: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for vf in list_view_files(views_dir):
        out.append(normalize_view(read_yaml(vf), vf, views_dir))
    return out


def render_html(template_path: Path, payload: Dict[str, Any], mode: str) -> str:
    template = template_path.read_text(encoding="utf-8")
    html = template.replace("__DIAGRAM_DATA_JSON__", json.dumps(payload, ensure_ascii=False))
    html = html.replace("__DIAGRAM_MODE__", mode)
    return html


def main() -> int:
    ap = argparse.ArgumentParser(description="Render diagram.html frame from architecture artifacts")
    ap.add_argument("--output-root", required=True, help="Folder containing architecture/")
    ap.add_argument("--mode", choices=["fast", "rich"], default="fast", help="Fallback rendering mode")
    ap.add_argument("--demo-mode", action="store_true", help="Demo quality mode: force rich view set and require SVG fragments (no fallback)")
    ap.add_argument("--include-sequence", action="store_true", help="Include sequence views (disabled by default)")
    ap.add_argument("--svg-dir", default="architecture/.out/diagram-svg", help="Folder under output-root containing per-view SVG fragments")
    ap.add_argument("--require-svg-fragments", action="store_true", help="Fail if any selected non-sequence view is missing an SVG fragment")
    ap.add_argument("--write-data-json", action="store_true", help="Also write architecture/.out/diagram-data.json for debugging")
    ap.add_argument("--feedback-bridge-url", default="http://127.0.0.1:8765", help="Bridge URL embedded in diagram.html comment handoff")
    args = ap.parse_args()

    if args.demo_mode:
        args.mode = "rich"
        args.require_svg_fragments = True

    output_root = Path(args.output_root).expanduser().resolve()
    arch_dir = architecture_dir(output_root)

    manifest = read_yaml(arch_dir / "manifest.yaml")
    model = read_yaml(arch_dir / "model.yaml")
    views = load_views(arch_dir / "views")
    chosen_views = choose_views(views, args.mode, include_sequence=args.include_sequence)
    svg_fragments = load_svg_fragments(output_root, chosen_views, args.svg_dir)

    if args.require_svg_fragments:
        missing = [v.get("id") for v in chosen_views if v.get("type") != "sequence" and not svg_fragments.get(v.get("id", ""))]
        if missing:
            raise RenderError(f"Missing SVG fragments for selected views: {', '.join([m for m in missing if m])}")

    payload = build_payload(manifest, model, chosen_views, svg_fragments, output_root, args.feedback_bridge_url)
    payload.setdefault("comment_handoff", {})
    payload["comment_handoff"]["render_context"] = {
        "mode": args.mode,
        "include_sequence": args.include_sequence,
        "view_types": [str(v.get("type") or "") for v in payload.get("views", []) if isinstance(v, dict)],
        "view_ids": [str(v.get("id") or "") for v in payload.get("views", []) if isinstance(v, dict)],
        "svg_fragment_view_ids": [
            str(v.get("id") or "")
            for v in payload.get("views", [])
            if isinstance(v, dict) and v.get("svg_fragment")
        ],
    }

    template_path = Path(__file__).resolve().parents[1] / "templates" / "diagram-app.html"
    if not template_path.exists():
        raise RenderError(f"Template missing: {template_path}")

    html = render_html(template_path, payload, args.mode)
    out_html = diagram_html_path(output_root)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(html, encoding="utf-8")

    if args.write_data_json:
        data_path = diagram_data_path(output_root)
        data_path.parent.mkdir(parents=True, exist_ok=True)
        data_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    fragment_count = sum(1 for v in payload.get("views", []) if v.get("svg_fragment"))
    print(f"Wrote {out_html} (svg fragments used: {fragment_count}, include_sequence={args.include_sequence})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RenderError as err:
        print(f"ERROR: {err}", flush=True)
        raise SystemExit(1)
