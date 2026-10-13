# Recentred market access (Borusyak–Hull 2023): design and implementation plan

*October 2026. Proposed replacement for the "exclude the J nearest cities" identification in
`paper_draft05032026` §2.2, and for the least-cost-path IV idea in `research_agenda.md`
(lines 195–199). It combines two independent reviews of the design.*

---

## 0. Summary

**Pursue this, conditional on an archival audit that finds a defensible assignment mechanism
for road projects.**

The design:
- Some road projects were planned by the mid-1970s. Of these, some were operational by 1987
  and some were delayed or never built.
- Suppose that, within historically justified strata, *which* projects were operational is
  as-good-as-random. Then recomputing township MA growth under every feasible assignment
  gives each township's **expected** MA growth `μ_i`.
- The deviation `z_i = q_i − μ_i` is a valid instrument for observed MA growth.
- `μ_i` absorbs the centrality bias that the J-exclusion does not.
- Inference is by randomisation over the same assignments.

Recentring fixes identification, not measurement: it does not make travel times more
accurate. If no defensible assignment mechanism emerges, report μ-controlled estimates as a
sensitivity check, not as a new causal claim.

---

## 1. Problems with the current design

1. **Nonrandom exposure.** Any network improvement raises MA most for townships between
   large cities. ΔlogMA therefore loads on centrality, and centrality plausibly predicts
   1970–90 outcomes directly. Fixing 1970 populations and excluding the J nearest cities do
   not remove this.
2. **Local roads reach every destination.** A township's own paving also changes its travel
   time to distant cities. The J-exclusion therefore does not isolate MA from endogenous
   local road building.
3. **Equation (3) is asymmetric as typeset.**
   - The 1987 term sums over `rank(i,c) ≥ J`, but the 1974 term sums over all `c ∈ C`.
   - Read literally, `Δlog MA^J` = [change over far cities] + ln(far cities' share of 1974
     MA). The second term is pure baseline geography.
   - `≥ J` also keeps the J-th nearest city.
   - Fix this before replicating: use the same destination set in both terms, with ranks
     frozen at 1974 travel times.
4. **Inference.** The regressor is spatially smooth, and townships far apart share corridor
   shocks. County clustering does not capture that dependence.

---

## 2. Design

### 2.1 Objects

- **Assignment units `k = 1…K`.** These are road projects or construction packages, not GIS
  segments. Each unit has:
  - a planned alignment `A_k` (an edge set);
  - a planning stratum `s(k)`;
  - prerequisites (dependencies);
  - an observed status `D_k = 1` if operational by end-1987, with opening year `O_k`.
- **Fixed information `W`:**
  - the 1974/75 network `N_0`, trunk and local;
  - the alignments `{A_k}`, strata and dependencies;
  - 1970 city populations and geography;
  - park sites as designated at baseline.
- **Road-driven exposure** (the instrument's building block):

  ```
  q_i(D) = ln Σ_c P_c,1970 · T_ic(N_0 ∪ ⋃_{k: D_k=1} A_k)^(−θ)  −  ln Σ_c P_c,1970 · T_ic(N_0)^(−θ)
  ```

  Local (non-candidate) roads stay at their 1974/75 state in both terms (§2.3).
- **Expected exposure** `μ_i = E[q_i(D) | W]`, taken over the assignment model.
  **Recentred exposure** `z_i = q_i(D^obs) − μ_i`. Average the log changes; do not take the
  log of average MA.
- **Treatment `x_i`.** Observed Δlog MA, 1974→1987, from the corrected equation (3): all road
  changes, `P_1970`, and the same destination set in both years.

### 2.2 Assignment model

| Design | Use | What varies across draws | Identifying assumption |
|---|---|---|---|
| **Operational by cutoff** (primary) | long difference 1974→87 | which planned units are operational by 1987, with the number (or km) per stratum fixed | within strata, built and delayed units are exchangeable given planning information |
| **Opening timing** (secondary) | annual panel | opening sequence among units, within strata | within strata, opening order is exchangeable |
| Alternative alignments | not pursued | route between fixed endpoints | needs a distribution over routes; least-cost paths do not supply one |

- **The two designs need different data.** Permuting the timing of units that all open by
  1987 produces *zero* variation in 1987 exposure. So the long difference needs delayed or
  unbuilt units in the candidate set, and the timing design needs the annual panel.
- **Feasibility constraints.** Draws must respect dependencies: a spur cannot open before its
  trunk, and a corridor that opened jointly is one unit. They must also respect interchange
  access.
- **Strata** (planning wave, road class, engineering difficulty, predetermined priority)
  need historical justification, not just balance.
- **Project-level balance table.** Compare built and delayed units at planning time: planned
  cost per km, terrain, corridor population, region. This is the most direct evidence on the
  assumption. With small K it is descriptive, but it must be shown.
- **Unbuilt units' alignments** come from plan maps. Use least-cost paths only as a flagged
  fallback, with a robustness check that drops those units.

### 2.3 Why local roads are held at baseline, not 1987

Feeder roads were plausibly paved *in response to* trunk openings, for example to reach new
interchanges. Local paving in 1987 would then be post-treatment, and conditioning on it
breaks the independence of `D` and `W`.

Holding local roads at 1974/75 in `q` keeps `W` predetermined. Local paving still enters the
treatment `x`, so it is instrumented rather than assumed exogenous.

For the same reason, the 30 km paved-density control must be a baseline level. Check which
year the draft uses.

### 2.4 Estimators

Primary (2SLS):

```
ΔY_i = β x_i + ρ μ_i + X_i0′γ + u_i,      x_i instrumented by z_i
```

- **Keep `μ_i` as a control.** Do not substitute `q − μ` as an OLS regressor and drop `μ`:
  it is not the same estimator in finite samples.
- **Reduced form / "treatment = q" variant:** OLS of `ΔY` on `q_i`, `μ_i` and `X_i0`.
- **Controls:** `X_i0` must be `W`-measurable, i.e. baseline.
- **Cost function:** report results for θ ∈ {1, 3} (the draft's value and the model's σ − 1)
  and for an exponential-in-time cost. Recentring is valid for any formula, so θ affects
  power and interpretation, not validity.

### 2.5 Inference

- **Primary: randomisation Anderson–Rubin confidence set.**
  - For each `β_0`, compute `e_0 = M_W(ΔY − β_0 x)`, where `M_W` residualises on
    `[1, μ, X_0]`. Under `H_0` and exclusion, `e_0` does not depend on `D`.
  - For each feasible assignment, compute `T(D) = Σ_i z_i(D) e_0,i`.
  - Compute `p(β_0) = Pr_D(|T(D)| ≥ |T(D^obs)|)`. The CI is `{β_0 : p(β_0) ≥ α}`.
  - The set is exact under the assignment model, robust to weak instruments, and robust to
    arbitrary spatial correlation in `u`.
- **Enumerate exactly when feasible.**
  - With K on the order of 10 the assignment set is small. Three strata of sizes 4/4/3 with
    2/2/1 opened give 6 × 6 × 3 = 108 assignments, so the smallest attainable p-value is
    ≈ 0.009.
  - Sampling 2,000 draws from a set of 108 adds nothing. Sample (B ≥ 2,000, with Monte Carlo
    error reported) only when the set is large.
  - More draws improve numerical approximation; they do not add independent historical
    shocks. **Power is set by K.**
- **Secondary:** county-clustered and Conley SEs, for comparison only.

### 2.6 What recentring does not fix

- **Direct effects of trunk roads.** Interchange access, construction employment and land
  take violate exclusion when the treatment is generic MA. Two robustness checks:
  - a donut that drops townships within k km of any *candidate* alignment. This is
    symmetric in `D`, so the design survives, and identification then comes purely from
    network spillovers;
  - a recentred direct-access term (e.g. an operational interchange within k km) as a second
    endogenous variable.
- **Park placement.** Conditioning on baseline park designations makes the road design valid
  given parks. It does not make parks exogenous or identify roads × parks complementarity
  (§4, E3).
- **Travel-time measurement error** from speed assumptions and network digitisation.

---

## 3. Diagnostics and the results table

One table per headline outcome (tillers, value added, non-farm population, services):

1. Draft specification, with equation (3) corrected.
2. The same, plus a `μ` control (OLS).
3. Recentred 2SLS (§2.4).
4. Recentred 2SLS under 2–3 alternative assignment schemes: different strata definitions;
   with and without never-built units; J-exclusion with frozen ranks.

Report alongside it:
- **Decomposition:** the share of `Var(x)` explained by `μ`, and `Var(z)/Var(q)`.
- **Maps:** `x`, `μ` and `z`, plus a map of townships with `Var_D(q_i) ≈ 0`, which contribute
  nothing.
- **First stage:** effective F and the randomisation distribution of the first-stage
  coefficient.
- **Balance:**
  - 1970 levels and 1966–70 trends (annual panel) on `z`, given `μ` and `X`. These should be
    null.
  - The same variables on `μ`. This shows the bias.
- **Sensitivity:** leave-one-stratum-out and leave-one-corridor-out estimates.

---

## 4. Extensions (annual panel)

- **E1. Timing design.**
  - Exposure `q_it` from opening years, and `μ_it` from simulated opening sequences permuted
    within strata.
  - Estimate an event study / distributed lags with township and year FE, plus `μ_it`.
  - Fixed effects do not replace recentring.
- **E2. Goods vs labour access.**
  - `q^G` uses agricultural-buyer weights: 1970 urban population or food demand.
  - `q^L` uses non-farm-job weights: 1970 manufacturing employment, or planned park
    capacity at designation.
  - Recentre both with the same draws.
  - Expect collinearity: the 28 cities are both buyers and employers, and the shocks are the
    same K units. Proceed only if the conditional first-stage F (Sanderson–Windmeijer) is
    adequate for both.
- **E3. Industrial-park interaction** (draft eq. 4).
  - Endogenous: `x` and `x·H`. Instruments: `z` and `z·H`. Controls: `μ`, `μ·H` and `H`.
  - `H` is baseline park proximity, measured to designated sites.
  - `z·H` is mean-zero given `W` automatically.
  - If rejected park sites turn up (`research_agenda.md:219-225`), randomise parks and roads
    jointly and recentre `H` too.
- **E4. Industrial-pull shift-share** (`research_agenda.md:191-194`). The same draws recentre
  it.

---

## 5. Work plan and gates

| Phase | Data needed | Output | Gate to proceed |
|---|---|---|---|
| **A. Fix and scaffold** (now) | none | equation (3) correction sent to the draft's authors (source not in repo); `src/korea_growth/empirics/`; synthetic Monte Carlo test (§6) | test shows naive OLS biased, recentred 2SLS ≈ unbiased, RI-AR coverage ≈ nominal |
| **B. Archival audit** (in parallel with A) | plans, construction histories | `data/raw/road_projects.csv` (schema below) and a short memo on assignment | enough units with variation in `D` for a usable RI (rule of thumb: ≥ 10 units, ≥ 3 not operational by 1987); delay reasons documented and plausibly unrelated to township prospects |
| **C. Long-difference prototype** | 1975/87 networks (geography pipeline), project table | `x`, `q`, `μ`, `z`; §3 table and maps | meaningful first stage; balance on pre-trends |
| **D. Panel and mechanisms** | annual township panel, opening dates | E1–E4 | conditional F for E2 |

**Fallbacks at gate B:**
- If expressway projects alone give too few units, audit national-road paving packages.
  These plausibly carried most of the 1974–87 change in travel times and would supply far
  more units.
- If neither yields a defensible mechanism, report the μ-controlled specification as a
  sensitivity check. Do not present it as causal.

**Sources to audit:**
- the First (1972–81) and Second (1982–91) Comprehensive National Land Development Plans;
- Korea Expressway Corporation histories;
- Ministry of Construction road plans and yearbooks;
- appraisal and completion reports for any loan-financed highway projects, which record
  planned scope, schedules and reasons for delays;
- interchange opening dates.

**Project table schema:** `project_id, name, road_class, plan_document, plan_year,
stratum vars (wave, priority, terrain), planned_start, planned_completion, actual_start,
actual_opening, alignment_source {built, plan_map, lcp}, edge_ids, prerequisite_ids,
interchanges (id, opening_date), delay_reason (coded), planned_cost_per_km`.

---

## 6. Code layout and synthetic test

```
src/korea_growth/empirics/
  network.py     edge table → sparse graph; multi-source Dijkstra (scipy.sparse.csgraph)
  access.py      log MA and q_i(D) for any cost formula; destination mask with frozen ranks
  assignment.py  stratified assignment model with dependencies; enumerate() / sample(B, rng)
  recenter.py    μ and draws of z; 2SLS with μ control; randomisation AR confidence set
tests/test_recentering.py
```

Compute is trivial: each assignment needs one 28-source Dijkstra run.

**Synthetic Monte Carlo (the Phase A gate).**
- Setup: a grid network with about 8 cities and about 10 candidate corridors in 2–3 strata.
- Outcome: `ΔY = β x + λ·centrality + u`, where centrality is correlated with `μ`.
- Local paving is correlated with `u`, to show why §2.3 holds local roads at baseline.
- Across replications that redraw `D` from the assignment model:
  - naive OLS is biased;
  - recentred 2SLS is centred on `β`;
  - the RI-AR set covers `β` at about the nominal rate.

This validates the code before any real data arrive.

---

## 7. Open questions for the team

1. Do the plan documents list delayed or unbuilt expressway and national-road projects, with
   alignments?
2. Which map underlies the draft's "1974" network — the 1975 snapshot?
3. Is the 30 km paved-density control a baseline level or a change?
4. In the J-exclusion, which year's travel times define `rank(i,c)`?
5. Will annual paving dates (`fresh_look.md:765`) be available? That decides whether paving
   packages can be assignment units.
