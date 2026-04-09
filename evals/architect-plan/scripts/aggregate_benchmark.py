#!/usr/bin/env python3
import argparse
import json
import statistics
from pathlib import Path


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def mean_std(values):
    if not values:
        return {"mean": None, "stddev": None}
    if len(values) == 1:
        return {"mean": values[0], "stddev": 0.0}
    return {"mean": sum(values) / len(values), "stddev": statistics.pstdev(values)}


def _is_placeholder_run(run_dir: Path, timing: dict, grading: dict) -> bool:
    total_tokens = float(timing.get("total_tokens", 0) or 0)
    duration_ms = float(timing.get("duration_ms", 0) or 0)

    outputs_dir = run_dir / "outputs"
    has_outputs = outputs_dir.exists() and any(outputs_dir.rglob("*"))

    lane_a_checks = (grading.get("lane_a_contract", {}) or {}).get("checks", []) or []

    return (total_tokens == 0 and duration_ms == 0 and not has_outputs and len(lane_a_checks) == 0)


def collect_run_metrics(run_dir: Path):
    grading = load_json(run_dir / "grading.json", {})
    timing = load_json(run_dir / "timing.json", {})

    if _is_placeholder_run(run_dir, timing, grading):
        return None

    lane_a = grading.get("lane_a_contract", {}) or {}
    lane_b = grading.get("lane_b_semantic", {}) or {}
    lane_c = grading.get("lane_c_steering_loop", {}) or {}

    return {
        "contract_pass": bool(lane_a.get("passed", False)),
        "semantic_score_40": float(lane_b.get("semantic_score_40", 0) or 0),
        "feedback_incorporation_success_rate": float(lane_c.get("feedback_incorporation_success_rate", 0) or 0),
        "unchanged_id_churn_pct": float(lane_c.get("unchanged_id_churn_pct", 0) or 0),
        "rounds_to_approval": int(lane_c.get("rounds_to_approval", 0) or 0),
        "critical_hallucinations": int(lane_c.get("critical_hallucinations", 0) or 0),
        "duration_ms": float(timing.get("duration_ms", 0) or 0),
        "total_tokens": float(timing.get("total_tokens", 0) or 0),
    }


def summarize(metrics_list):
    if not metrics_list:
        return {
            "case_count": 0,
            "contract_pass_rate": None,
            "semantic_score_40": {"mean": None, "stddev": None},
            "feedback_incorporation_success_rate": {"mean": None, "stddev": None},
            "unchanged_id_churn_pct": {"mean": None, "stddev": None},
            "rounds_to_approval": {"median": None},
            "critical_hallucinations_total": None,
            "time_seconds": {"mean": None, "stddev": None},
            "tokens": {"mean": None, "stddev": None},
        }

    contract_rate = sum(1 for m in metrics_list if m["contract_pass"]) / len(metrics_list)
    semantic = mean_std([m["semantic_score_40"] for m in metrics_list])
    fic = mean_std([m["feedback_incorporation_success_rate"] for m in metrics_list])
    churn = mean_std([m["unchanged_id_churn_pct"] for m in metrics_list])
    rounds = [m["rounds_to_approval"] for m in metrics_list if m["rounds_to_approval"] > 0]
    median_rounds = statistics.median(rounds) if rounds else None
    hall_total = sum(m["critical_hallucinations"] for m in metrics_list)
    time_stats = mean_std([m["duration_ms"] / 1000.0 for m in metrics_list])
    tok_stats = mean_std([m["total_tokens"] for m in metrics_list])

    return {
        "case_count": len(metrics_list),
        "contract_pass_rate": contract_rate,
        "semantic_score_40": semantic,
        "feedback_incorporation_success_rate": fic,
        "unchanged_id_churn_pct": churn,
        "rounds_to_approval": {"median": median_rounds},
        "critical_hallucinations_total": hall_total,
        "time_seconds": time_stats,
        "tokens": tok_stats,
    }


def compute_delta(with_summary, base_summary):
    def mean_or_none(section, key):
        item = section.get(key, {})
        if isinstance(item, dict):
            return item.get("mean")
        return item

    ws = mean_or_none(with_summary, "semantic_score_40")
    bs = mean_or_none(base_summary, "semantic_score_40")
    wt = mean_or_none(with_summary, "time_seconds")
    bt = mean_or_none(base_summary, "time_seconds")
    wtok = mean_or_none(with_summary, "tokens")
    btok = mean_or_none(base_summary, "tokens")

    return {
        "semantic_score_40": (None if ws is None or bs is None else ws - bs),
        "time_seconds": (None if wt is None or bt is None else wt - bt),
        "tokens": (None if wtok is None or btok is None else wtok - btok),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Aggregate architect-plan iteration benchmark")
    ap.add_argument("--iteration", required=True, help="Path to iteration-N directory")
    args = ap.parse_args()

    it_dir = Path(args.iteration)
    if not it_dir.exists():
        raise SystemExit(f"Iteration dir not found: {it_dir}")

    iteration_num = int(it_dir.name.split("-")[1]) if "-" in it_dir.name else None
    baseline_mode = "without_skill" if iteration_num == 1 else "old_skill"

    with_metrics = []
    base_metrics = []

    for case_dir in sorted(it_dir.glob("eval-*")):
        with_dir = case_dir / "with_skill"
        base_dir = case_dir / baseline_mode
        if with_dir.exists():
            m = collect_run_metrics(with_dir)
            if m is not None:
                with_metrics.append(m)
        if base_dir.exists():
            m = collect_run_metrics(base_dir)
            if m is not None:
                base_metrics.append(m)

    with_summary = summarize(with_metrics)
    base_summary = summarize(base_metrics)
    delta = compute_delta(with_summary, base_summary)

    contract_rate = with_summary.get("contract_pass_rate")
    semantic_mean = with_summary.get("semantic_score_40", {}).get("mean")
    fic_mean = with_summary.get("feedback_incorporation_success_rate", {}).get("mean")
    churn_mean = with_summary.get("unchanged_id_churn_pct", {}).get("mean")
    rounds_median = with_summary.get("rounds_to_approval", {}).get("median")
    critical_total = with_summary.get("critical_hallucinations_total")

    gates = {
        "contract_pass_100": (contract_rate == 1.0),
        "critical_hallucinations_zero": (critical_total == 0),
        "avg_semantic_gte_32_of_40": (semantic_mean is not None and semantic_mean >= 32),
        "feedback_incorp_gte_80": (fic_mean is not None and fic_mean >= 80),
        "id_churn_lte_10": (churn_mean is not None and churn_mean <= 10),
        "median_rounds_lte_3": (rounds_median is not None and rounds_median <= 3),
    }
    gates["ready_to_promote"] = all(gates.values())

    out = {
        "iteration": iteration_num,
        "baseline_mode": baseline_mode,
        "run_summary": {
            "with_skill": with_summary,
            baseline_mode: base_summary,
            "delta": delta,
        },
        "promotion_gates": gates,
    }

    (it_dir / "benchmark.json").write_text(json.dumps(out, indent=2) + "\n")
    print(f"Wrote {(it_dir / 'benchmark.json')} with ready_to_promote={gates['ready_to_promote']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
