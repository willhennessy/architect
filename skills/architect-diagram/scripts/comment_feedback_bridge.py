#!/usr/bin/env python3
"""Localhost bridge for batched architecture comment feedback.

Phase 1:
- file-backed jobs
- immediate acknowledgement
- SSE status stream + polling fallback
- fast patch path
- same-file refresh UX

Phase 2:
- richer slow reconcile path
- latest-job status lookup on page load
- pluggable host adapter with terminal implementation
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import queue
import random
import re
import subprocess
import threading
import time
import traceback
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

import yaml


SECTION_START = "<!-- comment-feedback:start -->"
SECTION_END = "<!-- comment-feedback:end -->"
STATE_ORDER = [
    "received",
    "acknowledged",
    "analyzing",
    "fast_patch_running",
    "fast_patch_ready",
    "slow_patch_running",
    "completed",
    "failed",
    "blocked",
]

STATUS_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "acknowledged": {
        "needs_refresh": False,
        "has_fast_result": False,
        "has_final_result": False,
        "refresh_hint": "",
    },
    "analyzing": {
        "needs_refresh": False,
        "has_fast_result": False,
        "has_final_result": False,
        "refresh_hint": "",
    },
    "fast_patch_running": {
        "needs_refresh": False,
        "has_fast_result": False,
        "has_final_result": False,
        "refresh_hint": "",
    },
    "fast_patch_ready": {
        "needs_refresh": True,
        "has_fast_result": True,
        "has_final_result": False,
        "refresh_hint": "Refresh this page to view the quick update.",
    },
    "slow_patch_running": {
        "needs_refresh": True,
        "has_fast_result": True,
        "has_final_result": False,
        "refresh_hint": "Refresh this page to view the quick update now.",
    },
    "completed": {
        "needs_refresh": True,
        "has_fast_result": True,
        "has_final_result": True,
        "refresh_hint": "Refresh this page to view the latest diagram.",
    },
    "failed": {
        "needs_refresh": False,
        "has_fast_result": False,
        "has_final_result": False,
        "refresh_hint": "",
    },
    "blocked": {
        "needs_refresh": False,
        "has_fast_result": False,
        "has_final_result": False,
        "refresh_hint": "",
    },
}

VIEW_ALLOWED_KINDS = {
    "system_context": {"person", "software_system", "system", "external_system"},
    "container": {"person", "software_system", "system", "external_system", "container", "database", "queue", "cache"},
    "component": {"component"},
}

KIND_NORMALIZATION = {
    "service": "container",
    "worker": "container",
    "db": "database",
    "external service": "external_system",
    "external system": "external_system",
    "software system": "software_system",
    "person": "person",
    "actor": "person",
}
RUNTIME_DIR = ".out"


class BridgeError(RuntimeError):
    pass


class BlockedUpdate(RuntimeError):
    pass


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    atomic_write_text(path, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def read_yaml(path: Path, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not path.exists():
        if default is None:
            raise BridgeError(f"Missing required YAML file: {path}")
        return default
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise BridgeError(f"Expected YAML mapping at: {path}")
    return data


def write_yaml(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, yaml.safe_dump(obj, sort_keys=False, allow_unicode=True))


def append_unique(items: List[Any], value: Any) -> None:
    if value not in items:
        items.append(value)


def slugify(text: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9]+", "-", str(text or "").strip().lower()).strip("-")
    return clean or "item"


def short_hash(text: str, length: int = 8) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:length]


def architecture_dir(output_root: Path) -> Path:
    return output_root / "architecture"


def runtime_dir(output_root: Path) -> Path:
    return architecture_dir(output_root) / RUNTIME_DIR


def feedback_jobs_dir(output_root: Path) -> Path:
    return runtime_dir(output_root) / "feedback-jobs"


def claude_threads_path(output_root: Path) -> Path:
    return runtime_dir(output_root) / "claude-comments.json"


def diagram_html_path(output_root: Path) -> Path:
    return architecture_dir(output_root) / "diagram.html"


def load_rendered_diagram_revision_id(output_root: Path) -> str:
    diagram_path = diagram_html_path(output_root)
    if not diagram_path.exists():
        return ""
    html = diagram_path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r'"diagram_revision_id"\s*:\s*"([^"]+)"', html)
    return str(match.group(1) or "").strip() if match else ""


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


def current_diagram_revision_id(output_root: Path) -> str:
    rendered_revision = load_rendered_diagram_revision_id(output_root)
    if rendered_revision:
        return rendered_revision
    try:
        return compute_revision_id(output_root)
    except Exception:  # noqa: BLE001
        return ""


def normalize_kind(token: str) -> str:
    raw = " ".join(str(token or "").strip().lower().split())
    return KIND_NORMALIZATION.get(raw, raw)


def default_kind_fields(kind: str) -> Tuple[str, str, bool]:
    if kind in {"person", "external_system"}:
        return ("context", "external", True)
    if kind in {"software_system", "system"}:
        return ("context", "process", False)
    if kind in {"database", "queue", "cache"}:
        return ("container", "data_store", False)
    if kind == "container":
        return ("container", "deployable", False)
    if kind == "component":
        return ("component", "internal_module", False)
    return ("container", "deployable", False)


def allowed_in_view(view_type: str, kind: str) -> bool:
    allowed = VIEW_ALLOWED_KINDS.get(str(view_type or "").lower())
    if not allowed:
        return True
    return kind in allowed


def summarize_comment_count(n: int) -> str:
    return f"Received {n} diagram comment{'s' if n != 1 else ''}. Thinking through the update now."


def default_status_fields(state: str) -> Dict[str, Any]:
    return copy.deepcopy(STATUS_DEFAULTS.get(state, {}))


def list_view_files(views_dir: Path) -> List[Path]:
    return sorted(
        [p for p in views_dir.rglob("*") if p.is_file() and p.suffix in {".yaml", ".yml"}],
        key=lambda path: path.relative_to(views_dir).as_posix(),
    )


@dataclass
class ViewRecord:
    id: str
    path: Path
    data: Dict[str, Any]

    @property
    def view_type(self) -> str:
        return str(self.data.get("type") or self.data.get("view_type") or "").lower().replace("-", "_")


def load_views(output_root: Path) -> Dict[str, ViewRecord]:
    views_dir = architecture_dir(output_root) / "views"
    if not views_dir.exists():
        raise BridgeError(f"Missing views directory: {views_dir}")
    out: Dict[str, ViewRecord] = {}
    for path in list_view_files(views_dir):
        data = read_yaml(path, default={})
        vid = str(data.get("id") or path.stem)
        out[vid] = ViewRecord(id=vid, path=path, data=data)
    return out


def get_refs(view: Dict[str, Any], key: str, fallback_key: str) -> List[str]:
    explicit = view.get(key)
    if isinstance(explicit, list):
        return [str(x) for x in explicit if isinstance(x, str)]
    refs = []
    items = view.get(fallback_key) or []
    if isinstance(items, list):
        for item in items:
            if isinstance(item, str):
                refs.append(item)
            elif isinstance(item, dict):
                ref = item.get("ref") or item.get("id")
                if isinstance(ref, str) and ref:
                    refs.append(ref)
    return refs


def set_refs(view: Dict[str, Any], key: str, fallback_key: str, values: Iterable[str]) -> None:
    clean = [v for v in values if isinstance(v, str) and v]
    if key in view:
        view[key] = clean
        return
    view[fallback_key] = [{"ref": v} for v in clean]


def ensure_view_note(view: Dict[str, Any], note: str, limit: int = 20) -> None:
    notes = view.get("notes")
    if not isinstance(notes, list):
        notes = []
        view["notes"] = notes
    append_unique(notes, note)
    if len(notes) > limit:
        view["notes"] = notes[-limit:]


def first_system_like_id(model: Dict[str, Any]) -> str:
    for element in model.get("elements", []) or []:
        if not isinstance(element, dict):
            continue
        if str(element.get("kind", "")).lower() in {"software_system", "system"}:
            return str(element.get("id") or "")
    return ""


def ensure_list_field(obj: Dict[str, Any], key: str) -> List[Any]:
    value = obj.get(key)
    if not isinstance(value, list):
        value = []
        obj[key] = value
    return value


def element_index(model: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        str(e.get("id")): e
        for e in (model.get("elements") or [])
        if isinstance(e, dict) and isinstance(e.get("id"), str) and e.get("id")
    }


def relationship_index(model: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        str(r.get("id")): r
        for r in (model.get("relationships") or [])
        if isinstance(r, dict) and isinstance(r.get("id"), str) and r.get("id")
    }


def add_annotation_evidence(model: Dict[str, Any], job_id: str, comment: Dict[str, Any]) -> str:
    evidence = ensure_list_field(model, "evidence")
    evidence_id = f"ann-{short_hash(job_id, 6)}-{int(comment['index']):02d}"
    existing = {str(item.get("id")) for item in evidence if isinstance(item, dict)}
    if evidence_id not in existing:
        evidence.append(
            {
                "id": evidence_id,
                "path": f"plan://diagram-feedback/{job_id}/{comment['index']}",
                "kind": "diagram_annotation",
                "strength": "high",
                "reason": str(comment.get("comment") or "").strip(),
            }
        )
    return evidence_id


def find_element_by_name(model: Dict[str, Any], raw_name: str) -> Optional[Dict[str, Any]]:
    needle = str(raw_name or "").strip().lower()
    if not needle:
        return None
    for element in model.get("elements", []) or []:
        if not isinstance(element, dict):
            continue
        candidates = [str(element.get("id") or ""), str(element.get("name") or "")]
        aliases = element.get("aliases") or []
        if isinstance(aliases, list):
            candidates.extend([str(x) for x in aliases])
        for cand in candidates:
            if needle == cand.strip().lower():
                return element
    for element in model.get("elements", []) or []:
        if not isinstance(element, dict):
            continue
        blob = " ".join(
            [
                str(element.get("id") or ""),
                str(element.get("name") or ""),
                " ".join([str(x) for x in (element.get("aliases") or []) if isinstance(x, str)]),
            ]
        ).lower()
        if needle in blob:
            return element
    return None


def remove_element_everywhere(model: Dict[str, Any], views: Dict[str, ViewRecord], element_id: str) -> None:
    rels = [r for r in (model.get("relationships") or []) if isinstance(r, dict)]
    remove_rel_ids = [
        str(r.get("id"))
        for r in rels
        if str(r.get("source_id") or "") == element_id or str(r.get("target_id") or "") == element_id
    ]
    model["elements"] = [
        e for e in (model.get("elements") or []) if not (isinstance(e, dict) and str(e.get("id") or "") == element_id)
    ]
    if remove_rel_ids:
        model["relationships"] = [
            r for r in rels if not (isinstance(r, dict) and str(r.get("id") or "") in set(remove_rel_ids))
        ]
    for view in views.values():
        element_ids = [v for v in get_refs(view.data, "element_ids", "elements") if v != element_id]
        rel_ids = [v for v in get_refs(view.data, "relationship_ids", "relationships") if v not in set(remove_rel_ids)]
        set_refs(view.data, "element_ids", "elements", element_ids)
        set_refs(view.data, "relationship_ids", "relationships", rel_ids)


def remove_relationship_everywhere(model: Dict[str, Any], views: Dict[str, ViewRecord], relationship_id: str) -> None:
    model["relationships"] = [
        r for r in (model.get("relationships") or []) if not (isinstance(r, dict) and str(r.get("id") or "") == relationship_id)
    ]
    for view in views.values():
        rel_ids = [v for v in get_refs(view.data, "relationship_ids", "relationships") if v != relationship_id]
        set_refs(view.data, "relationship_ids", "relationships", rel_ids)


def add_element_to_view_if_allowed(view: ViewRecord, element_id: str, kind: str) -> bool:
    if not allowed_in_view(view.view_type, kind):
        return False
    current = get_refs(view.data, "element_ids", "elements")
    if element_id not in current:
        current.append(element_id)
        set_refs(view.data, "element_ids", "elements", current)
    return True


def add_relationship_to_view(view: ViewRecord, relationship_id: str) -> None:
    current = get_refs(view.data, "relationship_ids", "relationships")
    if relationship_id not in current:
        current.append(relationship_id)
        set_refs(view.data, "relationship_ids", "relationships", current)


def update_summary_feedback(summary_text: str, entry_markdown: str, keep_entries: int = 8) -> str:
    block = ""
    if SECTION_START in summary_text and SECTION_END in summary_text:
        before, rest = summary_text.split(SECTION_START, 1)
        _, after = rest.split(SECTION_END, 1)
        block = rest.split(SECTION_END, 1)[0]
        summary_text = before.rstrip() + "\n\n" + after.lstrip()
    entries = []
    if block:
        for chunk in re.split(r"\n(?=### Job )", block):
            chunk = chunk.strip()
            if chunk and not chunk.startswith(SECTION_START):
                entries.append(chunk)
    entries.append(entry_markdown.strip())
    entries = entries[-keep_entries:]
    feedback_block = "## Diagram Feedback Loop\n\n" + SECTION_START + "\n" + "\n\n".join(entries) + "\n" + SECTION_END + "\n"
    base = summary_text.rstrip()
    if base:
        return base + "\n\n" + feedback_block
    return feedback_block


def run_cmd(args: List[str], cwd: Optional[Path] = None, timeout: int = 120) -> Tuple[int, str]:
    proc = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
        check=False,
    )
    return proc.returncode, proc.stdout


@dataclass
class ParsedComment:
    raw: Dict[str, Any]
    action: str
    params: Dict[str, Any]
    scope: str
    recognized: bool
    slow_path: bool

    @property
    def comment_text(self) -> str:
        return str(self.raw.get("comment") or "")


def parse_comment(comment: Dict[str, Any]) -> ParsedComment:
    text = str(comment.get("comment") or "").strip()
    lower = text.lower()

    patterns: List[Tuple[str, str, str, bool]] = [
        ("rename", r"^(?:rename|call|label)(?: (?:this|it))?(?: to)?\s+(.+)$", "localized", False),
        ("set_description", r"^(?:description|desc)\s*[:=]\s*(.+)$", "localized", False),
        ("set_responsibility", r"^(?:responsibility)\s*[:=]\s*(.+)$", "localized", False),
        ("set_technology", r"^(?:technology|tech)\s*[:=]\s*(.+)$", "localized", False),
        ("add_tag", r"^(?:add )?tag(?: it)?(?: as)?\s+(.+)$", "localized", False),
        ("set_kind", r"^(?:mark as|make (?:this|it) (?:a|an)?|make)\s+(.+)$", "cross_view", False),
        ("set_async", r"^(?:make )?(?:this )?(async|asynchronous)$", "localized", False),
        ("set_sync", r"^(?:make )?(?:this )?(sync|synchronous)$", "localized", False),
        ("remove_target", r"^(?:remove|delete)(?: this| it)?$", "cross_view", True),
    ]

    for action, pattern, scope, slow in patterns:
        m = re.match(pattern, lower)
        if not m:
            continue
        value = text[m.start(1) :].strip() if m.groups() else ""
        if action == "set_kind":
            kind = normalize_kind(value)
            if kind in {"queue", "database", "cache", "container", "component", "external_system", "software_system", "person"}:
                return ParsedComment(comment, action, {"kind": kind}, scope, True, slow)
        elif action in {"rename", "set_description", "set_responsibility", "set_technology", "add_tag"}:
            return ParsedComment(comment, action, {"value": value}, scope, True, slow)
        elif action in {"set_async", "set_sync", "remove_target"}:
            return ParsedComment(comment, action, {}, scope, True, slow)

    m = re.match(
        r"^(?:set|change|make)(?: this)?(?: relationship)?(?: via)?\s+([a-z0-9_\-/+. ]+)$",
        lower,
    )
    if m and comment.get("relationship_id"):
        protocol = normalize_kind(m.group(1))
        if protocol in {"http", "https", "grpc", "sql", "queue", "kafka", "pubsub", "s3", "webhook"}:
            return ParsedComment(comment, "set_protocol", {"protocol": protocol}, "localized", True, False)

    m = re.match(
        r"^add (?:a |an )?(container|service|database|queue|cache|external system|external service|software system|person|component)\s+(.+)$",
        lower,
    )
    if m:
        return ParsedComment(
            comment,
            "add_element",
            {"kind": normalize_kind(m.group(1)), "name": text[m.start(2) :].strip()},
            "cross_view",
            True,
            True,
        )

    m = re.match(r"^connect\s+(.+?)\s+to\s+(.+?)(?:\s*:\s*(.+))?$", text, flags=re.IGNORECASE)
    if m:
        return ParsedComment(
            comment,
            "connect",
            {
                "source": m.group(1).strip(),
                "target": m.group(2).strip(),
                "label": (m.group(3) or "uses").strip(),
            },
            "cross_view",
            True,
            True,
        )

    if any(token in lower for token in ["split", "merge", "boundary", "ownership", "system of record", "auth", "subsystem"]):
        return ParsedComment(comment, "annotate", {}, "structural", False, True)

    return ParsedComment(comment, "annotate", {}, "cross_view", False, True)


def comment_scope_rank(scope: str) -> int:
    if scope == "structural":
        return 2
    if scope == "cross_view":
        return 1
    return 0


@dataclass
class UpdateAnalysis:
    parsed_comments: List[ParsedComment]
    needs_slow_path: bool
    scope: str


@dataclass
class ApplyResult:
    changed_element_ids: List[str] = field(default_factory=list)
    changed_relationship_ids: List[str] = field(default_factory=list)
    added_element_ids: List[str] = field(default_factory=list)
    removed_element_ids: List[str] = field(default_factory=list)
    added_relationship_ids: List[str] = field(default_factory=list)
    removed_relationship_ids: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    applied_actions: List[str] = field(default_factory=list)
    notes_only: List[str] = field(default_factory=list)


class ArchitectureUpdater:
    def __init__(self, output_root: Path, job_id: str, payload: Dict[str, Any]):
        self.output_root = output_root
        self.job_id = job_id
        self.payload = payload
        self.arch_dir = architecture_dir(output_root)
        self.model_path = self.arch_dir / "model.yaml"
        self.summary_path = self.arch_dir / "summary.md"
        self.manifest_path = self.arch_dir / "manifest.yaml"
        self.views = load_views(output_root)
        self.model = read_yaml(self.model_path)
        self.manifest = read_yaml(self.manifest_path, default={})
        self.summary_text = self.summary_path.read_text(encoding="utf-8") if self.summary_path.exists() else ""
        self.baseline_model = copy.deepcopy(self.model)
        self.baseline_summary = self.summary_text
        self.baseline_revision = compute_revision_id(output_root)

    def analyze(self) -> UpdateAnalysis:
        parsed = [parse_comment(comment) for comment in self.payload["comments"]]
        needs_slow = any(item.slow_path for item in parsed) or len(parsed) > 3
        max_rank = max([comment_scope_rank(item.scope) for item in parsed], default=0)
        scope = "localized"
        if max_rank >= 2:
            scope = "structural"
        elif max_rank == 1:
            scope = "cross_view"
        return UpdateAnalysis(parsed_comments=parsed, needs_slow_path=needs_slow, scope=scope)

    def apply_fast_patch(self, analysis: UpdateAnalysis) -> ApplyResult:
        result = ApplyResult()
        model_elements = element_index(self.model)
        model_relationships = relationship_index(self.model)
        top_system_id = first_system_like_id(self.model)
        current_revision = compute_revision_id(self.output_root)

        stale_revision = str(self.payload.get("diagram_revision_id") or "")
        if stale_revision and stale_revision != current_revision:
            result.warnings.append(
                f"Submitted against {stale_revision}, but current artifacts were already at {current_revision}."
            )

        for parsed in analysis.parsed_comments:
            comment = parsed.raw
            evidence_id = add_annotation_evidence(self.model, self.job_id, comment)
            target_view = self.views.get(str(comment.get("view_id") or ""))
            note = f"[Feedback {evidence_id}] {parsed.comment_text}"
            if target_view:
                ensure_view_note(target_view.data, note)

            element_id = str(comment.get("element_id") or "")
            relationship_id = str(comment.get("relationship_id") or "")
            element = model_elements.get(element_id) if element_id else None
            relationship = model_relationships.get(relationship_id) if relationship_id else None

            if element:
                append_unique(ensure_list_field(element, "evidence_ids"), evidence_id)
            if relationship:
                append_unique(ensure_list_field(relationship, "evidence_ids"), evidence_id)

            applied = self._apply_parsed_comment(parsed, element, relationship, top_system_id)
            if applied:
                result.applied_actions.append(applied)
            else:
                result.notes_only.append(parsed.comment_text)

            model_elements = element_index(self.model)
            model_relationships = relationship_index(self.model)

            if element_id and element_id in model_elements:
                append_unique(result.changed_element_ids, element_id)
            if relationship_id and relationship_id in model_relationships:
                append_unique(result.changed_relationship_ids, relationship_id)

        self.manifest["mode"] = "update"
        self.summary_text = self._update_summary(analysis, result)
        self._write_artifacts()
        self._render_fast()
        return result

    def apply_slow_patch(self, analysis: UpdateAnalysis, result: ApplyResult) -> ApplyResult:
        self._write_diff(analysis, result)
        self._generate_richer_visuals(result)
        self._run_strict_checks(result)
        self.finalize_result(result)
        return result

    def finalize_result(self, result: ApplyResult) -> None:
        self._write_result_summary(result)

    def _apply_parsed_comment(
        self,
        parsed: ParsedComment,
        element: Optional[Dict[str, Any]],
        relationship: Optional[Dict[str, Any]],
        top_system_id: str,
    ) -> str:
        if parsed.action == "rename":
            if element:
                element["name"] = parsed.params["value"]
                return f"Renamed element `{element['id']}`"
            if relationship:
                relationship["label"] = parsed.params["value"]
                return f"Relabeled relationship `{relationship['id']}`"
            return ""

        if parsed.action == "set_description" and element:
            element["description"] = parsed.params["value"]
            return f"Updated description for `{element['id']}`"

        if parsed.action == "set_responsibility" and element:
            element["responsibility"] = parsed.params["value"]
            return f"Updated responsibility for `{element['id']}`"

        if parsed.action == "set_technology" and element:
            element["technology"] = parsed.params["value"]
            return f"Updated technology for `{element['id']}`"

        if parsed.action == "add_tag" and element:
            append_unique(ensure_list_field(element, "tags"), parsed.params["value"])
            return f"Tagged `{element['id']}`"

        if parsed.action == "set_kind" and element:
            kind = parsed.params["kind"]
            c4_level, runtime_boundary, external = default_kind_fields(kind)
            element["kind"] = kind
            element["c4_level"] = c4_level
            element["runtime_boundary"] = runtime_boundary
            element["external"] = external
            if c4_level != "component":
                element["parent_id"] = top_system_id if c4_level == "container" else ""
            return f"Changed kind for `{element['id']}` to `{kind}`"

        if parsed.action == "set_async" and relationship:
            relationship["sync_async"] = "async"
            return f"Marked relationship `{relationship['id']}` as async"

        if parsed.action == "set_sync" and relationship:
            relationship["sync_async"] = "sync"
            return f"Marked relationship `{relationship['id']}` as sync"

        if parsed.action == "set_protocol" and relationship:
            protocol = parsed.params["protocol"]
            relationship["protocol"] = protocol
            if protocol in {"queue", "kafka", "pubsub"}:
                relationship["sync_async"] = "async"
            elif protocol in {"http", "https", "grpc", "sql"}:
                relationship["sync_async"] = "sync" if protocol != "sql" else "storage"
            return f"Updated protocol for `{relationship['id']}` to `{protocol}`"

        if parsed.action == "remove_target":
            element_id = str(parsed.raw.get("element_id") or "")
            relationship_id = str(parsed.raw.get("relationship_id") or "")
            if element_id:
                remove_element_everywhere(self.model, self.views, element_id)
                return f"Removed element `{element_id}` and attached relationships"
            if relationship_id:
                remove_relationship_everywhere(self.model, self.views, relationship_id)
                return f"Removed relationship `{relationship_id}`"
            return ""

        if parsed.action == "add_element":
            return self._add_element(parsed, top_system_id)

        if parsed.action == "connect":
            return self._connect_elements(parsed)

        return ""

    def _add_element(self, parsed: ParsedComment, top_system_id: str) -> str:
        kind = parsed.params["kind"]
        name = parsed.params["name"]
        element_id = slugify(name)
        existing_ids = {str(e.get("id")) for e in (self.model.get("elements") or []) if isinstance(e, dict)}
        while element_id in existing_ids:
            element_id = f"{element_id}-{random.randint(2, 9)}"
        c4_level, runtime_boundary, external = default_kind_fields(kind)
        parent_id = ""
        target_view = self.views.get(str(parsed.raw.get("view_id") or ""))
        if c4_level == "component":
            if target_view and target_view.data.get("parent_container_id"):
                parent_id = str(target_view.data.get("parent_container_id") or "")
            else:
                parent_id = str(parsed.raw.get("element_id") or "") or top_system_id
        elif c4_level == "container":
            parent_id = top_system_id

        evidence_id = add_annotation_evidence(self.model, self.job_id, parsed.raw)
        new_element = {
            "id": element_id,
            "name": name,
            "aliases": [],
            "kind": kind,
            "c4_level": c4_level,
            "description": f"{name} added from diagram feedback.",
            "responsibility": f"Handle {name} responsibilities.",
            "technology": "",
            "owned_data": [],
            "system_of_record": [],
            "runtime_boundary": runtime_boundary,
            "deployable": c4_level in {"context", "container"},
            "external": external,
            "parent_id": parent_id,
            "source_paths": [f"plan://diagram-feedback/{self.job_id}/{parsed.raw['index']}"],
            "tags": ["diagram-feedback"],
            "confidence": "strong_inference",
            "evidence_ids": [evidence_id],
        }
        ensure_list_field(self.model, "elements").append(new_element)

        if target_view and add_element_to_view_if_allowed(target_view, element_id, kind):
            pass
        else:
            for view in self.views.values():
                if add_element_to_view_if_allowed(view, element_id, kind):
                    break
        return f"Added `{kind}` `{element_id}`"

    def _connect_elements(self, parsed: ParsedComment) -> str:
        source = find_element_by_name(self.model, parsed.params["source"])
        target = find_element_by_name(self.model, parsed.params["target"])
        if not source or not target:
            raise BlockedUpdate(
                f"Could not resolve connect target(s): `{parsed.params['source']}` -> `{parsed.params['target']}`."
            )

        relationship_id = slugify(f"{source['id']}-{target['id']}-{parsed.params['label']}")
        existing_ids = {str(r.get("id")) for r in (self.model.get("relationships") or []) if isinstance(r, dict)}
        while relationship_id in existing_ids:
            relationship_id = f"{relationship_id}-{random.randint(2, 9)}"
        evidence_id = add_annotation_evidence(self.model, self.job_id, parsed.raw)
        relationship = {
            "id": relationship_id,
            "source_id": str(source["id"]),
            "target_id": str(target["id"]),
            "label": parsed.params["label"],
            "interaction_type": "uses",
            "directionality": "unidirectional",
            "sync_async": "async" if any(token in parsed.params["label"].lower() for token in ["async", "queue", "event"]) else "sync",
            "protocol": "queue" if "queue" in parsed.params["label"].lower() else "https",
            "data_objects": [],
            "confidence": "strong_inference",
            "evidence_ids": [evidence_id],
        }
        ensure_list_field(self.model, "relationships").append(relationship)

        added = False
        for view in self.views.values():
            element_ids = set(get_refs(view.data, "element_ids", "elements"))
            if source["id"] in element_ids and target["id"] in element_ids:
                add_relationship_to_view(view, relationship_id)
                added = True
        if not added:
            target_view = self.views.get(str(parsed.raw.get("view_id") or ""))
            if target_view:
                add_relationship_to_view(target_view, relationship_id)
        return f"Connected `{source['id']}` to `{target['id']}`"

    def _update_summary(self, analysis: UpdateAnalysis, result: ApplyResult) -> str:
        comments = analysis.parsed_comments
        lines = [f"### Job {self.job_id} — {utc_now_iso()}", ""]
        lines.append("**Comments**")
        for parsed in comments:
            label = parsed.raw.get("target_label") or parsed.raw.get("element_id") or parsed.raw.get("relationship_id") or "canvas"
            lines.append(f"- `{label}`: {parsed.comment_text}")
        if result.applied_actions:
            lines.append("")
            lines.append("**Applied in fast patch**")
            for action in result.applied_actions:
                lines.append(f"- {action}")
        if result.notes_only:
            lines.append("")
            lines.append("**Captured for follow-up**")
            for item in result.notes_only:
                lines.append(f"- {item}")
        if result.warnings:
            lines.append("")
            lines.append("**Warnings**")
            for warning in result.warnings:
                lines.append(f"- {warning}")
        entry = "\n".join(lines)
        return update_summary_feedback(self.summary_text, entry)

    def _write_artifacts(self) -> None:
        write_yaml(self.manifest_path, self.manifest)
        write_yaml(self.model_path, self.model)
        for view in self.views.values():
            write_yaml(view.path, view.data)
        atomic_write_text(self.summary_path, self.summary_text.rstrip() + "\n")

    def _render_fast(self) -> None:
        script_dir = Path(__file__).resolve().parent
        code, output = run_cmd(["python3", str(script_dir / "render-diagram-html.py"), "--output-root", str(self.output_root), "--mode", "fast"])
        if code != 0:
            raise BridgeError(output.strip() or "Fast render failed")
        code, output = run_cmd([str(script_dir / "validate-diagram-html.sh"), str(diagram_html_path(self.output_root))])
        if code != 0:
            raise BridgeError(output.strip() or "Fast validation failed")

    def _generate_richer_visuals(self, result: ApplyResult) -> None:
        script_dir = Path(__file__).resolve().parent
        code, output = run_cmd(["python3", str(script_dir / "generate-svg-fragments.py"), "--output-root", str(self.output_root)], timeout=180)
        if code != 0:
            result.warnings.append("SVG fragment generation failed; keeping deterministic HTML fallback.")
        code, output = run_cmd(["python3", str(script_dir / "render-diagram-html.py"), "--output-root", str(self.output_root), "--mode", "rich"], timeout=180)
        if code != 0:
            raise BridgeError(output.strip() or "Slow render failed")
        code, output = run_cmd([str(script_dir / "validate-diagram-html.sh"), str(diagram_html_path(self.output_root))], timeout=180)
        if code != 0:
            raise BridgeError(output.strip() or "Slow validation failed")

    def _write_diff(self, analysis: UpdateAnalysis, result: ApplyResult) -> None:
        before_elements = {str(e.get("id")) for e in (self.baseline_model.get("elements") or []) if isinstance(e, dict)}
        after_elements = {str(e.get("id")) for e in (self.model.get("elements") or []) if isinstance(e, dict)}
        before_rels = {str(r.get("id")) for r in (self.baseline_model.get("relationships") or []) if isinstance(r, dict)}
        after_rels = {str(r.get("id")) for r in (self.model.get("relationships") or []) if isinstance(r, dict)}
        diff = {
            "version": 1,
            "job_id": self.job_id,
            "baseline_revision_id": self.baseline_revision,
            "current_revision_id": compute_revision_id(self.output_root),
            "scope": analysis.scope,
            "comments": [parsed.comment_text for parsed in analysis.parsed_comments],
            "added_elements": sorted(after_elements - before_elements),
            "removed_elements": sorted(before_elements - after_elements),
            "added_relationships": sorted(after_rels - before_rels),
            "removed_relationships": sorted(before_rels - after_rels),
            "changed_elements": sorted(set(result.changed_element_ids)),
            "changed_relationships": sorted(set(result.changed_relationship_ids)),
            "warnings": result.warnings,
        }
        write_yaml(self.arch_dir / "diff.yaml", diff)

    def _run_strict_checks(self, result: ApplyResult) -> None:
        script_dir = Path(__file__).resolve().parents[2] / "architect-plan" / "scripts"
        checks = [
            [
                "python3",
                str(script_dir / "decision-coverage-check.py"),
                "--summary",
                str(self.summary_path),
                "--model",
                str(self.model_path),
                "--views-dir",
                str(self.arch_dir / "views"),
                "--strict",
            ],
            [
                "python3",
                str(script_dir / "container-decomposition-check.py"),
                "--model",
                str(self.model_path),
                "--summary",
                str(self.summary_path),
                "--strict",
                "--only-when-mentioned",
            ],
            [
                "python3",
                str(script_dir / "semantic-diff-gate.py"),
                "--baseline",
                str(feedback_jobs_dir(self.output_root) / self.job_id / "baseline-model.yaml"),
                "--current",
                str(self.model_path),
            ],
        ]
        for cmd in checks:
            code, output = run_cmd(cmd, timeout=180)
            if code != 0:
                result.warnings.append(self._format_check_warning(cmd, output))

    def _format_check_warning(self, cmd: List[str], output: str) -> str:
        script_name = Path(cmd[1]).name if len(cmd) > 1 else "strict-check"
        text = (output or "").strip()
        if not text:
            return f"{script_name} failed"
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                reason = parsed.get("strict_fail_reason") or parsed.get("fail_reasons")
                if isinstance(reason, list):
                    joined = "; ".join([str(x) for x in reason if x])
                    if joined:
                        return f"{script_name}: {joined}"
                if isinstance(reason, str) and reason:
                    return f"{script_name}: {reason}"
        except json.JSONDecodeError:
            pass

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in reversed(lines):
            if line not in {"{", "}"}:
                return f"{script_name}: {line}"
        return f"{script_name} failed"

    def _write_result_summary(self, result: ApplyResult) -> None:
        job_dir = feedback_jobs_dir(self.output_root) / self.job_id
        write_json(
            job_dir / "result.json",
            {
                "job_id": self.job_id,
                "output_root": str(self.output_root),
                "baseline_revision_id": self.baseline_revision,
                "current_revision_id": compute_revision_id(self.output_root),
                "applied_actions": result.applied_actions,
                "warnings": result.warnings,
                "changed_element_ids": sorted(set(result.changed_element_ids)),
                "changed_relationship_ids": sorted(set(result.changed_relationship_ids)),
                "diagram_path": str(diagram_html_path(self.output_root)),
            },
        )


@dataclass
class JobRecord:
    job_id: str
    output_root: Path
    job_dir: Path
    payload: Dict[str, Any]
    subscribers: List[queue.Queue] = field(default_factory=list)


class ClaudeChannelNotifier:
    def __init__(self, url: str, secret: str = "", timeout_seconds: float = 2.0):
        self.url = url.strip()
        self.secret = secret.strip()
        self.timeout_seconds = timeout_seconds

    def _payload_for(self, record: JobRecord, state: str, message: str) -> Dict[str, Any]:
        payload = record.payload
        return {
            "event_type": "architect_feedback_batch",
            "state": state,
            "message": message,
            "job_id": record.job_id,
            "output_root": str(record.output_root),
            "diagram_revision_id": str(payload.get("diagram_revision_id") or ""),
            "bridge_url": str(payload.get("bridge_url") or ""),
            "comments": payload.get("comments") or [],
        }

    def notify(self, record: JobRecord, state: str, message: str) -> None:
        if not self.url:
            return
        payload = self._payload_for(record, state, message)
        job_payload = record.payload
        open_thread_ids = job_payload.get("open_thread_ids")
        if isinstance(open_thread_ids, list) and open_thread_ids:
            payload["open_thread_ids"] = [str(x) for x in open_thread_ids if x]
            payload["open_thread_summary"] = str(job_payload.get("open_thread_summary") or "")
        self._post(payload)

    def notify_thread_event(self, event_type: str, output_root: Path, bridge_url: str, diagram_revision_id: str,
                            thread: Dict[str, Any], message: Optional[Dict[str, Any]] = None) -> None:
        if not self.url:
            return
        payload = {
            "event_type": event_type,
            "output_root": str(output_root),
            "bridge_url": bridge_url or "",
            "diagram_revision_id": diagram_revision_id or "",
            "thread_id": str(thread.get("thread_id") or ""),
            "view_id": str(thread.get("view_id") or ""),
            "element_id": thread.get("element_id"),
            "relationship_id": thread.get("relationship_id"),
            "target_label": str(thread.get("target_label") or ""),
            "status": str(thread.get("status") or ""),
        }
        if message is not None:
            payload["message_id"] = str(message.get("id") or "")
            payload["message_author"] = str(message.get("author") or "")
            payload["message_body"] = str(message.get("body") or "")
        self._post(payload)

    def _post(self, payload: Dict[str, Any]) -> None:
        if not self.url:
            return
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json; charset=utf-8"}
        if self.secret:
            headers["X-Architect-Secret"] = self.secret
        request = urllib.request.Request(self.url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                if response.status >= 400:
                    raise BridgeError(f"channel delivery failed with status {response.status}")
        except urllib.error.URLError as err:
            raise BridgeError(f"channel delivery failed: {err}") from err


class TerminalHostAdapter:
    def __init__(self, verbose: bool = True, channel_notifier: Optional[ClaudeChannelNotifier] = None):
        self.verbose = verbose
        self.channel_notifier = channel_notifier

    def _emit(self, record: JobRecord, state: str, message: str) -> None:
        line = f"[comment-feedback][{record.job_id}] {message}"
        if self.verbose:
            print(line, flush=True)
        atomic_write_text(record.job_dir / "agent-latest.txt", line + "\n")
        if self.channel_notifier:
            self.channel_notifier.notify(record, state, message)

    def acknowledge(self, record: JobRecord, message: str) -> None:
        self._emit(record, "acknowledged", message)

    def announce_state(self, record: JobRecord, message: str, state: str = "analyzing") -> None:
        self._emit(record, state, message)

    def announce_ready(self, record: JobRecord, message: str, state: str = "completed") -> None:
        self._emit(record, state, message)

    def announce_failure(self, record: JobRecord, message: str) -> None:
        self._emit(record, "failed", message)


class JobStore:
    def __init__(self):
        self.records: Dict[str, JobRecord] = {}
        self._lock = threading.Lock()

    def create_job(self, payload: Dict[str, Any]) -> JobRecord:
        output_root = Path(str(payload.get("output_root") or "")).expanduser().resolve()
        arch_dir = architecture_dir(output_root)
        if not output_root.exists() or not arch_dir.exists():
            raise BridgeError(f"output_root must contain architecture/: {output_root}")

        job_id = datetime.now(timezone.utc).strftime("job_%Y-%m-%dT%H-%M-%SZ_") + short_hash(str(time.time()) + str(random.random()), 4)
        job_dir = feedback_jobs_dir(output_root) / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        payload = copy.deepcopy(payload)
        payload["output_root"] = str(output_root)
        payload["job_id"] = job_id
        payload["submitted_at"] = utc_now_iso()
        write_json(job_dir / "input.json", payload)

        baseline_model = architecture_dir(output_root) / "model.yaml"
        if baseline_model.exists():
            atomic_write_text(job_dir / "baseline-model.yaml", baseline_model.read_text(encoding="utf-8"))

        record = JobRecord(job_id=job_id, output_root=output_root, job_dir=job_dir, payload=payload)
        with self._lock:
            self.records[job_id] = record
        self.update_status(
            record,
            "received",
            "Comments sent. The agent is reviewing them now.",
            submitted_comment_count=len(payload.get("comments") or []),
            submitted_revision_id=str(payload.get("diagram_revision_id") or ""),
            needs_refresh=False,
            has_fast_result=False,
            has_final_result=False,
            diagram_path=str(diagram_html_path(output_root)),
            output_root=str(output_root),
            bridge_url=str(payload.get("bridge_url") or ""),
        )
        return record

    def get(self, job_id: str) -> Optional[JobRecord]:
        with self._lock:
            return self.records.get(job_id)

    def update_status(self, record: JobRecord, state: str, message: str, **fields: Any) -> Dict[str, Any]:
        if state not in STATE_ORDER:
            raise BridgeError(f"Unsupported state: {state}")
        status_path = record.job_dir / "status.json"
        status = read_json(status_path, default={}) or {}
        timestamps = status.get("timestamps")
        if not isinstance(timestamps, dict):
            timestamps = {}
        timestamps.setdefault("received_at", utc_now_iso())
        timestamps[f"{state}_at"] = utc_now_iso()
        status.update(fields)
        status.update(
            {
                "job_id": record.job_id,
                "state": state,
                "message": message,
                "timestamps": timestamps,
                "diagram_path": str(diagram_html_path(record.output_root)),
                "output_root": str(record.output_root),
            }
        )
        write_json(status_path, status)
        self._append_event(record, status)
        self._write_latest_pointer(record, status)
        for subscriber in list(record.subscribers):
            try:
                subscriber.put_nowait(status)
            except queue.Full:
                pass
        return status

    def latest_status_for_output_root(self, output_root: Path) -> Optional[Dict[str, Any]]:
        latest_path = feedback_jobs_dir(output_root) / "latest.json"
        latest = read_json(latest_path, default=None)
        if not isinstance(latest, dict):
            return None
        status_path = Path(str(latest.get("status_path") or ""))
        if not status_path.exists():
            return None
        status = read_json(status_path, default=None)
        return status if isinstance(status, dict) else None

    def latest_status_snapshot_for_output_root(self, output_root: Path) -> Dict[str, Any]:
        latest_path = feedback_jobs_dir(output_root) / "latest.json"
        latest = read_json(latest_path, default=None)
        status: Optional[Dict[str, Any]] = None
        latest_job_id: Optional[str] = None
        submitted_revision_id: Optional[str] = None

        if isinstance(latest, dict):
            latest_job_id = str(latest.get("job_id") or "") or None
            status_path = Path(str(latest.get("status_path") or ""))
            if status_path.exists():
                loaded_status = read_json(status_path, default=None)
                if isinstance(loaded_status, dict):
                    status = loaded_status
                    submitted_revision_id = str(loaded_status.get("submitted_revision_id") or "") or None

            if not submitted_revision_id:
                if status_path.exists():
                    input_path = status_path.parent / "input.json"
                elif latest_job_id:
                    input_path = feedback_jobs_dir(output_root) / latest_job_id / "input.json"
                else:
                    input_path = None
                if input_path and input_path.exists():
                    input_payload = read_json(input_path, default=None)
                    if isinstance(input_payload, dict):
                        submitted_revision_id = str(input_payload.get("diagram_revision_id") or "") or None

        return {
            "status": status,
            "diagram_revision_id": current_diagram_revision_id(output_root) or None,
            "submitted_revision_id": submitted_revision_id,
            "latest_job_id": latest_job_id,
        }

    def subscribe(self, record: JobRecord) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=10)
        record.subscribers.append(q)
        return q

    def unsubscribe(self, record: JobRecord, subscriber: queue.Queue) -> None:
        if subscriber in record.subscribers:
            record.subscribers.remove(subscriber)

    def _append_event(self, record: JobRecord, status: Dict[str, Any]) -> None:
        event_path = record.job_dir / "events.ndjson"
        with event_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"event": "state", "data": status}, ensure_ascii=False) + "\n")

    def _write_latest_pointer(self, record: JobRecord, status: Dict[str, Any]) -> None:
        latest_path = feedback_jobs_dir(record.output_root) / "latest.json"
        write_json(
            latest_path,
            {
                "job_id": record.job_id,
                "state": status.get("state"),
                "status_path": str(record.job_dir / "status.json"),
                "result_path": str(record.job_dir / "result.json"),
                "diagram_path": str(diagram_html_path(record.output_root)),
                "output_root": str(record.output_root),
            },
        )


class ClaudeThreadStore:
    """File-backed store for Claude-authored comment threads.

    Threads persist to architecture/.out/claude-comments.json. Subscribers (SSE
    clients) are keyed by output_root so multiple browser tabs on the same
    diagram all receive thread_created, message_appended, and thread_resolved
    events in real time.
    """

    SCHEMA_VERSION = 1

    def __init__(self):
        self._lock = threading.Lock()
        self._subscribers: Dict[str, List[queue.Queue]] = {}

    def _load(self, output_root: Path) -> Dict[str, Any]:
        data = read_json(claude_threads_path(output_root), default=None)
        if not isinstance(data, dict):
            data = {}
        if not isinstance(data.get("threads"), list):
            data["threads"] = []
        data.setdefault("schema_version", self.SCHEMA_VERSION)
        return data

    def _save(self, output_root: Path, data: Dict[str, Any]) -> None:
        data["schema_version"] = self.SCHEMA_VERSION
        data["diagram_revision_id"] = current_diagram_revision_id(output_root)
        write_json(claude_threads_path(output_root), data)

    def snapshot(self, output_root: Path) -> Dict[str, Any]:
        with self._lock:
            return self._load(output_root)

    def open_threads(self, output_root: Path) -> List[Dict[str, Any]]:
        data = self.snapshot(output_root)
        return [t for t in data.get("threads", []) if t.get("status") == "open"]

    def thread_summary(self, output_root: Path, thread_ids: List[str]) -> str:
        data = self.snapshot(output_root)
        lookup = {t.get("thread_id"): t for t in data.get("threads", [])}
        lines: List[str] = []
        for tid in thread_ids:
            thread = lookup.get(tid)
            if not thread:
                continue
            label = thread.get("target_label") or thread.get("thread_id")
            lines.append(f"- {tid} ({label}): awaiting reply")
        return "\n".join(lines)

    def create_thread(self, output_root: Path, *, view_id: str, element_id: Optional[str],
                      relationship_id: Optional[str], target_label: str, body: str,
                      diagram_revision_id: str, author: str = "claude") -> Tuple[Dict[str, Any], Dict[str, Any]]:
        output_root = Path(output_root).expanduser().resolve()
        if not architecture_dir(output_root).exists():
            raise BridgeError(f"output_root must contain architecture/: {output_root}")

        now = utc_now_iso()
        thread_id = "thr_" + short_hash(f"{output_root}|{view_id}|{element_id}|{relationship_id}|{now}|{random.random()}", 10)
        message_id = "msg_" + short_hash(thread_id + now + body, 10)
        message = {"id": message_id, "author": author, "body": body, "created_at": now}
        thread = {
            "thread_id": thread_id,
            "view_id": view_id,
            "element_id": element_id,
            "relationship_id": relationship_id,
            "target_label": target_label,
            "status": "open",
            "resolved_at": None,
            "resolved_by": None,
            "diagram_revision_id": diagram_revision_id or current_diagram_revision_id(output_root),
            "created_at": now,
            "updated_at": now,
            "messages": [message],
        }

        with self._lock:
            data = self._load(output_root)
            data["threads"].append(thread)
            self._save(output_root, data)
        self._broadcast(output_root, "thread_created", {"thread": thread})
        return thread, message

    def append_message(self, output_root: Path, thread_id: str, *, author: str, body: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        output_root = Path(output_root).expanduser().resolve()
        now = utc_now_iso()
        message_id = "msg_" + short_hash(thread_id + now + body + author, 10)
        message = {"id": message_id, "author": author, "body": body, "created_at": now}
        with self._lock:
            data = self._load(output_root)
            for thread in data.get("threads", []):
                if thread.get("thread_id") == thread_id:
                    if thread.get("status") != "open":
                        raise BridgeError(f"thread is not open: {thread_id}")
                    thread.setdefault("messages", []).append(message)
                    thread["updated_at"] = now
                    self._save(output_root, data)
                    self._broadcast(output_root, "message_appended", {"thread_id": thread_id, "message": message})
                    return thread, message
        raise BridgeError(f"thread not found: {thread_id}")

    def resolve_thread(self, output_root: Path, thread_id: str, *, resolved_by: str) -> Dict[str, Any]:
        output_root = Path(output_root).expanduser().resolve()
        now = utc_now_iso()
        with self._lock:
            data = self._load(output_root)
            for thread in data.get("threads", []):
                if thread.get("thread_id") == thread_id:
                    thread["status"] = "resolved"
                    thread["resolved_at"] = now
                    thread["resolved_by"] = resolved_by
                    thread["updated_at"] = now
                    self._save(output_root, data)
                    self._broadcast(output_root, "thread_resolved", {"thread_id": thread_id, "resolved_by": resolved_by, "resolved_at": now})
                    return thread
        raise BridgeError(f"thread not found: {thread_id}")

    def subscribe(self, output_root: Path) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=32)
        key = str(Path(output_root).expanduser().resolve())
        with self._lock:
            self._subscribers.setdefault(key, []).append(q)
        return q

    def unsubscribe(self, output_root: Path, subscriber: queue.Queue) -> None:
        key = str(Path(output_root).expanduser().resolve())
        with self._lock:
            subs = self._subscribers.get(key) or []
            if subscriber in subs:
                subs.remove(subscriber)

    def _broadcast(self, output_root: Path, event: str, data: Dict[str, Any]) -> None:
        key = str(Path(output_root).expanduser().resolve())
        subs = list(self._subscribers.get(key) or [])
        for q in subs:
            try:
                q.put_nowait({"event": event, "data": data})
            except queue.Full:
                pass


class WorkerManager:
    def __init__(self, store: JobStore, adapter: TerminalHostAdapter, channel_handoff_only: bool = False):
        self.store = store
        self.adapter = adapter
        self.channel_handoff_only = channel_handoff_only
        self.output_root_locks: Dict[str, threading.Lock] = {}
        self._lock = threading.Lock()

    def enqueue(self, record: JobRecord) -> None:
        thread = threading.Thread(target=self._run_job, args=(record,), daemon=True)
        thread.start()

    def _root_lock(self, output_root: Path) -> threading.Lock:
        key = str(output_root)
        with self._lock:
            if key not in self.output_root_locks:
                self.output_root_locks[key] = threading.Lock()
            return self.output_root_locks[key]

    def _run_job(self, record: JobRecord) -> None:
        lock = self._root_lock(record.output_root)
        acquired = lock.acquire(blocking=False)
        if not acquired:
            self.store.update_status(
                record,
                "received",
                "Another update is already running. Your comments are queued next.",
                queued=True,
            )
            lock.acquire()
        try:
            ack = summarize_comment_count(len(record.payload.get("comments") or []))
            self.adapter.acknowledge(record, ack)
            self.store.update_status(record, "acknowledged", ack)

            if self.channel_handoff_only:
                waiting_message = "Feedback delivered to Claude. Follow the Claude session for the update."
                self.store.update_status(
                    record,
                    "analyzing",
                    waiting_message,
                    needs_refresh=False,
                    has_fast_result=False,
                    has_final_result=False,
                )
                return

            updater = ArchitectureUpdater(record.output_root, record.job_id, record.payload)
            self.store.update_status(record, "analyzing", "Updating the architecture and diagram now.")
            analysis = updater.analyze()

            self.store.update_status(record, "fast_patch_running", "Updating the architecture and diagram now.")
            fast_result = updater.apply_fast_patch(analysis)

            fast_message = "A quick update is ready. Refresh this page to view it."
            if analysis.needs_slow_path:
                fast_message += " A deeper reconcile is still running."
            self.adapter.announce_ready(record, fast_message, state="fast_patch_ready")
            self.store.update_status(
                record,
                "fast_patch_ready",
                fast_message,
                needs_refresh=True,
                has_fast_result=True,
                has_final_result=not analysis.needs_slow_path,
                refresh_hint="Refresh this page to view the updated diagram.",
                warnings=fast_result.warnings,
            )

            if analysis.needs_slow_path:
                slow_message = "A deeper reconcile is still running. Expect another update soon."
                self.adapter.announce_state(record, slow_message, state="slow_patch_running")
                self.store.update_status(
                    record,
                    "slow_patch_running",
                    slow_message,
                    needs_refresh=True,
                    has_fast_result=True,
                    has_final_result=False,
                    refresh_hint="Refresh this page to view the quick update now.",
                    warnings=fast_result.warnings,
                )
                updater.apply_slow_patch(analysis, fast_result)
                final_message = "The deeper update is ready. Refresh this page to view the latest diagram."
                self.adapter.announce_ready(record, final_message, state="completed")
                self.store.update_status(
                    record,
                    "completed",
                    final_message,
                    needs_refresh=True,
                    has_fast_result=True,
                    has_final_result=True,
                    refresh_hint="Refresh this page to view the latest diagram.",
                    warnings=fast_result.warnings,
                )
            else:
                final_message = "The update is ready. Refresh this page to view the latest diagram."
                updater.finalize_result(fast_result)
                self.store.update_status(
                    record,
                    "completed",
                    final_message,
                    needs_refresh=True,
                    has_fast_result=True,
                    has_final_result=True,
                    refresh_hint="Refresh this page to view the latest diagram.",
                    warnings=fast_result.warnings,
                )
        except BlockedUpdate as err:
            message = str(err)
            self.adapter.announce_failure(record, message)
            self.store.update_status(record, "blocked", message, needs_refresh=False)
        except Exception as err:  # noqa: BLE001
            message = f"The update hit a problem. Open the agent to review the error. ({err})"
            traceback_text = traceback.format_exc()
            atomic_write_text(record.job_dir / "error.log", traceback_text)
            self.adapter.announce_failure(record, message)
            self.store.update_status(record, "failed", message, needs_refresh=False, error=str(err))
        finally:
            lock.release()


class BridgeServer(ThreadingHTTPServer):
    def __init__(self, server_address: Tuple[str, int], handler_cls, store: JobStore, worker: WorkerManager,
                 thread_store: ClaudeThreadStore, notifier: Optional[ClaudeChannelNotifier]):
        super().__init__(server_address, handler_cls)
        self.store = store
        self.worker = worker
        self.thread_store = thread_store
        self.notifier = notifier


class RequestHandler(BaseHTTPRequestHandler):
    server: BridgeServer

    def log_message(self, fmt: str, *args) -> None:
        return

    def _send_json(self, code: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "content-type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def _send_status_event(self, status: Dict[str, Any]) -> None:
        payload = json.dumps({"state": status.get("state"), "message": status.get("message"), "status": status}, ensure_ascii=False)
        self.wfile.write(b"event: state\n")
        self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
        self.wfile.flush()

    def _send_sse(self, event_name: str, data: Dict[str, Any]) -> None:
        body = json.dumps(data, ensure_ascii=False)
        self.wfile.write(f"event: {event_name}\n".encode("utf-8"))
        self.wfile.write(f"data: {body}\n\n".encode("utf-8"))
        self.wfile.flush()

    def _read_json_body(self) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            content_length = int(self.headers.get("Content-Length") or "0")
        except ValueError:
            content_length = 0
        raw = self.rfile.read(content_length)
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return None, "invalid json"
        if not isinstance(payload, dict):
            return None, "body must be a JSON object"
        return payload, None

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "content-type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_json(200, {"ok": True, "time": utc_now_iso()})
            return

        if parsed.path == "/latest-status":
            query = parse_qs(parsed.query)
            raw_root = (query.get("output_root") or [""])[0]
            if not raw_root:
                self._send_json(400, {"error": "output_root is required"})
                return
            output_root = Path(raw_root).expanduser().resolve()
            snapshot = self.server.store.latest_status_snapshot_for_output_root(output_root)
            self._send_json(200, snapshot)
            return

        m = re.match(r"^/jobs/([^/]+)$", parsed.path)
        if m:
            record = self.server.store.get(m.group(1))
            if not record:
                self._send_json(404, {"error": "job not found"})
                return
            status = read_json(record.job_dir / "status.json", default={}) or {}
            self._send_json(200, status)
            return

        m = re.match(r"^/jobs/([^/]+)/events$", parsed.path)
        if m:
            record = self.server.store.get(m.group(1))
            if not record:
                self._send_json(404, {"error": "job not found"})
                return
            subscriber = self.server.store.subscribe(record)
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            current = read_json(record.job_dir / "status.json", default={}) or {}
            self._send_status_event(current)
            try:
                while True:
                    try:
                        status = subscriber.get(timeout=15)
                        self._send_status_event(status)
                    except queue.Empty:
                        self.wfile.write(b": heartbeat\n\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                self.server.store.unsubscribe(record, subscriber)
            return

        if parsed.path == "/claude-threads":
            query = parse_qs(parsed.query)
            raw_root = (query.get("output_root") or [""])[0]
            if not raw_root:
                self._send_json(400, {"error": "output_root is required"})
                return
            output_root = Path(raw_root).expanduser().resolve()
            snapshot = self.server.thread_store.snapshot(output_root)
            self._send_json(200, snapshot)
            return

        if parsed.path == "/claude-threads/events":
            query = parse_qs(parsed.query)
            raw_root = (query.get("output_root") or [""])[0]
            if not raw_root:
                self._send_json(400, {"error": "output_root is required"})
                return
            output_root = Path(raw_root).expanduser().resolve()
            subscriber = self.server.thread_store.subscribe(output_root)
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self._send_sse("snapshot", self.server.thread_store.snapshot(output_root))
            try:
                while True:
                    try:
                        event = subscriber.get(timeout=15)
                        self._send_sse(event["event"], event["data"])
                    except queue.Empty:
                        self.wfile.write(b": heartbeat\n\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                self.server.thread_store.unsubscribe(output_root, subscriber)
            return

        self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        m = re.match(r"^/jobs/([^/]+)/status$", parsed.path)
        if m:
            record = self.server.store.get(m.group(1))
            if not record:
                self._send_json(404, {"error": "job not found"})
                return

            try:
                content_length = int(self.headers.get("Content-Length") or "0")
            except ValueError:
                content_length = 0
            raw = self.rfile.read(content_length)
            try:
                payload = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._send_json(400, {"error": "invalid json"})
                return

            state = payload.get("state")
            message = payload.get("message")
            if not isinstance(state, str) or state not in STATE_ORDER:
                self._send_json(400, {"error": "state must be one of the supported job states"})
                return
            if not isinstance(message, str) or not message.strip():
                self._send_json(400, {"error": "message is required"})
                return

            fields = default_status_fields(state)
            extra_fields = payload.get("fields")
            if isinstance(extra_fields, dict):
                fields.update(extra_fields)
            for key in (
                "needs_refresh",
                "has_fast_result",
                "has_final_result",
                "refresh_hint",
                "warnings",
                "error",
            ):
                if key in payload:
                    fields[key] = payload[key]

            status = self.server.store.update_status(record, state, message.strip(), **fields)
            self._send_json(200, status)
            return

        if parsed.path == "/claude-threads":
            payload, err = self._read_json_body()
            if err or payload is None:
                self._send_json(400, {"error": err or "invalid body"})
                return
            required = ["output_root", "view_id", "target_label", "body"]
            for key in required:
                if not isinstance(payload.get(key), str) or not payload.get(key).strip():
                    self._send_json(400, {"error": f"{key} is required"})
                    return
            element_id = payload.get("element_id")
            relationship_id = payload.get("relationship_id")
            if element_id and relationship_id:
                self._send_json(400, {"error": "element_id and relationship_id are mutually exclusive"})
                return
            try:
                thread, message = self.server.thread_store.create_thread(
                    Path(payload["output_root"]),
                    view_id=payload["view_id"],
                    element_id=element_id,
                    relationship_id=relationship_id,
                    target_label=payload["target_label"],
                    body=payload["body"],
                    diagram_revision_id=str(payload.get("diagram_revision_id") or ""),
                    author=str(payload.get("author") or "claude"),
                )
            except BridgeError as e:
                self._send_json(400, {"error": str(e)})
                return
            self._send_json(201, {"thread": thread, "message": message})
            return

        m = re.match(r"^/claude-threads/([^/]+)/messages$", parsed.path)
        if m:
            thread_id = m.group(1)
            payload, err = self._read_json_body()
            if err or payload is None:
                self._send_json(400, {"error": err or "invalid body"})
                return
            for key in ("output_root", "author", "body"):
                if not isinstance(payload.get(key), str) or not payload.get(key).strip():
                    self._send_json(400, {"error": f"{key} is required"})
                    return
            author = payload["author"]
            if author not in ("user", "claude"):
                self._send_json(400, {"error": "author must be 'user' or 'claude'"})
                return
            try:
                thread, message = self.server.thread_store.append_message(
                    Path(payload["output_root"]),
                    thread_id,
                    author=author,
                    body=payload["body"],
                )
            except BridgeError as e:
                self._send_json(400, {"error": str(e)})
                return
            if author == "user" and self.server.notifier:
                try:
                    self.server.notifier.notify_thread_event(
                        "architect_thread_user_reply",
                        Path(payload["output_root"]),
                        bridge_url=f"http://{self.server.server_address[0]}:{self.server.server_address[1]}",
                        diagram_revision_id=str(payload.get("diagram_revision_id") or ""),
                        thread=thread,
                        message=message,
                    )
                except BridgeError:
                    pass
            self._send_json(200, {"thread": thread, "message": message})
            return

        m = re.match(r"^/claude-threads/([^/]+)/resolve$", parsed.path)
        if m:
            thread_id = m.group(1)
            payload, err = self._read_json_body()
            if err or payload is None:
                self._send_json(400, {"error": err or "invalid body"})
                return
            if not isinstance(payload.get("output_root"), str) or not payload["output_root"].strip():
                self._send_json(400, {"error": "output_root is required"})
                return
            resolved_by = str(payload.get("resolved_by") or "claude")
            if resolved_by not in ("user", "claude"):
                self._send_json(400, {"error": "resolved_by must be 'user' or 'claude'"})
                return
            try:
                thread = self.server.thread_store.resolve_thread(
                    Path(payload["output_root"]),
                    thread_id,
                    resolved_by=resolved_by,
                )
            except BridgeError as e:
                self._send_json(400, {"error": str(e)})
                return
            self._send_json(200, {"thread": thread})
            return

        if parsed.path != "/feedback-batches":
            self._send_json(404, {"error": "not found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length") or "0")
        except ValueError:
            content_length = 0
        raw = self.rfile.read(content_length)
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid json"})
            return

        comments = payload.get("comments")
        if not isinstance(comments, list) or not comments:
            self._send_json(400, {"error": "comments must be a non-empty list"})
            return
        if not payload.get("output_root"):
            self._send_json(400, {"error": "output_root is required"})
            return

        payload["bridge_url"] = f"http://{self.server.server_address[0]}:{self.server.server_address[1]}"

        raw_open_thread_ids = payload.get("open_thread_ids")
        if isinstance(raw_open_thread_ids, list):
            cleaned_ids = [str(x).strip() for x in raw_open_thread_ids if isinstance(x, str) and x.strip()]
            if cleaned_ids:
                payload["open_thread_ids"] = cleaned_ids
                try:
                    payload["open_thread_summary"] = self.server.thread_store.thread_summary(
                        Path(payload["output_root"]), cleaned_ids
                    )
                except Exception:  # noqa: BLE001
                    payload["open_thread_summary"] = ""
            else:
                payload.pop("open_thread_ids", None)

        try:
            record = self.server.store.create_job(payload)
        except Exception as err:  # noqa: BLE001
            self._send_json(400, {"error": str(err)})
            return

        self.server.worker.enqueue(record)
        status = read_json(record.job_dir / "status.json", default={}) or {}
        self._send_json(
            202,
            {
                "job_id": record.job_id,
                "state": status.get("state"),
                "message": status.get("message"),
                "status_url": f"http://{self.server.server_address[0]}:{self.server.server_address[1]}/jobs/{record.job_id}",
                "events_url": f"http://{self.server.server_address[0]}:{self.server.server_address[1]}/jobs/{record.job_id}/events",
                "diagram_path": str(diagram_html_path(record.output_root)),
            },
        )


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the local comment feedback bridge")
    ap.add_argument("--bind", default="127.0.0.1", help="Bind address")
    ap.add_argument("--port", type=int, default=8765, help="Port")
    ap.add_argument("--quiet", action="store_true", help="Reduce terminal logging")
    ap.add_argument("--claude-channel-url", default="", help="Optional Architect Claude channel POST /notify URL")
    ap.add_argument("--claude-channel-secret", default="", help="Optional shared secret for the Architect Claude channel")
    ap.add_argument(
        "--channel-handoff-only",
        action="store_true",
        help="Deliver feedback batches to Claude and skip the built-in deterministic updater",
    )
    args = ap.parse_args()

    store = JobStore()
    thread_store = ClaudeThreadStore()
    notifier = None
    if args.claude_channel_url:
        notifier = ClaudeChannelNotifier(args.claude_channel_url, secret=args.claude_channel_secret)
    adapter = TerminalHostAdapter(verbose=not args.quiet, channel_notifier=notifier)
    worker = WorkerManager(store, adapter, channel_handoff_only=args.channel_handoff_only)
    server = BridgeServer((args.bind, args.port), RequestHandler, store, worker, thread_store, notifier)

    print(f"[comment-feedback] listening on http://{args.bind}:{args.port}", flush=True)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        print("\n[comment-feedback] shutting down", flush=True)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
