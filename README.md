# MSME Credit Pipeline Scheduling — ScoreMe Assignment

Polynomial-time heuristic (**SCFG-MR**) for assigning credit-pipeline tasks to cluster slots under conflict, capacity, and SLA constraints.

## Quick start

```powershell
cd c:\assessment
pip install -r requirements.txt
python -m pytest tests/ -v
python run.py --input instances/toy.json
python run.py --benchmark
python scripts/make_charts.py
```

## Submission contents

| File | Description |
|------|-------------|
| **REPORT.md** | Written submission Tasks 1–7 |
| **AI_USAGE_LOG.md** | Required AI usage disclosure |
| **src/** | Implementation (Task 5) |
| **tests/** | Unit tests |
| **output/** | Benchmark JSON + charts (Task 6) |
| **instances/toy.json** | Assignment toy instance |

## Output format

```json
{
  "assignment": {"T0": 1, "T1": 2},
  "penalty": 42.5,
  "runtime_ms": 3,
  "feasible": true,
  "violation_reason": ""
}
```

## Task 8 (Viva)

Prepare from `REPORT.md` Task 3 pseudocode and `src/scheduler.py`. Practice tracing `instances/toy.json` by hand.
