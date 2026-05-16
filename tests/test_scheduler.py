"""Unit tests for SCFG scheduler (Task 5 requirements)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.models import Instance
from src.scheduler import brute_force_optimal, solve
from src.validation import check_feasibility


def _instance(**overrides) -> Instance:
    base = dict(
        tasks=["T0"],
        conflicts=[],
        resources=[[2.0, 4.0, 0.0, 0.5]],
        capacities=[[32.0, 128.0, 8.0, 6.0]],
        windows=[(0, 0)],
        weights=[5.0],
        K=1,
    )
    base.update(overrides)
    return Instance.from_dict(base)


def test_single_task_instance():
    """Single task must be assigned to its only valid slot."""
    inst = _instance()
    result = solve(inst)
    assert result.feasible
    assert result.assignment == {"T0": 1}
    assert result.penalty < float("inf")


def test_all_conflict_graph_infeasible_when_k_too_small():
    """Complete graph on 4 tasks needs K >= 4; K=2 cannot be feasible."""
    n = 4
    conflicts = [(i, j) for i in range(n) for j in range(i + 1, n)]
    inst = Instance.from_dict(
        dict(
            tasks=[f"T{i}" for i in range(n)],
            conflicts=conflicts,
            resources=[[1.0, 1.0, 0.0, 0.1] for _ in range(n)],
            capacities=[[32.0, 128.0, 8.0, 6.0], [32.0, 128.0, 8.0, 6.0]],
            windows=[(0, 1) for _ in range(n)],
            weights=[1.0] * n,
            K=2,
        )
    )
    opt, opt_p = brute_force_optimal(inst)
    assert opt is None or opt_p == float("inf")
    result = solve(inst)
    assert not result.feasible or len(set(result.assignment.values())) >= n


def test_zero_capacity_slot_blocks_overload():
    """Slot with zero GPU cannot host GPU-heavy task if that is the only slot."""
    inst = Instance.from_dict(
        dict(
            tasks=["T0", "T1"],
            conflicts=[],
            resources=[[1.0, 1.0, 4.0, 0.1], [1.0, 1.0, 0.0, 0.1]],
            capacities=[
                [32.0, 128.0, 0.0, 6.0],
                [32.0, 128.0, 8.0, 6.0],
            ],
            windows=[(0, 0), (1, 1)],
            weights=[1.0, 1.0],
            K=2,
        )
    )
    result = solve(inst)
    if result.feasible:
        assert result.assignment["T0"] == 2
    else:
        assert result.violation_reason


def test_tight_sla_windows():
    """Each task restricted to exactly one slot must land there."""
    inst = Instance.from_dict(
        dict(
            tasks=["T0", "T1", "T2"],
            conflicts=[[0, 1], [1, 2]],
            resources=[[1.0, 1.0, 0.0, 0.1] for _ in range(3)],
            capacities=[[32.0, 128.0, 8.0, 6.0] for _ in range(3)],
            windows=[(0, 0), (1, 1), (2, 2)],
            weights=[1.0, 1.0, 1.0],
            K=3,
        )
    )
    result = solve(inst)
    assert result.feasible
    assert result.assignment["T0"] == 1
    assert result.assignment["T1"] == 2
    assert result.assignment["T2"] == 3
    ok, _ = check_feasibility(
        inst, {i: result.assignment[inst.tasks[i]] for i in range(3)}
    )
    assert ok


def test_toy_instance_from_assignment_doc():
    path = ROOT / "instances" / "toy.json"
    inst = Instance.from_dict(json.loads(path.read_text(encoding="utf-8")))
    result = solve(inst, use_brute_compare=True)
    assert result.feasible, result.violation_reason
    if result.approximation_ratio is not None:
        assert result.approximation_ratio >= 1.0
