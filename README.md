# MSME Credit Pipeline Scheduling — ScoreMe Assignment

**ScoreMe Solutions Pvt. Ltd.** — Advanced Systems Design assessment  
**Algorithm:** SCFG-MR (SLA-Weighted Conflict-First Greedy with Multi-Restart)

Assign credit-pipeline tasks to discrete cluster **slots** while respecting **conflict** (F1), **resource capacity** (F2), and **SLA windows** (F3), and minimizing a custom **penalty** P(σ).

---

## Assignment status

| Task | Points | Status | Location |
|------|--------|--------|----------|
| 1 — NP-hardness proof | 20 | Done | `REPORT.md` § Task 1 |
| 2 — Penalty function | 15 | Done | `REPORT.md` § Task 2, `src/penalty.py` |
| 3 — Algorithm design | 40 | Done | `REPORT.md` § Task 3, `src/scheduler.py` |
| 4 — Approximation bounds | 30 | Done | `REPORT.md` § Task 4 |
| 5 — Python implementation | 25 | Done | `src/`, `run.py`, `tests/` |
| 6 — Benchmarking & charts | 20 | Done | `output/`, `REPORT.md` § Task 6 |
| 7 — Design journal | 20 | Done | `REPORT.md` § Task 7 |
| 8 — Viva voce (live oral) | 30 | **You** — after submit | See below |

**Also required:** `AI_USAGE_LOG.md` (sign before submitting)

---

## Project structure

```
assessment/
├── REPORT.md              # Written submission (Tasks 1–7)
├── AI_USAGE_LOG.md        # AI disclosure + attestation
├── README.md              # This file
├── run.py                 # CLI entry point
├── requirements.txt
├── src/
│   ├── generator.py       # Random instances (assignment spec)
│   ├── models.py          # Instance & ScheduleResult
│   ├── penalty.py         # P(σ) = base + imbalance + SLA risk
│   ├── validation.py      # F1, F2, F3 checks
│   ├── scheduler.py       # SCFG-MR solver
│   └── io_handler.py      # JSON load/save
├── tests/
│   └── test_scheduler.py  # 5 required unit tests
├── instances/
│   └── toy.json           # 6-task example from assignment doc
├── scripts/
│   └── make_charts.py     # Regenerate benchmarks + Task 6 charts
└── output/
    ├── benchmark_results.json
    ├── chart_penalty_vs_n.png
    └── chart_runtime_vs_n.png
```

---

## Setup

**Requirements:** Python 3.10+

```powershell
cd c:\assessment
pip install -r requirements.txt
```

---

## Run & test

### Unit tests (Task 5)

```powershell
python -m pytest tests/ -v
```

### Toy instance (assignment doc example)

```powershell
python run.py --input instances/toy.json
```

### Random instance

```powershell
python run.py --n 8 --K 3 --density 0.3 --seed 1
python run.py --n 8 --K 3 --density 0.3 --seed 1 --brute   # + optimal compare (n ≤ 12)
```

### Save instance and result

```powershell
python run.py --n 10 --K 4 --density 0.4 --seed 2 --save-instance instances/generated.json --output output/result.json --brute
```

### Full benchmark suite (Task 6)

```powershell
python run.py --benchmark
python scripts/make_charts.py    # same 9 runs + PNG charts
```

---

## Output format (Task 5)

```json
{
  "assignment": { "T0": 1, "T1": 3 },
  "penalty": 72.59,
  "runtime_ms": 0,
  "feasible": true,
  "violation_reason": "",
  "optimal_penalty": 72.59,
  "approximation_ratio": 1.0
}
```

`optimal_penalty` and `approximation_ratio` appear only when `--brute` is used and `n ≤ 12`.

**Slots are 1-based** in `assignment`. SLA `windows` in JSON are 0-based from the generator; valid slots are `[lo+1, hi+1]`.

---

## Benchmark summary (latest)

| n | K | seed | Feasible | Approx. ratio |
|---|-----|------|----------|----------------|
| 8 | 3 | 1 | Yes | 1.00 |
| 10 | 4 | 2 | Yes | ~1.22 |
| 12 | 4 | 3 | Yes | 1.00 |
| 50–200 | various | 10–22 | No | — |

Details and analysis: `REPORT.md` Task 6 and `output/benchmark_results.json`.

---

## What to submit

Zip or upload (per ScoreMe instructions):

| Include | Notes |
|---------|--------|
| `REPORT.md` | Main report; convert to PDF if required |
| `AI_USAGE_LOG.md` | Fill name/date on attestation line |
| `src/`, `tests/`, `run.py`, `requirements.txt` | Code |
| `instances/toy.json` | Toy instance |
| `output/benchmark_results.json` | Task 6 table |
| `output/chart_penalty_vs_n.png` | Task 6 chart |
| `output/chart_runtime_vs_n.png` | Task 6 chart |

**Do not submit:** `sch/` (local venv), `.pytest_cache/`, large `output/result_*.json` unless asked.


---

## Constraints (assignment rules)

**Forbidden:** OR-Tools, PuLP, CPLEX, Gurobi, Z3, `networkx.coloring`, SAT solvers  

**Allowed:** numpy, pandas, matplotlib, standard library, custom data structures

---

## References

- Problem statement: `Fullstack Assignment.docx` / `assignment.txt`
- Full write-up: `REPORT.md`
