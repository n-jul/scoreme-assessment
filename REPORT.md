# ScoreMe Advanced Systems Design — Assignment Report

**Candidate submission:** MSME Credit Pipeline Scheduling  
**Algorithm name:** SCFG-MR (SLA-Weighted Conflict-First Greedy with Multi-Restart)  
**Implementation:** Python 3.10+ (`src/`, `run.py`)  
**Repository layout:** See `README.md`

---

## Task 1: NP-Hardness Proof [20 pts]

### Theorem

The MSME Credit Pipeline Scheduling problem (feasibility version: does there exist σ satisfying F1–F3?) is **NP-complete**.

### Reduction source

We reduce from **Graph K-Coloring**, which is NP-complete for K ≥ 3.

**Input to K-Coloring:** Graph G = (V, E), integer K.  
**Question:** Does there exist a coloring c : V → {1,…,K} such that c(u) ≠ c(v) for all (u,v) ∈ E?

### Construction (polynomial time)

Given (G, K) with |V| = n, build scheduling instance I(G, K):

| Component | Construction |
|-----------|--------------|
| Tasks | One task t_v per vertex v ∈ V |
| Slots | K slots {1,…,K} |
| Conflicts (F1) | Edge (u,v) ∈ E ⟹ add conflict (t_u, t_v) |
| Resources (F2) | Each task needs 1 unit of CPU; slot s has capacity K (total CPU = K per slot). No RAM/GPU/Net demand (set to 0). |
| SLA windows (F3) | Every task: window [1, K] (may use any slot) |
| Weights | w(t_v) = 1 for all v |

**Size:** O(n + |E|) — polynomial in input size.

### Forward direction (coloring ⇒ assignment)

If c is a proper K-coloring, define σ(t_v) = c(v).

- **F1:** For conflicting pair (t_u, t_v), c(u) ≠ c(v) ⇒ different slots.
- **F2:** At most n tasks could be placed in one slot, each using 1 CPU; capacity K ≥ 1 per slot; with exactly one task per vertex and coloring assigning each vertex one color, at most |c⁻¹(s)| vertices share color s. In worst case a color class has size ≤ n, but we strengthen construction: use **unit capacity per slot C(s) = 1** CPU only. Then each slot holds at most one task — valid coloring assigns at most one vertex per color, satisfying capacity.
- **F3:** All slots in [1,K] by construction.

### Reverse direction (assignment ⇒ coloring)

If σ is feasible, define c(v) = σ(t_v).

- **F1** ensures adjacent vertices have different colors.
- **F2** with unit slot capacity forces at most one task per slot, hence σ is injective on V — still a valid K-coloring.
- **F3** is vacuous (full window).

### Encoding all three families simultaneously

| Constraint family | Role in reduction |
|-------------------|-------------------|
| Conflicts | Directly encodes edges (graph coloring) |
| Capacity | Forces injective placement (strengthens coloring) |
| SLA windows | Full window — present but non-binding; can tighten to show **temporal** constraints add hardness via separate clause-gadget reduction (below) |

### Strengthening: SLA + resources (sketch)

To bind **F3** non-trivially, attach clause gadgets from 3-SAT: each task representing a literal may only run in slots corresponding to “true” or “false” phases; link with unit-capacity and zero-GPU resources so satisfying assignment ↔ satisfying formula. Combined with conflict edges between inconsistent literals, the **compound** problem remains NP-hard because it generalizes K-coloring (set all windows to [1,K] and recover coloring subproblem).

### Conclusion

Feasibility is NP-hard. The optimization version (minimize P) is NP-hard as a search extension (decision: P ≤ B reduces to feasibility with penalty cap).

---

## Task 2: Penalty Function Design [15 pts]

### Base (given)

\[
P_{\text{base}}(\sigma) = \sum_{i=1}^{n} w(t_i) \cdot \sigma(t_i)
\]

Models **priority-weighted delay**: high-importance lender tasks penalized more for late slots.

### Extension 1: Load imbalance (operational)

\[
P_{\text{imb}}(\sigma) = \sum_{d \in \{\text{CPU,RAM,GPU,Net}\}} \sum_{s=1}^{K} \left( u_{s,d} - \bar{u}_d \right)^2
\]

where \(u_{s,d} = \frac{\sum_{i:\sigma(t_i)=s} r_i^{(d)}}{C_s^{(d)}}\) and \(\bar{u}_d = \frac{1}{K}\sum_s u_{s,d}\).

**Motivation (ScoreMe):** NiFi/Kubernetes clusters with one executor at 95% CPU while others idle cause tail latency and autoscaling thrash. Minimizing variance encourages even spread.

**Polynomial time:** O(n·K·d) per evaluation.

**Monotonicity:** Higher imbalance increases P; minimizing P pushes toward fair utilization.

### Extension 2: SLA boundary risk (bureau pulls)

\[
P_{\text{sla}}(\sigma) = \sum_{i=1}^{n} w(t_i) \cdot \frac{\sigma(t_i) - \ell_i}{u_i - \ell_i}
\]

(window width \(u_i - \ell_i > 0\); slots mapped from 0-indexed \([\ell_i, u_i]\) in generator).

**Motivation:** Bureau API tasks near upper window bound risk missing lender SLA if upstream delays occur.

### Total penalty

\[
P(\sigma) = P_{\text{base}} + \lambda_1 P_{\text{imb}} + \lambda_2 P_{\text{sla}}, \quad \lambda_1 = 0.5,\; \lambda_2 = 0.3
\]

Implemented in `src/penalty.py`.

---

## Task 3: Algorithm Design — SCFG-MR [40 pts]

### Rationale

The instance combines **graph coloring** (conflicts), **multi-dimensional bin packing** (resources), and **interval scheduling** (SLA). Pure coloring ignores capacity; pure packing ignores conflicts. SCFG-MR:

1. Orders tasks by **hardness** (weight, degree, tight window).
2. **Greedy** assigns first feasible slot in SLA window.
3. **Multi-restart** with alternate orderings avoids false infeasibility.
4. **Backtrack** (n ≤ 18) completes search when greedy fails.
5. **Local search** improves penalty.

### Pseudocode

```
ALGORITHM SCFG-MR(Instance I)
  adj ← conflict_neighbors(I)
  best ← (∞, ∅)

  FOR order IN OrderingVariants(I, adj):
    σ ← GREEDY-BUILD(I, order)
    IF σ = FAIL THEN CONTINUE
    σ ← LOCAL-SEARCH(I, σ)
    IF feasible(σ) AND P(σ) < best.penalty THEN best ← (P(σ), σ)

  IF best = ∅ AND I.n ≤ 18 THEN
    σ ← BACKTRACK(I, order_default, depth=0)
    IF σ ≠ FAIL THEN best ← (P(LOCAL-SEARCH(I, σ)), σ)

  IF best = ∅ AND I.n > 18 THEN
    FOR seed IN 1..24:
      order ← RANDOM-PERM(I.n, seed)
      σ ← GREEDY-BUILD(I, order); ... same as above

  IF best = ∅ THEN RETURN INFEASIBLE
  ELSE RETURN best.σ

GREEDY-BUILD(I, order):
  usage ← zero matrix K × d
  FOR task IN order:
    FOR slot FROM ℓ_task+1 TO u_task+1:
      IF Feasible(task, slot, usage, conflicts) THEN
        Assign; BREAK
    ELSE RETURN FAIL
  RETURN σ

LOCAL-SEARCH(I, σ):
  REPEAT up to 50 rounds:
    improved ← false
    FOR each task t:
      FOR each alternate slot s in window:
        IF move t→s feasible AND P decreases THEN σ ← move; improved ← true
    UNTIL not improved
  RETURN σ
```

**Line-level decisions:**

- **Order by (-weight, -degree, window width):** High-priority, highly constrained tasks first (DSATUR principle).
- **Lowest slot first in greedy:** Reduces P_base early-slot bias.
- **Multi-restart:** Greedy is order-sensitive; restarts are polynomial.
- **Backtrack only for n ≤ 18:** Exponential depth manageable; avoids timeout on n=200.

### Rejected alternatives

| Alternative | Reason rejected |
|-------------|-----------------|
| **Pure simulated annealing** | Slow to find *any* feasible σ on tight capacity; needs good initializer (we use greedy as initializer instead). |
| **ILP / OR-Tools** | Forbidden by assignment; also hides design intent for viva. |
| **Single-pass greedy only** | Empirically failed 7/9 benchmarks (false infeasibility); multi-restart fixed n=10 case. |

---

## Task 4: Approximation Bounds [30 pts]

### 4.1 Feasibility guarantee [10 pts]

**Claim:** If SCFG-MR returns σ with `feasible=true`, then σ satisfies F1–F3.

**Proof:** `check_feasibility()` in `validation.py` explicitly verifies F1, F2, F3 before output. Local search only applies feasible moves (`_slot_feasible`). Backtrack only commits feasible partial assignments. ∎

**False infeasibility:** If algorithm returns `feasible=false`, a feasible σ may still exist (greedy incomplete). Backtrack for n ≤ 18 reduces false negatives.

### 4.2 Approximation ratio [10 pts]

For **P_base only** and greedy that always places task i in **minimum** feasible slot within its window:

\[
P_{\text{base}}(\sigma_{\text{greedy}}) \leq P_{\text{base}}(\sigma^*)
\]

when each task’s slot is minimized independently and weights are positive — actually false with conflicts. **Weaker bound:**

Let σ* be optimal. Greedy-with-backtrack explores a subset S of feasible assignments. If σ* ∈ S (e.g. n ≤ 18 complete backtrack finds optimum in finite set only if full enumeration — backtrack finds *some* feasible, not all).

**Empirical ratio** (small n, brute force): For n ∈ {8,12}, ratio = 1.0; for n=10, seed 2, ratio ≈ 1.22 (see Task 6).

**Analytical loose bound** for extended P: Let Δ be maximum slot index. Then P_base ≤ W_max · n · Δ where W_max = max w_i. Greedy earliest-slot ensures σ_greedy(t) ≤ u_t+1, so

\[
P_{\text{base}}(\sigma_g) \leq W_{\max} \sum_i (u_i + 1) \leq W_{\max} \cdot n \cdot K
\]

Optimal ≥ W_min · n (if all in slot 1 feasible). Ratio ≤ (W_max/W_min)·K — instance-dependent, not constant α.

**Honest assessment:** Without PTAS for this compound problem, we report **empirical** α on small instances rather than a universal constant.

### 4.3 Tight adversarial example [10 pts]

**Instance:** 2 tasks, K=2, conflicts between them, each needs 60% CPU, capacity 100% per slot, windows [1,2], weights equal.

- Optimal: slots 1 and 2, P_base = 1+2 = 3.
- Greedy (wrong order): assign both to slot 1 — infeasible; correct order gives optimal.

**Tightness for our n=10 benchmark:** seed 2 achieves ratio ≈ 1.22; brute optimal = 80.70, SCFG-MR = 98.44 — greedy locked early tasks into suboptimal slots; local search did not escape. Shows bound is not 1.

---

## Task 5: Implementation [25 pts]

| Requirement | Status |
|-------------|--------|
| Python 3.10+ | ✅ |
| JSON in/out | ✅ `io_handler.py`, `run.py` |
| Output keys | ✅ assignment, penalty, runtime_ms, feasible, violation_reason |
| No forbidden libs | ✅ |
| Original logic | ✅ SCFG-MR in `scheduler.py` |
| Unit tests | ✅ `tests/test_scheduler.py` (5 cases) |
| Docstrings | ✅ Non-trivial functions documented |

**Run:**

```bash
python run.py --input instances/toy.json
python run.py --n 8 --K 3 --density 0.3 --seed 1 --brute
```

---

## Task 6: Empirical Analysis [20 pts]

### Benchmark table

| n | K | density | seed | Penalty | Time (ms) | Feasible | Approx ratio |
|---|---|---------|------|---------|-----------|----------|--------------|
| 8 | 3 | 0.3 | 1 | 72.59 | 0 | Yes | 1.000 |
| 10 | 4 | 0.4 | 2 | 98.44 | 0 | Yes | 1.220 |
| 12 | 4 | 0.5 | 3 | 138.18 | 1 | Yes | 1.000 |
| 50 | 8 | 0.25 | 10 | — | 0 | No | — |
| 100 | 10 | 0.30 | 11 | — | 2 | No | — |
| 150 | 12 | 0.35 | 12 | — | 4 | No | — |
| 200 | 15 | 0.40 | 20 | — | 10 | No | — |
| 200 | 5 | 0.60 | 21 | — | 13 | No | — |
| 200 | 20 | 0.10 | 22 | — | 3 | No | — |

*Regenerate:* `python run.py --benchmark` or `python scripts/make_charts.py`

### Charts

- `output/chart_penalty_vs_n.png` — penalty by instance (green/red = feasible/infeasible)
- `output/chart_runtime_vs_n.png` — runtime scaling

### Anomalies explained

1. **n=10, ratio 1.22:** Greedy order placed high-conflict tasks early in suboptimal slots; local search stuck in local minimum. Optimal exists (brute force verified).

2. **Large n infeasible:** Random generator produces tight resource + conflict + window constraints. SCFG-MR reports constructive failure (first task with no slot). May be true infeasibility or beyond polynomial heuristic — not verified by exact solver at n=200.

3. **n=8,12 ratio 1.0:** Backtrack / multi-restart found optimal on these seeds.

---

## Task 7: Design Journal [20 pts]

### Hardest design decision

Choosing **when to stop escalating** from greedy → multi-restart → backtrack → random restarts. Full backtrack at n=200 is exponential; greedy-only failed benchmarks. I kept backtrack cap at n ≤ 18 and 24 random permutations for larger n — trading completeness for runtime (milliseconds on large n).

**Rejected:** Always backtrack (too slow); never backtrack (false infeasibility on n=10).

### Empirical failure

**Instance:** n=10, K=4, density=0.4, seed=2 — initially reported infeasible with single greedy; after multi-restart, feasible but ratio 1.22. **Failure mode:** order sensitivity, not constraint unsatisfiability.

**With one week:** Add tabu search on top of local search; try LP-relaxation rounding for capacity (not full ILP solver) to guide slot choice.

### ScoreMe production mapping

**OCR GPU cluster + Kafka partitions:** Tasks map to NiFi processors; slots map to batch windows; conflicts = GPU exclusivity or same partition consumers; capacity = cluster quotas; SLA = bureau submission deadlines. SCFG-MR would run as a **pre-flight scheduler** before each batch window, outputting processor group assignments.

### What surprised me

Compound constraints are **not** separable — fixing coloring then packing can violate capacity. Multi-restart greedy was necessary for a problem I first treated as “just graph coloring.”

---

## Task 8: Viva Voce [30 pts]

**Candidate preparation:** Study pseudocode above, trace `instances/toy.json` by hand, read `scheduler.py` line-by-line. Be ready to explain `_slot_feasible`, multi-restart loop, and penalty terms.

**Perturbation answers (preview):**

- **5th resource dimension:** Add column to `resources` and `capacities`; F2 loop already iterates `d_dims`.
- **Different slot capacities:** Already supported — `capacities[s]` per slot in `Instance`.

---

## References

- Assignment document: `Fullstack Assignment.docx` / `assignment.txt`
- Code: `src/scheduler.py`, `src/penalty.py`, `src/validation.py`
- AI Usage: `AI_USAGE_LOG.md`
