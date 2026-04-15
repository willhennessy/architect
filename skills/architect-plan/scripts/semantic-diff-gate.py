#!/usr/bin/env python3
"""Semantic drift gate for architecture model revisions.

Compares baseline and current model.yaml files and fails when drift exceeds thresholds.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import yaml


def load_model(path: Path) -> Dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    return data


def element_maps(model: Dict[str, Any]) -> Tuple[Set[str], Dict[str, str]]:
    ids: Set[str] = set()
    by_name: Dict[str, str] = {}
    for e in model.get("elements", []) or []:
        if not isinstance(e, dict):
            continue
        eid = e.get("id")
        name = e.get("name")
        if isinstance(eid, str) and eid:
            ids.add(eid)
        if isinstance(name, str) and name and isinstance(eid, str) and eid:
            key = name.strip().lower()
            if key and key not in by_name:
                by_name[key] = eid
    return ids, by_name


def relationship_ids(model: Dict[str, Any]) -> Set[str]:
    out: Set[str] = set()
    for r in model.get("relationships", []) or []:
        if not isinstance(r, dict):
            continue
        rid = r.get("id")
        if isinstance(rid, str) and rid:
            out.add(rid)
    return out


def pct_delta(added: int, removed: int, baseline: int) -> float:
    denom = baseline if baseline > 0 else 1
    return ((added + removed) / denom) * 100.0


def main() -> int:
    ap = argparse.ArgumentParser(description="Check semantic drift between architecture model revisions")
    ap.add_argument("--baseline", required=True, help="Baseline architecture/model.yaml")
    ap.add_argument("--current", required=True, help="Current architecture/model.yaml")
    ap.add_argument("--max-element-drift-pct", type=float, default=35.0)
    ap.add_argument("--max-relationship-drift-pct", type=float, default=45.0)
    ap.add_argument("--allow-id-shifts", action="store_true", help="Allow name-stable entities to change IDs")
    ap.add_argument("--report-json", help="Optional JSON report path")
    args = ap.parse_args()

    baseline_path = Path(args.baseline)
    current_path = Path(args.current)

    if not baseline_path.exists():
        raise SystemExit(f"ERROR: baseline file not found: {baseline_path}")
    if not current_path.exists():
        raise SystemExit(f"ERROR: current file not found: {current_path}")

    base_model = load_model(baseline_path)
    cur_model = load_model(current_path)

    base_elements, base_by_name = element_maps(base_model)
    cur_elements, cur_by_name = element_maps(cur_model)

    base_rels = relationship_ids(base_model)
    cur_rels = relationship_ids(cur_model)

    added_elements = sorted(cur_elements - base_elements)
    removed_elements = sorted(base_elements - cur_elements)
    added_rels = sorted(cur_rels - base_rels)
    removed_rels = sorted(base_rels - cur_rels)

    name_stable_id_shifts: List[Dict[str, str]] = []
    for name, base_id in base_by_name.items():
        cur_id = cur_by_name.get(name)
        if cur_id and cur_id != base_id:
            name_stable_id_shifts.append({"name": name, "baseline_id": base_id, "current_id": cur_id})

    element_drift_pct = pct_delta(len(added_elements), len(removed_elements), len(base_elements))
    rel_drift_pct = pct_delta(len(added_rels), len(removed_rels), len(base_rels))

    fail_reasons: List[str] = []
    if element_drift_pct > args.max_element_drift_pct:
        fail_reasons.append(
            f"element drift {element_drift_pct:.1f}% exceeds threshold {args.max_element_drift_pct:.1f}%"
        )
    if rel_drift_pct > args.max_relationship_drift_pct:
        fail_reasons.append(
            f"relationship drift {rel_drift_pct:.1f}% exceeds threshold {args.max_relationship_drift_pct:.1f}%"
        )
    if name_stable_id_shifts and not args.allow_id_shifts:
        fail_reasons.append(
            f"found {len(name_stable_id_shifts)} name-stable ID shifts (enable --allow-id-shifts to bypass)"
        )

    report: Dict[str, Any] = {
        "baseline": str(baseline_path),
        "current": str(current_path),
        "element_counts": {"baseline": len(base_elements), "current": len(cur_elements)},
        "relationship_counts": {"baseline": len(base_rels), "current": len(cur_rels)},
        "element_drift_pct": round(element_drift_pct, 2),
        "relationship_drift_pct": round(rel_drift_pct, 2),
        "added_elements": added_elements,
        "removed_elements": removed_elements,
        "added_relationships": added_rels,
        "removed_relationships": removed_rels,
        "name_stable_id_shifts": name_stable_id_shifts,
        "fail_reasons": fail_reasons,
        "pass": not fail_reasons,
    }

    if args.report_json:
        Path(args.report_json).write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))

    return 0 if report["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
