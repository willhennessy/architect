#!/usr/bin/env python3
"""Decision coverage checker for architecture plan outputs.

Checks whether key decisions in summary.md are grounded in model/view artifacts.
Supports explicit coverage annotations and keyword-based fallback checks.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import yaml

STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "into",
    "that",
    "this",
    "will",
    "should",
    "must",
    "have",
    "has",
    "use",
    "using",
    "only",
    "when",
    "where",
    "than",
    "over",
    "under",
    "across",
    "about",
    "then",
    "also",
    "mode",
    "plan",
    "mvp",
    "service",
    "system",
}


def load_yaml(path: Path) -> Dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def parse_key_decision_lines(summary_text: str) -> List[str]:
    lines = summary_text.splitlines()
    in_section = False
    out: List[str] = []
    for line in lines:
        if re.match(r"^##+\s+", line):
            heading = re.sub(r"^##+\s+", "", line).strip().lower()
            in_section = "key decisions" in heading or "decisions locked" in heading
            continue
        if not in_section:
            continue
        if re.match(r"^\s*[-*]\s+", line):
            out.append(re.sub(r"^\s*[-*]\s+", "", line).strip())
        elif line.strip() == "":
            continue
        elif re.match(r"^##+\s+", line):
            break
    return out


def extract_cover_ids(decision_line: str) -> List[str]:
    m = re.search(r"\bcovers\s*:\s*([A-Za-z0-9_.,\-\s]+)", decision_line, flags=re.IGNORECASE)
    if not m:
        return []
    raw = m.group(1)
    ids = [x.strip() for x in raw.split(",") if x.strip()]
    return ids


def keyword_tokens(text: str) -> Set[str]:
    cleaned = re.sub(r"\bcovers\s*:\s*.*$", "", text, flags=re.IGNORECASE)
    words = re.findall(r"[A-Za-z][A-Za-z0-9_\-/]{3,}", cleaned.lower())
    return {w for w in words if w not in STOPWORDS}


def build_artifact_corpus(model: Dict[str, Any], views: List[Dict[str, Any]]) -> str:
    chunks: List[str] = []
    for e in model.get("elements", []) or []:
        if isinstance(e, dict):
            chunks.extend([str(e.get("id", "")), str(e.get("name", "")), str(e.get("description", ""))])
    for r in model.get("relationships", []) or []:
        if isinstance(r, dict):
            chunks.extend([str(r.get("id", "")), str(r.get("label", "")), str(r.get("protocol", ""))])
    for v in views:
        chunks.extend([str(v.get("id", "")), str(v.get("title", "")), str(v.get("type", ""))])
    return "\n".join(chunks).lower()


def load_views(views_dir: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in sorted(views_dir.glob("*.y*ml")):
        d = load_yaml(p)
        d.setdefault("id", p.stem)
        out.append(d)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Check key decision coverage against architecture artifacts")
    ap.add_argument("--summary", required=True, help="Path to architecture/summary.md")
    ap.add_argument("--model", required=True, help="Path to architecture/model.yaml")
    ap.add_argument("--views-dir", required=True, help="Path to architecture/views")
    ap.add_argument("--strict", action="store_true", help="Fail if uncovered decisions are found")
    ap.add_argument("--min-keyword-matches", type=int, default=1)
    ap.add_argument("--report-json", help="Optional JSON report path")
    args = ap.parse_args()

    summary_path = Path(args.summary)
    model_path = Path(args.model)
    views_dir = Path(args.views_dir)

    if not summary_path.exists() or not model_path.exists() or not views_dir.exists():
        raise SystemExit("ERROR: summary/model/views inputs must exist")

    summary_text = summary_path.read_text(encoding="utf-8")
    model = load_yaml(model_path)
    views = load_views(views_dir)

    decision_lines = parse_key_decision_lines(summary_text)
    model_element_ids = {e.get("id") for e in (model.get("elements") or []) if isinstance(e, dict) and e.get("id")}
    model_rel_ids = {r.get("id") for r in (model.get("relationships") or []) if isinstance(r, dict) and r.get("id")}
    view_ids = {v.get("id") for v in views if v.get("id")}
    corpus = build_artifact_corpus(model, views)

    coverage_rows: List[Dict[str, Any]] = []
    uncovered: List[str] = []

    for line in decision_lines:
        explicit_ids = extract_cover_ids(line)
        valid_explicit = [
            i
            for i in explicit_ids
            if i in model_element_ids or i in model_rel_ids or i in view_ids
        ]

        keywords = keyword_tokens(line)
        keyword_matches = [k for k in sorted(keywords) if k in corpus]

        covered = bool(valid_explicit) or (len(keyword_matches) >= args.min_keyword_matches)
        if not covered:
            uncovered.append(line)

        coverage_rows.append(
            {
                "decision": line,
                "explicit_cover_ids": explicit_ids,
                "valid_cover_ids": valid_explicit,
                "keyword_matches": keyword_matches,
                "covered": covered,
            }
        )

    strict_pass = True
    if args.strict:
        strict_pass = len(uncovered) == 0 and len(decision_lines) > 0

    report = {
        "decision_count": len(decision_lines),
        "covered_count": len([r for r in coverage_rows if r["covered"]]),
        "uncovered_count": len(uncovered),
        "rows": coverage_rows,
        "strict": args.strict,
        "pass": strict_pass if args.strict else True,
        "strict_fail_reason": None if strict_pass else "strict mode requires at least one key decision and full coverage",
    }

    if args.report_json:
        Path(args.report_json).write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))

    return 0 if report["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
