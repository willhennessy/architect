#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def next_iteration(root: Path) -> int:
    nums = []
    for d in root.glob("iteration-*"):
        try:
            nums.append(int(d.name.split("-")[1]))
        except Exception:
            pass
    return (max(nums) + 1) if nums else 1


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Initialize architect-plan eval iteration workspace")
    ap.add_argument("--root", default="evals/architect-plan", help="architect-plan eval root")
    ap.add_argument(
        "--baseline-mode",
        choices=["auto", "without_skill", "old_skill"],
        default="auto",
        help="baseline folder to create",
    )
    ap.add_argument("--iteration-number", type=int, default=None, help="explicit iteration number to initialize")
    args = ap.parse_args()

    root = Path(args.root)
    evals_path = root / "evals.json"
    if not evals_path.exists():
        raise SystemExit(f"Missing eval definition file: {evals_path}")

    data = json.loads(evals_path.read_text())
    cases = data.get("evals", [])
    if not cases:
        raise SystemExit("No cases found in evals.json")

    it_num = args.iteration_number if args.iteration_number is not None else next_iteration(root)
    if it_num <= 0:
        raise SystemExit("iteration-number must be >= 1")

    it_dir = root / f"iteration-{it_num}"
    it_dir.mkdir(parents=True, exist_ok=True)

    baseline_mode = args.baseline_mode
    if baseline_mode == "auto":
        baseline_mode = "without_skill" if it_num == 1 else "old_skill"

    for case in cases:
        slug = case.get("slug") or f"case-{case.get('id', 'unknown')}"
        case_dir = it_dir / f"eval-{slug}"
        with_dir = case_dir / "with_skill"
        base_dir = case_dir / baseline_mode

        for run_dir in (with_dir, base_dir):
            (run_dir / "outputs").mkdir(parents=True, exist_ok=True)
            write_json(
                run_dir / "timing.json",
                {"total_tokens": 0, "duration_ms": 0},
            )
            write_json(
                run_dir / "grading.json",
                {
                    "lane_a_contract": {"passed": False, "checks": []},
                    "lane_b_semantic": {
                        "scores": {
                            "scope_boundary_correctness": 1,
                            "data_ownership_sor_clarity": 1,
                            "workflow_sequence_correctness": 1,
                            "rationale_quality": 1,
                            "uncertainty_handling": 1,
                        },
                        "semantic_raw_total": 5,
                        "semantic_score_40": 8.0,
                        "evidence_notes": [],
                    },
                    "lane_c_steering_loop": {
                        "asks_targeted_feedback": False,
                        "feedback_incorporation_success_rate": 0,
                        "unchanged_id_churn_pct": 0,
                        "rounds_to_approval": 0,
                        "critical_hallucinations": 0,
                        "evidence_notes": [],
                    },
                    "gate_readiness": {
                        "contract_pass_100": False,
                        "critical_hallucinations_zero": False,
                        "avg_semantic_gte_32_of_40": False,
                        "feedback_incorp_gte_80": False,
                        "id_churn_lte_10": False,
                        "median_rounds_lte_3": False,
                    },
                },
            )
            (run_dir / "transcript.md").write_text("# Transcript notes\n\n")

    write_json(it_dir / "feedback.json", {"notes": {}})

    write_json(
        it_dir / "benchmark.json",
        {
            "iteration": it_num,
            "baseline_mode": baseline_mode,
            "run_summary": {
                "with_skill": {},
                baseline_mode: {},
                "delta": {},
            },
            "promotion_gates": {
                "contract_pass_100": False,
                "critical_hallucinations_zero": False,
                "avg_semantic_gte_32_of_40": False,
                "feedback_incorp_gte_80": False,
                "id_churn_lte_10": False,
                "median_rounds_lte_3": False,
                "ready_to_promote": False,
            },
        },
    )

    print(f"Initialized {it_dir} using baseline_mode={baseline_mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
