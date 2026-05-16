#!/usr/bin/env python3
"""
CLI for MSME Credit Pipeline Scheduling.

Examples:
  python run.py --n 8 --K 3 --density 0.3 --seed 1
  python run.py --input instances/toy.json --output out/result.json
  python run.py --benchmark
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Project root on sys.path when run as: python run.py
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.generator import generate_instance
from src.io_handler import save_instance, write_json
from src.models import Instance
from src.scheduler import solve

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


def run_instance(
    instance: Instance,
    output: Path | None,
    brute: bool,
) -> dict:
    result = solve(instance, use_brute_compare=brute)
    data = result.to_dict()
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        write_json(data, output)
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Credit pipeline task scheduler (SCFG)")
    parser.add_argument("--n", type=int, help="Number of tasks")
    parser.add_argument("--K", type=int, help="Number of slots")
    parser.add_argument("--density", type=float, default=0.3, help="Conflict density")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--input", type=str, help="Input JSON instance file")
    parser.add_argument("--output", type=str, help="Output JSON result file")
    parser.add_argument(
        "--save-instance",
        type=str,
        help="Write generated instance JSON to this path",
    )
    parser.add_argument(
        "--brute",
        action="store_true",
        help="Compare to brute-force optimal (n <= 12 only)",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run all 9 assignment benchmark instances",
    )
    args = parser.parse_args()

    if args.benchmark:
        rows = []
        for n, k, density, seed in BENCHMARKS:
            inst = Instance.from_dict(generate_instance(n, k, conflict_density=density, seed=seed))
            brute = n <= 12
            data = run_instance(inst, None, brute)
            row = {
                "n": n,
                "K": k,
                "density": density,
                "seed": seed,
                "penalty": data["penalty"],
                "runtime_ms": data["runtime_ms"],
                "feasible": data["feasible"],
            }
            if "approximation_ratio" in data:
                row["approximation_ratio"] = data["approximation_ratio"]
                row["optimal_penalty"] = data["optimal_penalty"]
            if not data["feasible"]:
                row["violation_reason"] = data["violation_reason"]
            rows.append(row)
            status = "OK" if data["feasible"] else "INFEASIBLE"
            extra = ""
            if "approximation_ratio" in data:
                extra = f" ratio={data['approximation_ratio']:.3f}"
            print(
                f"n={n:3d} K={k:2d} seed={seed:2d}  "
                f"penalty={data['penalty']:.2f}  "
                f"time={data['runtime_ms']}ms  "
                f"{status}{extra}"
            )
        out_dir = Path("output")
        out_dir.mkdir(exist_ok=True)
        write_json(rows, out_dir / "benchmark_results.json")
        print(f"\nWrote {out_dir / 'benchmark_results.json'}")
        return 0

    if args.input:
        from src.io_handler import load_instance

        instance = load_instance(args.input)
        out = Path(args.output) if args.output else None
        data = run_instance(instance, out, args.brute or instance.n <= 12)
    elif args.n is not None and args.K is not None:
        raw = generate_instance(args.n, args.K, conflict_density=args.density, seed=args.seed)
        instance = Instance.from_dict(raw)
        if args.save_instance:
            save_instance(instance, args.save_instance)
        out = Path(args.output) if args.output else Path("output") / f"result_n{args.n}_K{args.K}_s{args.seed}.json"
        data = run_instance(instance, out, args.brute or args.n <= 12)
        if args.save_instance:
            print(f"Instance: {args.save_instance}")
        print(f"Result:   {out}")
    else:
        parser.print_help()
        return 1

    print(json.dumps(data, indent=2))
    return 0 if data["feasible"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
