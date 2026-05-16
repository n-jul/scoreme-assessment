
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Instance:

    tasks: list[str]
    conflicts: list[tuple[int, int]]
    resources: list[list[float]]
    capacities: list[list[float]]
    windows: list[tuple[int, int]]
    weights: list[float]
    K: int

    @property
    def n(self) -> int:
        return len(self.tasks)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Instance:
        conflicts = [tuple(c) for c in data["conflicts"]]
        windows = [tuple(w) for w in data["windows"]]
        return cls(
            tasks=list(data["tasks"]),
            conflicts=conflicts,
            resources=[list(r) for r in data["resources"]],
            capacities=[list(c) for c in data["capacities"]],
            windows=windows,
            weights=[float(w) for w in data["weights"]],
            K=int(data["K"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return dict(
            tasks=self.tasks,
            conflicts=[list(c) for c in self.conflicts],
            resources=self.resources,
            capacities=self.capacities,
            windows=[list(w) for w in self.windows],
            weights=self.weights,
            K=self.K,
        )

    def conflict_neighbors(self) -> list[set[int]]:
        adj: list[set[int]] = [set() for _ in range(self.n)]
        for i, j in self.conflicts:
            adj[i].add(j)
            adj[j].add(i)
        return adj


@dataclass
class ScheduleResult:

    assignment: dict[str, int]
    penalty: float
    runtime_ms: int
    feasible: bool
    violation_reason: str = ""
    optimal_penalty: float | None = None
    approximation_ratio: float | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "assignment": self.assignment,
            "penalty": self.penalty,
            "runtime_ms": self.runtime_ms,
            "feasible": self.feasible,
            "violation_reason": self.violation_reason,
        }
        if self.optimal_penalty is not None:
            out["optimal_penalty"] = self.optimal_penalty
        if self.approximation_ratio is not None:
            out["approximation_ratio"] = self.approximation_ratio
        return out
