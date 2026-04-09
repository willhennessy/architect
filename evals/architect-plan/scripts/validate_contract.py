#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


def load_yaml(path: Path):
    if yaml is None:
        raise RuntimeError("PyYAML is required. Install with: pip install pyyaml")
    return yaml.safe_load(path.read_text()) if path.exists() else None


def check_no_dangling_ids(architecture_dir: Path):
    model = load_yaml(architecture_dir / "model.yaml") or {}
    elements = model.get("elements", []) or []
    relationships = model.get("relationships", []) or []

    element_ids = {e.get("id") for e in elements if e.get("id")}
    rel_ids = {r.get("id") for r in relationships if r.get("id")}

    errors = []

    for r in relationships:
        sid = r.get("source_id")
        tid = r.get("target_id")
        rid = r.get("id")
        if sid not in element_ids:
            errors.append(f"relationship {rid}: missing source element {sid}")
        if tid not in element_ids:
            errors.append(f"relationship {rid}: missing target element {tid}")

    views_dir = architecture_dir / "views"
    for vf in sorted(views_dir.glob("*.yaml")) if views_dir.exists() else []:
        view = load_yaml(vf) or {}
        for eid in view.get("element_ids", []) or []:
            if eid not in element_ids:
                errors.append(f"{vf.name}: unknown element_id {eid}")
        for rid in view.get("relationship_ids", []) or []:
            if rid not in rel_ids:
                errors.append(f"{vf.name}: unknown relationship_id {rid}")

        if view.get("type") == "sequence":
            for pid in view.get("participant_ids", []) or []:
                if pid not in element_ids:
                    errors.append(f"{vf.name}: unknown participant_id {pid}")
            for step in view.get("steps", []) or []:
                sid = step.get("source_id")
                tid = step.get("target_id")
                if sid not in element_ids:
                    errors.append(f"{vf.name}: step source_id missing {sid}")
                if tid not in element_ids:
                    errors.append(f"{vf.name}: step target_id missing {tid}")
                srid = step.get("relationship_id")
                if srid and srid not in rel_ids:
                    errors.append(f"{vf.name}: step relationship_id missing {srid}")

    return len(errors) == 0, errors


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate architect-plan lane A contract checks")
    ap.add_argument("--architecture-dir", required=True, help="Path to architecture directory")
    args = ap.parse_args()

    arch = Path(args.architecture_dir)
    manifest = load_yaml(arch / "manifest.yaml") or {}

    checks = []

    checks.append(
        {
            "name": "generated_by_skill",
            "passed": manifest.get("generated_by_skill") == "architect-plan",
            "evidence": f"generated_by_skill={manifest.get('generated_by_skill')}",
        }
    )

    checks.append(
        {
            "name": "evidence_basis_plan",
            "passed": manifest.get("evidence_basis") == "plan",
            "evidence": f"evidence_basis={manifest.get('evidence_basis')}",
        }
    )

    state = manifest.get("architecture_state")
    state_ok = state in {"proposed", "approved", "implementing", "drifted", None}
    checks.append(
        {
            "name": "architecture_state_allowed",
            "passed": state_ok,
            "evidence": f"architecture_state={state}",
        }
    )

    no_dangling, dangling_errors = check_no_dangling_ids(arch)
    checks.append(
        {
            "name": "no_dangling_ids",
            "passed": no_dangling,
            "evidence": "; ".join(dangling_errors) if dangling_errors else "all IDs resolved",
        }
    )

    passed = all(c["passed"] for c in checks)
    out = {"lane_a_contract": {"passed": passed, "checks": checks}}
    print(json.dumps(out, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
