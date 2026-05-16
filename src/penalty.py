"""Penalty function P(sigma) = P_base + load-imbalance + SLA-risk terms."""

from __future__ import annotations

from src.models import Instance

# Tunable weights for extension terms (Task 2 design).
LAMBDA_IMBALANCE = 0.5
LAMBDA_SLA_RISK = 0.3


def p_base(instance: Instance, assignment: dict[int, int]) -> float:
    """Weighted slot index: sum_i w(t_i) * sigma(t_i). Slots are 1-indexed in output."""
    total = 0.0
    for i, slot in assignment.items():
        total += instance.weights[i] * slot
    return total


def load_imbalance_penalty(instance: Instance, assignment: dict[int, int]) -> float:
    """
    Penalize uneven utilization across slots (ScoreMe cluster load-balancing concern).

    For each resource dimension d, compute per-slot utilization u_{s,d} in [0,1],
    then sum squared deviation from the mean utilization across slots.
    """
    K = instance.K
    d_dims = len(instance.resources[0]) if instance.n else 4
    util = [[0.0] * d_dims for _ in range(K)]

    for i, slot in assignment.items():
        s_idx = slot - 1
        for d in range(d_dims):
            cap = instance.capacities[s_idx][d]
            if cap > 0:
                util[s_idx][d] += instance.resources[i][d] / cap

    penalty = 0.0
    for d in range(d_dims):
        vals = [util[s][d] for s in range(K)]
        mean_u = sum(vals) / K if K else 0.0
        penalty += sum((u - mean_u) ** 2 for u in vals)
    return penalty


def sla_risk_penalty(instance: Instance, assignment: dict[int, int]) -> float:
    """
    Penalize tasks placed near the upper SLA boundary (bureau pull deadline risk).

    risk_i = w_i * (sigma(t_i) - l_i) / (u_i - l_i)  when window width > 0.
    """
    total = 0.0
    for i, slot in assignment.items():
        lo, hi = instance.windows[i]
        width = hi - lo
        if width <= 0:
            if slot > hi:
                total += instance.weights[i] * 10.0
            continue
        slack_used = (slot - lo) / width
        total += instance.weights[i] * slack_used
    return total


def total_penalty(instance: Instance, assignment: dict[int, int]) -> float:
    """Full penalty P(sigma) used by the scheduler and benchmarks."""
    return (
        p_base(instance, assignment)
        + LAMBDA_IMBALANCE * load_imbalance_penalty(instance, assignment)
        + LAMBDA_SLA_RISK * sla_risk_penalty(instance, assignment)
    )
