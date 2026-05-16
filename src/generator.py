"""Random instance generator (assignment Section 5 — do not modify logic)."""

import random
from typing import Any


def generate_instance(
    n: int,
    K: int,
    d: int = 4,
    conflict_density: float = 0.3,
    seed: int = 42,
) -> dict[str, Any]:
    """Generate a random MSME Credit Pipeline Scheduling instance."""
    random.seed(seed)
    tasks = [f"T{i}" for i in range(n)]
    conflicts = [
        (i, j)
        for i in range(n)
        for j in range(i + 1, n)
        if random.random() < conflict_density
    ]
    cap = [32.0, 128.0, 8.0, 6.0]  # CPU, RAM, GPU, Network
    resources = [
        [random.uniform(1, cap[dim] // (n // K + 1)) for dim in range(4)]
        for _ in range(n)
    ]
    capacities = [cap[:] for _ in range(K)]
    windows = []
    for _ in range(n):
        lo = random.randint(0, K - 2)
        hi = random.randint(lo + 1, K - 1)
        windows.append((lo, hi))
    weights = [random.uniform(1, 10) for _ in range(n)]
    return dict(
        tasks=tasks,
        conflicts=conflicts,
        resources=resources,
        capacities=capacities,
        windows=windows,
        weights=weights,
        K=K,
    )
