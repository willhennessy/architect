#!/usr/bin/env python3
"""Container decomposition policy check for async responsibilities.

Guardrail: webhook / notification / audit responsibilities should be separated
into distinct containers unless there is explicit merge justification.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Set

import yaml

TOKENS = ["webhook", "notification", "audit"]


def load_yaml(path: Path) -> Dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def load_text(path: Path | None) -> str:
    if path is None:
        return ""
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").lower()


def element_text(e: Dict[str, Any]) -> str:
    parts: List[str] = [
        str(e.get("id", "")),
        str(e.get("name", "")),
        str(e.get("description", "")),
    ]
    tags = e.get("tags") or []
    if isinstance(tags, list):
        parts.extend([str(t) for t in tags])
    return " ".join(parts).lower()


def is_container_like(e: Dict[str, Any]) -> bool:
    kind = str(e.get("kind", "")).lower()
    return kind in {
        "container",
        "component",
        "service",
        "worker",
        "job",
        "software_system",
        "system",
    }


def has_merge_justification(summary_text: str, tokens: List[str]) -> bool:
    if not summary_text.strip():
        return False

    # Accept explicit rationale cues around consolidation language.
    patterns = [
        r"justification\s*:\s*.*(merge|merged|combine|combined|consolidat)",
        r"(merge|merged|combine|combined|consolidat).*(webhook|notification|audit)",
        r"single\s+(worker|service).*(webhook|notification|audit)",
    ]
    for p in patterns:
        if re.search(p, summary_text):
            return True

    # Lightweight heuristic: if summary explicitly says tradeoff for consolidation.
    if "tradeoff" in summary_text and any(t in summary_text for t in tokens) and (
        "single" in summary_text or "merged" in summary_text or "combined" in summary_text
    ):
        return True

    return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Check async container decomposition policy")
    ap.add_argument("--model", required=True, help="Path to architecture/model.yaml")
    ap.add_argument("--summary", help="Path to architecture/summary.md for merge justification detection")
    ap.add_argument("--strict", action="store_true", help="Fail when policy violations are found")
    ap.add_argument(
        "--only-when-mentioned",
        action="store_true",
        help="Only enforce token checks for responsibilities mentioned in summary text",
    )
    ap.add_argument("--report-json", help="Optional JSON report path")
    args = ap.parse_args()

    model_path = Path(args.model)
    if not model_path.exists():
        raise SystemExit(f"ERROR: model file not found: {model_path}")

    summary_path = Path(args.summary) if args.summary else None
    summary_text = load_text(summary_path)

    model = load_yaml(model_path)
    elements = [e for e in (model.get("elements") or []) if isinstance(e, dict) and is_container_like(e)]

    token_to_ids: Dict[str, Set[str]] = {t: set() for t in TOKENS}
    id_to_tokens: Dict[str, Set[str]] = {}

    for e in elements:
        eid = e.get("id")
        if not isinstance(eid, str) or not eid:
            continue
        txt = element_text(e)
        matched = {t for t in TOKENS if t in txt}
        if not matched:
            continue
        id_to_tokens[eid] = matched
        for t in matched:
            token_to_ids[t].add(eid)

    expected_tokens = TOKENS[:]
    if args.only_when_mentioned and summary_text:
        expected_tokens = [t for t in TOKENS if t in summary_text]

    missing_tokens = [t for t in expected_tokens if not token_to_ids.get(t)]

    active_tokens = [t for t in expected_tokens if token_to_ids.get(t)]
    unique_ids: Set[str] = set()
    for t in active_tokens:
        unique_ids.update(token_to_ids[t])

    merged_detected = len(active_tokens) > 1 and len(unique_ids) < len(active_tokens)
    justification = has_merge_justification(summary_text, active_tokens)

    fail_reasons: List[str] = []
    if missing_tokens:
        fail_reasons.append(f"missing dedicated container evidence for: {', '.join(missing_tokens)}")
    if merged_detected and not justification:
        fail_reasons.append(
            "async responsibilities appear merged into too few containers without explicit justification"
        )

    report: Dict[str, Any] = {
        "model": str(model_path),
        "summary": str(summary_path) if summary_path else None,
        "expected_tokens": expected_tokens,
        "token_to_container_ids": {k: sorted(v) for k, v in token_to_ids.items()},
        "containers_with_multiple_async_tokens": [
            {"id": eid, "tokens": sorted(list(ts))}
            for eid, ts in sorted(id_to_tokens.items())
            if len(ts) > 1
        ],
        "merged_detected": merged_detected,
        "merge_justification_found": justification,
        "missing_tokens": missing_tokens,
        "fail_reasons": fail_reasons,
        "strict": args.strict,
        "pass": (len(fail_reasons) == 0) if args.strict else True,
    }

    if args.report_json:
        Path(args.report_json).write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    return 0 if report["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
