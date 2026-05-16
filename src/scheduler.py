
from __future__ import annotations

import itertools
import time
from typing import Callable

from src.models import Instance, ScheduleResult
from src.penalty import total_penalty
from src.validation import check_feasibility


def _slot_feasible(
    instance: Instance,
    task: int,
    slot: int,
    assignment: dict[int, int],
    usage: list[list[float]],
    adj: list[set[int]],
) -> bool:
    """Check F1/F2/F3 for placing task into slot (1-indexed)."""
    lo, hi = instance.windows[task]
    if slot < lo + 1 or slot > hi + 1:
        return False

    s_idx = slot - 1
    for neighbor in adj[task]:
        if neighbor in assignment and assignment[neighbor] == slot:
            return False

    d_dims = len(instance.resources[task])
    for d in range(d_dims):
        if usage[s_idx][d] + instance.resources[task][d] > instance.capacities[s_idx][d] + 1e-9:
            return False
    return True


def _apply_task(
    instance: Instance,
    task: int,
    slot: int,
    assignment: dict[int, int],
    usage: list[list[float]],
) -> None:
    assignment[task] = slot
    s_idx = slot - 1
    for d, req in enumerate(instance.resources[task]):
        usage[s_idx][d] += req


def _remove_task(
    instance: Instance,
    task: int,
    assignment: dict[int, int],
    usage: list[list[float]],
) -> None:
    slot = assignment.pop(task)
    s_idx = slot - 1
    for d, req in enumerate(instance.resources[task]):
        usage[s_idx][d] -= req


def _task_order(instance: Instance, adj: list[set[int]]) -> list[int]:
    """
    DSATUR-inspired ordering: high weight, high degree, tight SLA window first.
    Tighter windows and more conflicts are scheduled before easy tasks.
    """
    def key(i: int) -> tuple:
        lo, hi = instance.windows[i]
        width = hi - lo
        return (
            -instance.weights[i],
            -len(adj[i]),
            width,
            -sum(len(adj[j]) for j in adj[i]),
        )

    return sorted(range(instance.n), key=key)


def scfg_schedule(instance: Instance) -> tuple[dict[int, int] | None, str]:
    """
    Run SCFG: greedy placement + iterative local improvement.

    Returns (assignment or None, violation_reason).
    """
    n = instance.n
    K = instance.K
    adj = instance.conflict_neighbors()
    d_dims = len(instance.resources[0]) if n else 4
    usage = [[0.0] * d_dims for _ in range(K)]
    assignment: dict[int, int] = {}

    for task in _task_order(instance, adj):
        placed = False
        # Prefer earlier slots to reduce P_base, but scan all feasible in window
        lo, hi = instance.windows[task]
        candidates = range(lo + 1, hi + 2)
        for slot in sorted(candidates, key=lambda s: (s, total_penalty(instance, {**assignment, task: s}))):
            if _slot_feasible(instance, task, slot, assignment, usage, adj):
                _apply_task(instance, task, slot, assignment, usage)
                placed = True
                break
        if not placed:
            return None, (
                f"No feasible slot for task {instance.tasks[task]} "
                f"(window [{lo + 1},{hi + 1}], conflicts/ capacity block all slots)"
            )

    assignment = _local_search(instance, assignment)
    feasible, reason = check_feasibility(instance, assignment)
    if not feasible:
        return None, reason
    return assignment, ""


def _local_search(instance: Instance, assignment: dict[int, int], max_rounds: int = 50) -> dict[int, int]:
    """
    Hill-climb: try moving one task to another feasible slot if penalty decreases.
  Stops when no improving move exists or max_rounds exhausted.
    """
    adj = instance.conflict_neighbors()
    d_dims = len(instance.resources[0])
    current = dict(assignment)
    best_penalty = total_penalty(instance, current)

    for _ in range(max_rounds):
        improved = False
        for task in range(instance.n):
            old_slot = current[task]
            _remove_task(instance, task, current, _build_usage(instance, current))
            usage = _build_usage(instance, current)
            lo, hi = instance.windows[task]
            for slot in range(lo + 1, hi + 2):
                if slot == old_slot:
                    continue
                if not _slot_feasible(instance, task, slot, current, usage, adj):
                    continue
                trial = dict(current)
                _apply_task(instance, task, slot, trial, _build_usage(instance, trial))
                p = total_penalty(instance, trial)
                if p < best_penalty - 1e-9:
                    current = trial
                    best_penalty = p
                    improved = True
                    break
            if task in current:
                continue
            # restore if not moved
            usage = _build_usage(instance, current)
            _apply_task(instance, task, old_slot, current, usage)
        if not improved:
            break
    return assignment if not improved else current


def _build_usage(instance: Instance, assignment: dict[int, int]) -> list[list[float]]:
    d_dims = len(instance.resources[0])
    usage = [[0.0] * d_dims for _ in range(instance.K)]
    for i, slot in assignment.items():
        s_idx = slot - 1
        for d, req in enumerate(instance.resources[i]):
            usage[s_idx][d] += req
    return usage


def brute_force_optimal(instance: Instance, max_n: int = 12) -> tuple[dict[int, int] | None, float]:
    """
    Enumerate all assignments (K^n) for small n; return optimal feasible assignment.
    Used only for benchmark comparison on small instances.
    """
    if instance.n > max_n:
        return None, float("inf")

    adj = instance.conflict_neighbors()
    best: dict[int, int] | None = None
    best_p = float("inf")

    for slots in itertools.product(range(1, instance.K + 1), repeat=instance.n):
        assignment = {i: slots[i] for i in range(instance.n)}
        ok, _ = check_feasibility(instance, assignment)
        if not ok:
            continue
        p = total_penalty(instance, assignment)
        if p < best_p:
            best_p = p
            best = assignment

    return best, best_p


def solve(instance: Instance, use_brute_compare: bool = False) -> ScheduleResult:
    """Main entry: run SCFG and optionally compute brute-force optimal."""
    start = time.perf_counter()
    assignment, violation = scfg_schedule(instance)
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    if assignment is None:
        return ScheduleResult(
            assignment={},
            penalty=float("inf"),
            runtime_ms=elapsed_ms,
            feasible=False,
            violation_reason=violation,
        )

    penalty = total_penalty(instance, assignment)
    feasible, reason = check_feasibility(instance, assignment)
    out_assign = {instance.tasks[i]: assignment[i] for i in range(instance.n)}

    result = ScheduleResult(
        assignment=out_assign,
        penalty=penalty,
        runtime_ms=elapsed_ms,
        feasible=feasible,
        violation_reason=reason if not feasible else "",
    )

    if use_brute_compare and instance.n <= 12:
        opt, opt_p = brute_force_optimal(instance)
        if opt is not None and opt_p < float("inf"):
            result.optimal_penalty = opt_p
            result.approximation_ratio = penalty / opt_p if opt_p > 0 else 1.0

    return result
