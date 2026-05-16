"""
SLA-Weighted Conflict-First Greedy with Multi-Restart and Backtrack (SCFG-MR).

Polynomial-time heuristic for MSME credit pipeline scheduling.
"""

from __future__ import annotations

import itertools
import random
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
    """True if placing task in slot respects F1 (conflict), F2 (capacity), F3 (SLA)."""
    lo, hi = instance.windows[task]
    if slot < lo + 1 or slot > hi + 1:
        return False

    s_idx = slot - 1
    for neighbor in adj[task]:
        if neighbor in assignment and assignment[neighbor] == slot:
            return False

    for d, req in enumerate(instance.resources[task]):
        if usage[s_idx][d] + req > instance.capacities[s_idx][d] + 1e-9:
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


def _build_usage(instance: Instance, assignment: dict[int, int]) -> list[list[float]]:
    d_dims = len(instance.resources[0]) if instance.n else 4
    usage = [[0.0] * d_dims for _ in range(instance.K)]
    for i, slot in assignment.items():
        s_idx = slot - 1
        for d, req in enumerate(instance.resources[i]):
            usage[s_idx][d] += req
    return usage


def _order_default(instance: Instance, adj: list[set[int]]) -> list[int]:
    """High lender weight, high conflict degree, tight SLA window first."""

    def key(i: int) -> tuple:
        lo, hi = instance.windows[i]
        return (-instance.weights[i], -len(adj[i]), hi - lo, -sum(len(adj[j]) for j in adj[i]))

    return sorted(range(instance.n), key=key)


def _order_degree_first(instance: Instance, adj: list[set[int]]) -> list[int]:
    return sorted(range(instance.n), key=lambda i: (-len(adj[i]), instance.windows[i][1] - instance.windows[i][0]))


def _order_window_tight(instance: Instance, adj: list[set[int]]) -> list[int]:
    return sorted(range(instance.n), key=lambda i: (instance.windows[i][1] - instance.windows[i][0], -instance.weights[i]))


def _ordering_variants(instance: Instance, adj: list[set[int]]) -> list[list[int]]:
    """Multiple task orderings for multi-restart greedy (reduces false infeasibility)."""
    base = _order_default(instance, adj)
    variants = [
        base,
        list(reversed(base)),
        _order_degree_first(instance, adj),
        _order_window_tight(instance, adj),
        sorted(range(instance.n), key=lambda i: instance.weights[i]),
    ]
    rng = random.Random(instance.n * 997 + instance.K)
    shuffled = list(range(instance.n))
    rng.shuffle(shuffled)
    variants.append(shuffled)
    return variants


def _greedy_build(instance: Instance, order: list[int]) -> tuple[dict[int, int] | None, str]:
    """Place tasks in given order; prefer lowest slot index among feasible candidates."""
    adj = instance.conflict_neighbors()
    d_dims = len(instance.resources[0]) if instance.n else 4
    usage = [[0.0] * d_dims for _ in range(instance.K)]
    assignment: dict[int, int] = {}

    for task in order:
        lo, hi = instance.windows[task]
        placed = False
        for slot in range(lo + 1, hi + 2):
            if _slot_feasible(instance, task, slot, assignment, usage, adj):
                _apply_task(instance, task, slot, assignment, usage)
                placed = True
                break
        if not placed:
            return None, (
                f"No feasible slot for task {instance.tasks[task]} "
                f"(window [{lo + 1},{hi + 1}])"
            )
    return assignment, ""


def _backtrack_build(
    instance: Instance,
    order: list[int],
    idx: int,
    assignment: dict[int, int],
    usage: list[list[float]],
    adj: list[set[int]],
    best: list,
) -> bool:
    """Depth-first backtrack on task order; keeps best feasible assignment by penalty."""
    if idx == len(order):
        feasible, _ = check_feasibility(instance, assignment)
        if not feasible:
            return False
        p = total_penalty(instance, assignment)
        if p < best[0]:
            best[0] = p
            best[1] = dict(assignment)
        return True

    task = order[idx]
    lo, hi = instance.windows[task]
    found = False
    for slot in range(lo + 1, hi + 2):
        if not _slot_feasible(instance, task, slot, assignment, usage, adj):
            continue
        _apply_task(instance, task, slot, assignment, usage)
        if _backtrack_build(instance, order, idx + 1, assignment, usage, adj, best):
            found = True
        _remove_task(instance, task, assignment, usage)
    return found


def _local_search(instance: Instance, assignment: dict[int, int], max_rounds: int = 50) -> dict[int, int]:
    """Hill-climb: relocate tasks to lower-penalty feasible slots."""
    adj = instance.conflict_neighbors()
    current = dict(assignment)
    best_penalty = total_penalty(instance, current)

    for _ in range(max_rounds):
        improved = False
        for task in range(instance.n):
            old_slot = current[task]
            usage = _build_usage(instance, current)
            _remove_task(instance, task, current, usage)
            lo, hi = instance.windows[task]
            for slot in range(lo + 1, hi + 2):
                if slot == old_slot:
                    continue
                usage = _build_usage(instance, current)
                if not _slot_feasible(instance, task, slot, current, usage, adj):
                    continue
                trial = dict(current)
                trial_usage = _build_usage(instance, trial)
                _apply_task(instance, task, slot, trial, trial_usage)
                p = total_penalty(instance, trial)
                if p < best_penalty - 1e-9:
                    current = trial
                    best_penalty = p
                    improved = True
                    break
            if task not in current:
                usage = _build_usage(instance, current)
                _apply_task(instance, task, old_slot, current, usage)
        if not improved:
            break
    return current


def scfg_schedule(instance: Instance) -> tuple[dict[int, int] | None, str]:
    """
    SCFG-MR: multi-restart greedy + backtrack (small n) + local search.

    Tries several task orderings; for n <= 18 also runs backtracking to avoid
    false infeasibility from greedy ordering. Returns best feasible assignment.
    """
    adj = instance.conflict_neighbors()
    best_assign: dict[int, int] | None = None
    best_penalty = float("inf")
    last_reason = "No feasible assignment found"

    for order in _ordering_variants(instance, adj):
        assignment, reason = _greedy_build(instance, order)
        if assignment is None:
            last_reason = reason
            continue
        assignment = _local_search(instance, assignment)
        p = total_penalty(instance, assignment)
        ok, _ = check_feasibility(instance, assignment)
        if ok and p < best_penalty:
            best_penalty = p
            best_assign = assignment

    if best_assign is not None:
        return best_assign, ""

    if instance.n <= 18:
        order = _order_default(instance, adj)
        d_dims = len(instance.resources[0])
        usage = [[0.0] * d_dims for _ in range(instance.K)]
        best = [float("inf"), None]
        _backtrack_build(instance, order, 0, {}, usage, adj, best)
        if best[1] is not None:
            improved = _local_search(instance, best[1])
            return improved, ""

    # Large n: extra random orderings (polynomial restarts, no full backtrack)
    for seed in range(24):
        rng = random.Random(instance.n * 1009 + instance.K * 17 + seed)
        order = list(range(instance.n))
        rng.shuffle(order)
        assignment, reason = _greedy_build(instance, order)
        if assignment is None:
            last_reason = reason
            continue
        assignment = _local_search(instance, assignment)
        p = total_penalty(instance, assignment)
        ok, _ = check_feasibility(instance, assignment)
        if ok and p < best_penalty:
            best_penalty = p
            best_assign = assignment

    if best_assign is not None:
        return best_assign, ""

    return None, last_reason


def brute_force_optimal(instance: Instance, max_n: int = 12) -> tuple[dict[int, int] | None, float]:
    """Enumerate K^n assignments; return minimum-penalty feasible solution."""
    if instance.n > max_n:
        return None, float("inf")

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
    """Run SCFG-MR and package results for JSON output."""
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
