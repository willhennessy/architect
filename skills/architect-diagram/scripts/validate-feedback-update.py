#!/usr/bin/env python3
"""Validate architecture artifacts after a Claude feedback update.

This is a lightweight hardening check for the Claude channel feedback loop.
It focuses on the most common drift introduced by freeform edits:

- contract-invalid element / relationship enum values
- missing required fields
- broken view references
- relationship endpoints that no longer exist
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import yaml


ELEMENT_KINDS = {
    "person",
    "software_system",
    "external_system",
    "container",
    "component",
    "database",
    "queue",
    "cache",
    "deployment_node",
    "library_module",
}

C4_LEVELS = {"context", "container", "component", "deployment"}
RUNTIME_BOUNDARIES = {"process", "deployable", "internal_module", "external", "data_store", "network_zone"}
INTERACTION_TYPES = {
    "uses",
    "calls",
    "publishes",
    "subscribes",
    "reads",
    "writes",
    "stores",
    "authenticates_with",
    "renders",
    "triggers",
    "contains",
    "deploys_to",
}
DIRECTIONALITY = {"unidirectional", "bidirectional"}
SYNC_ASYNC = {"sync", "async", "storage", "human", "n_a"}
RUNTIME_BOUNDARIES.update({"library", "file", "network"})
PROTOCOLS = {"https", "http", "http/https", "grpc", "sql", "sqlite", "kafka", "s3", "redis", "in_process", "manual", "cli", "n_a"}
CONFIDENCE_LEVELS = {"confirmed", "strong_inference", "weak_inference"}
EVIDENCE_STRENGTHS = {"high", "medium", "low"}
EVIDENCE_KINDS = {
    "runtime_entrypoint",
    "deploy_config",
    "api_schema",
    "migration",
    "infra",
    "queue_definition",
    "code_path",
    "doc",
    "directory_name",
    "plan_requirement",
    "plan_constraint",
    "plan_assumption",
    "plan_tradeoff",
    "user_intent",
    "diagram_annotation",
}
VIEW_ALLOWED_KINDS = {
    "system_context": {"person", "software_system", "external_system"},
    "container": {"person", "software_system", "external_system", "container", "database", "queue", "cache"},
}

ELEMENT_REQUIRED_FIELDS = [
    "id",
    "name",
    "kind",
    "c4_level",
    "description",
    "responsibility",
    "owned_data",
    "system_of_record",
    "runtime_boundary",
    "source_paths",
    "confidence",
    "evidence_ids",
]

REL_REQUIRED_FIELDS = [
    "id",
    "source_id",
    "target_id",
    "label",
    "interaction_type",
    "directionality",
    "sync_async",
    "data_objects",
    "confidence",
    "evidence_ids",
]

NORMALIZATION_HINTS = {
    "datastore": "database",
    "db": "database",
    "external service": "external_system",
    "service": "container",
    "worker": "container",
}


def read_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Missing required file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise SystemExit(f"Expected YAML mapping at: {path}")
    return data


def list_view_files(views_dir: Path) -> List[Path]:
    if not views_dir.exists() or not views_dir.is_dir():
        raise SystemExit(f"Missing views directory: {views_dir}")
    return sorted(
        [p for p in views_dir.rglob("*") if p.is_file() and p.suffix in {".yaml", ".yml"}],
        key=lambda path: path.relative_to(views_dir).as_posix(),
    )


def is_blank(value: Any) -> bool:
    return value is None or value == ""


def add_error(errors: List[str], path: str, message: str) -> None:
    errors.append(f"{path}: {message}")


def extract_refs(items: Any) -> List[str]:
    refs: List[str] = []
    if not isinstance(items, list):
        return refs
    for item in items:
        if isinstance(item, str):
            refs.append(item)
        elif isinstance(item, dict):
            ref = item.get("ref") or item.get("id")
            if isinstance(ref, str) and ref:
                refs.append(ref)
    return refs


def validate_required_fields(
    item: Dict[str, Any],
    required_fields: Sequence[str],
    path_prefix: str,
    errors: List[str],
) -> None:
    for field in required_fields:
        if field not in item:
            add_error(errors, path_prefix, f"missing required field `{field}`")
            continue
        value = item.get(field)
        if isinstance(value, list) and value == []:
            continue
        if is_blank(value):
            add_error(errors, path_prefix, f"required field `{field}` is blank")


def validate_model(output_root: Path, errors: List[str], warnings: List[str]) -> Tuple[Dict[str, str], set[str]]:
    model = read_yaml(output_root / "architecture" / "model.yaml")
    elements = model.get("elements") or []
    relationships = model.get("relationships") or []
    evidence = model.get("evidence") or []

    if not isinstance(elements, list):
        add_error(errors, "architecture/model.yaml", "`elements` must be a list")
        elements = []
    if not isinstance(relationships, list):
        add_error(errors, "architecture/model.yaml", "`relationships` must be a list")
        relationships = []
    if not isinstance(evidence, list):
        add_error(errors, "architecture/model.yaml", "`evidence` must be a list")
        evidence = []

    element_ids: set[str] = set()
    element_kinds: Dict[str, str] = {}
    relationship_ids: set[str] = set()
    evidence_ids: set[str] = set()

    for index, item in enumerate(evidence):
        path = f"architecture/model.yaml:evidence[{index}]"
        if not isinstance(item, dict):
            add_error(errors, path, "evidence entry must be a mapping")
            continue
        evidence_id = item.get("id")
        if not isinstance(evidence_id, str) or not evidence_id:
            add_error(errors, path, "missing required field `id`")
            continue
        if evidence_id in evidence_ids:
            add_error(errors, path, f"duplicate evidence id `{evidence_id}`")
        evidence_ids.add(evidence_id)

        for field in ("path", "kind", "strength", "reason"):
            value = item.get(field)
            if not isinstance(value, str) or not value.strip():
                add_error(errors, path, f"required field `{field}` is blank")

        kind = str(item.get("kind") or "")
        if kind and kind not in EVIDENCE_KINDS:
            add_error(errors, path, f"invalid evidence kind `{kind}`")

        strength = str(item.get("strength") or "")
        if strength and strength not in EVIDENCE_STRENGTHS:
            add_error(errors, path, f"invalid evidence strength `{strength}`")

    for index, element in enumerate(elements):
        path = f"architecture/model.yaml:elements[{index}]"
        if not isinstance(element, dict):
            add_error(errors, path, "element must be a mapping")
            continue
        validate_required_fields(element, ELEMENT_REQUIRED_FIELDS, path, errors)
        if "technology" not in element:
            add_error(errors, path, "missing required field `technology`")

        element_id = element.get("id")
        if isinstance(element_id, str) and element_id:
            if element_id in element_ids:
                add_error(errors, path, f"duplicate element id `{element_id}`")
            element_ids.add(element_id)

        kind = str(element.get("kind") or "")
        if kind and kind not in ELEMENT_KINDS:
            hint = NORMALIZATION_HINTS.get(kind.lower())
            if hint:
                add_error(errors, path, f"invalid kind `{kind}`; use `{hint}`")
            else:
                add_error(errors, path, f"invalid kind `{kind}`")
        if isinstance(element_id, str) and element_id and kind:
            element_kinds[element_id] = kind

        c4_level = str(element.get("c4_level") or "")
        if c4_level and c4_level not in C4_LEVELS:
            add_error(errors, path, f"invalid c4_level `{c4_level}`")

        runtime_boundary = str(element.get("runtime_boundary") or "")
        if runtime_boundary and runtime_boundary not in RUNTIME_BOUNDARIES:
            add_error(errors, path, f"invalid runtime_boundary `{runtime_boundary}`")

        if kind == "component" and is_blank(element.get("parent_id")):
            add_error(errors, path, "component elements must set `parent_id`")

        for field in ("deployable", "external"):
            value = element.get(field)
            if value is not None and not isinstance(value, bool):
                add_error(errors, path, f"`{field}` must be a boolean")

        for field in ("owned_data", "system_of_record", "source_paths", "tags", "evidence_ids"):
            value = element.get(field)
            if value is not None and not isinstance(value, list):
                add_error(errors, path, f"`{field}` must be a list")

        confidence = str(element.get("confidence") or "")
        if confidence and confidence not in CONFIDENCE_LEVELS:
            add_error(errors, path, f"invalid confidence `{confidence}`")

        for ev_id in element.get("evidence_ids") or []:
            if ev_id not in evidence_ids:
                add_error(errors, path, f"references unknown evidence id `{ev_id}`")

    for index, rel in enumerate(relationships):
        path = f"architecture/model.yaml:relationships[{index}]"
        if not isinstance(rel, dict):
            add_error(errors, path, "relationship must be a mapping")
            continue
        validate_required_fields(rel, REL_REQUIRED_FIELDS, path, errors)

        rel_id = rel.get("id")
        if isinstance(rel_id, str) and rel_id:
            if rel_id in relationship_ids:
                add_error(errors, path, f"duplicate relationship id `{rel_id}`")
            relationship_ids.add(rel_id)

        for field, allowed in (
            ("interaction_type", INTERACTION_TYPES),
            ("directionality", DIRECTIONALITY),
            ("sync_async", SYNC_ASYNC),
        ):
            value = str(rel.get(field) or "")
            if value and value not in allowed:
                add_error(errors, path, f"invalid {field} `{value}`")

        protocol = str(rel.get("protocol") or "")
        if protocol and protocol not in PROTOCOLS:
            add_error(errors, path, f"invalid protocol `{protocol}`")

        source_id = rel.get("source_id")
        target_id = rel.get("target_id")
        if isinstance(source_id, str) and source_id and source_id not in element_ids:
            add_error(errors, path, f"source_id `{source_id}` does not exist")
        if isinstance(target_id, str) and target_id and target_id not in element_ids:
            add_error(errors, path, f"target_id `{target_id}` does not exist")

        for field in ("data_objects", "evidence_ids"):
            value = rel.get(field)
            if value is not None and not isinstance(value, list):
                add_error(errors, path, f"`{field}` must be a list")

        confidence = str(rel.get("confidence") or "")
        if confidence and confidence not in CONFIDENCE_LEVELS:
            add_error(errors, path, f"invalid confidence `{confidence}`")

        for ev_id in rel.get("evidence_ids") or []:
            if ev_id not in evidence_ids:
                add_error(errors, path, f"references unknown evidence id `{ev_id}`")

    return element_kinds, relationship_ids


def validate_views(output_root: Path, element_kinds: Dict[str, str], relationship_ids: set[str], errors: List[str]) -> None:
    element_ids = set(element_kinds)
    views_dir = output_root / "architecture" / "views"
    for path in list_view_files(views_dir):
        data = read_yaml(path)
        view_label = f"architecture/views/{path.relative_to(views_dir).as_posix()}"
        view_type = str(data.get("type") or data.get("view_type") or "").strip().lower().replace("-", "_")

        explicit_element_ids = data.get("element_ids")
        if not isinstance(explicit_element_ids, list):
            explicit_element_ids = extract_refs(data.get("elements"))
        for ref in explicit_element_ids:
            if ref not in element_ids:
                add_error(errors, view_label, f"references unknown element `{ref}`")
                continue
            allowed_kinds = VIEW_ALLOWED_KINDS.get(view_type)
            if allowed_kinds and element_kinds.get(ref) not in allowed_kinds:
                add_error(
                    errors,
                    view_label,
                    f"element `{ref}` has kind `{element_kinds.get(ref)}` which is not allowed in `{view_type}` views",
                )

        explicit_relationship_ids = data.get("relationship_ids")
        if not isinstance(explicit_relationship_ids, list):
            explicit_relationship_ids = extract_refs(data.get("relationships"))
        for ref in explicit_relationship_ids:
            if ref not in relationship_ids:
                add_error(errors, view_label, f"references unknown relationship `{ref}`")

        participant_ids = data.get("participant_ids")
        if not isinstance(participant_ids, list):
            participant_ids = extract_refs(data.get("participants"))
        for ref in participant_ids:
            if ref not in element_ids:
                add_error(errors, view_label, f"references unknown sequence participant `{ref}`")

        steps = data.get("steps") or []
        if not isinstance(steps, list):
            add_error(errors, view_label, "`steps` must be a list when present")
            continue
        for step_index, step in enumerate(steps):
            if not isinstance(step, dict):
                add_error(errors, view_label, f"step[{step_index}] must be a mapping")
                continue
            source_id = step.get("source_id") or step.get("source")
            target_id = step.get("target_id") or step.get("target")
            if source_id and source_id not in element_ids:
                add_error(errors, view_label, f"step[{step_index}] references unknown source `{source_id}`")
            if target_id and target_id not in element_ids:
                add_error(errors, view_label, f"step[{step_index}] references unknown target `{target_id}`")


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate architecture artifacts after a Claude feedback update")
    ap.add_argument("--output-root", required=True, help="Folder containing architecture/")
    ap.add_argument("--json", action="store_true", help="Emit structured JSON")
    args = ap.parse_args()

    output_root = Path(args.output_root).expanduser().resolve()
    errors: List[str] = []
    warnings: List[str] = []

    element_kinds, relationship_ids = validate_model(output_root, errors, warnings)
    validate_views(output_root, element_kinds, relationship_ids, errors)

    result = {
        "ok": not errors,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "output_root": str(output_root),
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["ok"]:
            print("OK: architecture feedback update validation passed")
        else:
            print("ERROR: architecture feedback update validation failed")
            for err in errors:
                print(f"- {err}")
        for warning in warnings:
            print(f"WARN: {warning}")

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
