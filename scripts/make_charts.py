#!/usr/bin/env python3
"""Generate Task 6 charts from benchmark_results.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BENCHMARKS = [
    (8, 3, 0.3, 1),
    (10, 4, 0.4, 2),
    (12, 4, 0.5, 3),
    (50, 8, 0.25, 10),
    (100, 10, 0.30, 11),
    (150, 12, 0.35, 12),
    (200, 15, 0.40, 20),
    (200, 5, 0.60, 21),
    (200, 20, 0.10, 22),
]


def main() -> None:
    from src.generator import generate_instance
    from src.models import Instance
    from src.scheduler import solve

    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)

    rows = []
    for n, k, density, seed in BENCHMARKS:
        inst = Instance.from_dict(generate_instance(n, k, conflict_density=density, seed=seed))
        result = solve(inst, use_brute_compare=n <= 12)
        row = {
            "n": n,
            "K": k,
            "density": density,
            "seed": seed,
            "penalty": result.penalty if result.feasible else None,
            "runtime_ms": result.runtime_ms,
            "feasible": result.feasible,
            "violation_reason": result.violation_reason,
        }
        if result.approximation_ratio is not None:
            row["approximation_ratio"] = result.approximation_ratio
            row["optimal_penalty"] = result.optimal_penalty
        rows.append(row)

    write_json = lambda data, p: p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    write_json(rows, out_dir / "benchmark_results.json")

    labels = [f"n={r['n']}\nK={r['K']}" for r in rows]
    penalties = [r["penalty"] if r["feasible"] and r["penalty"] is not None else 0 for r in rows]
    runtimes = [r["runtime_ms"] for r in rows]
    feasible_mask = [r["feasible"] for r in rows]

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ["#2ecc71" if f else "#e74c3c" for f in feasible_mask]
    ax.bar(range(len(rows)), penalties, color=colors)
    ax.set_xticks(range(len(rows)))
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("Penalty P(σ)")
    ax.set_title("Task 6: Penalty vs benchmark instance (green=feasible, red=infeasible)")
    fig.tight_layout()
    fig.savefig(out_dir / "chart_penalty_vs_n.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(range(len(rows)), runtimes, marker="o", color="#3498db", linewidth=2)
    ax.set_xticks(range(len(rows)))
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("Runtime (ms)")
    ax.set_title("Task 6: Runtime vs benchmark instance")
    fig.tight_layout()
    fig.savefig(out_dir / "chart_runtime_vs_n.png", dpi=150)
    plt.close(fig)

    print(f"Wrote {out_dir / 'benchmark_results.json'}")
    print(f"Wrote {out_dir / 'chart_penalty_vs_n.png'}")
    print(f"Wrote {out_dir / 'chart_runtime_vs_n.png'}")


if __name__ == "__main__":
    main()
