
from __future__ import annotations

from src.models import Instance


def check_feasibility(
    instance: Instance, assignment: dict[int, int]
) -> tuple[bool, str]:
    """
    Verify F1 (conflicts), F2 (capacity), F3 (SLA windows).
    Returns (feasible, violation_reason).
    """
    if len(assignment) != instance.n:
        missing = set(range(instance.n)) - set(assignment.keys())
        return False, f"Unassigned tasks: {[instance.tasks[i] for i in missing]}"

    adj = instance.conflict_neighbors()

    # F1 — no conflicting tasks in same slot
    slot_tasks: dict[int, list[int]] = {}
    for i, slot in assignment.items():
        slot_tasks.setdefault(slot, []).append(i)

    for slot, members in slot_tasks.items():
        for a in range(len(members)):
            for b in range(a + 1, len(members)):
                i, j = members[a], members[b]
                if j in adj[i]:
                    return (
                        False,
                        f"F1: conflict {instance.tasks[i]} and {instance.tasks[j]} "
                        f"both in slot {slot}",
                    )

    # F3 — SLA windows (slots are 1-indexed externally: map to 0-index for windows)
    for i, slot in assignment.items():
        lo, hi = instance.windows[i]
        # Generator uses 0-indexed window bounds; assignment uses 1..K slots
        if slot < lo + 1 or slot > hi + 1:
            return (
                False,
                f"F3: task {instance.tasks[i]} in slot {slot}, "
                f"allowed [{lo + 1}, {hi + 1}]",
            )

    # F2 — capacity per slot
    d_dims = len(instance.resources[0])
    usage = [[0.0] * d_dims for _ in range(instance.K)]
    for i, slot in assignment.items():
        s_idx = slot - 1
        for d in range(d_dims):
            usage[s_idx][d] += instance.resources[i][d]

    for s in range(instance.K):
        for d in range(d_dims):
            if usage[s][d] > instance.capacities[s][d] + 1e-9:
                return (
                    False,
                    f"F2: slot {s + 1} dimension {d} usage {usage[s][d]:.2f} "
                    f"> capacity {instance.capacities[s][d]:.2f}",
                )

    return True, ""
