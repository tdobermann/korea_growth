# Model Status & Roadmap

Status of the `korea_growth` model relative to the referee report in
[`docs/model_review.md`](docs/model_review.md). It records what has been fixed, the
modeling choices that still need a decision, and a sequenced plan for the remaining work.

_Last updated: 2026-07-06 (branch `claude/model-review-md-jjiaa2`)._

---

## 1. Done

### Theory document (`docs/model.tex`) — commit `cdafe29`
Corrected the primer to state the right theory (review §1, §2, §7, plus the write-up parts
of §3.5/3.9/3.10): accounting that adds up, migration re-derived from Gumbel shocks on a
positive money-metric index, the `ξ` fix, cutoff-ordering restriction, welfare
(inclusive-value) formula, existence/multiplicity and market-structure caveats, timing,
PIGL regularity conditions, a self-contained equilibrium definition, and macro cleanup.

### Code pass (`src/korea_growth/`) — commit `015588b`
All 8 "theory-consistent minimum" items are implemented and tested:

| # | Fix | Review | Where |
|---|-----|--------|-------|
| 1 | `ξ` in domestic mechanized aggregate `Z̆` | §2.1 | `trade.py` |
| 2 | Subsidy grossing-up: true factor cost `TFC = (σ−1)/(σ(1−s))·R` in factor + intermediate demand and subsidy outlay | §1.3 | `equilibrium.py` |
| 3 | Land rents rebated to residents (`r·H/L` in income; inner fixed point for `L`) | §1.1 | `equilibrium.py` |
| 4 | Fixed costs paid in local labor (`Φ^F`) | §1.2 | `equilibrium.py` |
| 5 | Infrastructure buys goods (`E^G` into clearing) | §1.4 | `equilibrium.py` |
| 6 | Migration on positive `real_income_index` | §2.3 | `preferences.py` |
| 7 | Sign-unrestricted `π̄`/`τ̄` (level updates) | §2.4 | `solver.py` |
| 8 | PIGL restrictions + Walras/ordering checks | §1, §2.2, §7.3 | `checks.py`, `tests/test_accounting.py` |

Walras / resource / government identities hold to ~1e-13 at the solution; toy and policy
sims converge; all tests pass. The corrected accounting also lowered the 1985
heavy-manufacturing effect from **+0.127 → +0.057** (consistent with review §4.6).

---

## 2. Open decisions (cheap, but change results — confirm before Phase 2)

These are modeling choices currently set to a default and flagged inline as
`% [REVIEW FLAG ...]` in `model.tex`. Revisit before building on them.

- **Trade closure (§1.5).** Net position `T = IM − EX` is carried into income *proportional
  to income*, so `NX*` is an endogenous residual rather than pinned to 0. Truly imposing
  `NX* = 0` needs an added equilibrating instrument (e.g. an aggregate transfer/relative
  price that clears the foreign account). Decide whether the residual closure is acceptable
  or the instrument is worth adding.
- **Cutoff ordering (§2.2).** `φ̄ ≤ φ̆ ≤ φ̃` is a *diagnostic*, and the toy calibration
  violates it (~1.1). Choose between (a) primitive parameter restrictions that guarantee it
  (then enforce in `checks.py`), or (b) solving the joint adoption–export discrete choice.
- **Numeraire (§1.5).** Foreign heavy-mfg price ≡ 1. Alternative: fix aggregate income.
- **Ownership (§1.1/§3.4).** Local land + nationally-pooled wage-proportional profits.
  Incidence work may want *local* profit retention; add as a robustness switch.
- **Infra allocation (§1.4).** `G^infra` split 50/50 heavy-mfg/services by population.
  Consider a dedicated construction sector.
- **Welfare wiring (§3.9).** The inclusive-value formula (`model.tex` eq. `welfare`) is
  derived but not yet *computed and reported* by the solver, and the exact PIGL money metric
  for general `η` (vs. the log-case index now used) is still a to-derive appendix item.

---

## 3. Roadmap for the remaining edits

Ordered so each phase is independently useful. Phase numbering follows review §5. Severity
and effort are from the review's summary table.

### Phase 2 — Re-specify the vulnerable blocks
Structural changes that alter what the model can say. None attempted yet.

1. **Capital and credit wedges (§3.1, severity: high).** HCI's real instruments were
   directed credit at negative real rates, tax holidays, and public capital — not output
   subsidies. Add sector–region capital with a rental-rate wedge `(1 + s^K)` as the policy
   instrument, plus accumulation with time-to-build. Gives a second state variable (where
   the dynamics live). *Touches:* `types.py` (new exogenous paths + state), `production.py`
   (capital in the cost bundle), `equilibrium.py`, `solver.py` (second state), scripts.
2. **Annual, forward-looking migration (§3.2, high).** Periods are unevenly spaced
   (1965/68/73/75/80/85), so per-period elasticities have no consistent time meaning, and
   myopia understates reallocation toward credibly-growing places. Go annual; move to
   dynamic discrete choice (Caliendo–Dvorkin–Parro) or at least add a perfect-foresight
   robustness run. *Touches:* time grid in scripts, `preferences.py`, `solver.py`.
3. **Sector-specific `σ_j` and (near-)non-traded services (§3.6, medium).** One `σ` now
   governs rice, machine tools, and imported services through the same friction matrix.
   Make `σ` a vector and give services a high internal trade cost. *Touches:* `types.py`
   (`sigma` → `sigma_j`), `trade.py`, `checks.py`.
4. **Separate inbound vs outbound port frictions (§3.7, low).** `tautilde` currently does
   double duty as import and export friction; split into two arrays. *Touches:* `types.py`,
   `trade.py`.
5. **Competitive agriculture with heterogeneous land (§3.5, medium).** Replace Melitz
   monopolistic-competition agriculture (millions of farmers with markups) with competitive,
   homogeneous-good agriculture and land-quality heterogeneity (Sotelo 2020), or justify the
   current structure with robustness. *Touches:* `trade.py`, `production.py`.
6. **Land/housing in utility (§3.9/§7.4).** Price congestion through housing demand rather
   than the reduced-form `ι < 0`, making `ι` estimable. *Touches:* `preferences.py`.
7. **Free entry / population-scaled entrant mass (§3.4, medium).** `M_{j,t}` varies by
   sector–time but not region, forcing all scale effects through `L^{ρ}`. Make potential
   entrants proportional to local labor, or add a sunk entry cost. *Touches:* `trade.py`.

### Phase 3 — Scale the geography and invert
8. **County-level geography (§4.3, high).** Five regions cannot express the paper's best
   fact — the sign reversal of market-access effects by industrial-park distance (Figure 8).
   Move to ~160–183 counties with `τ_od` from the digitized road network by year and parks
   located where they actually were. *Touches:* data pipeline (new), all dimensions.
9. **QSE inversion (§4.2).** Given observed populations/wages/employment, back out amenities
   `V̄` and productivities `A` in the baseline year; let policy + estimated elasticities move
   them thereafter, replacing hand-set exogenous paths.

### Phase 4 — Estimate, don't calibrate directionally
10. **Stop hard-coding the empirics (§4.1, fatal-for-credibility).** The agricultural
    channel imposes `A_Agri` and `β_Agri` paths to *match* Tables 2/4 while the model
    already has an endogenous mechanization margin (`F̆`, `φ̆`). Let roads → market access →
    adoption generate those outcomes so Tables 2/4 become targets, not inputs. *Touches:*
    `scripts/simulate_policy_shock.py` (Channel 3).
11. **Validate parks against the SDID (§4.2).** Replace Changwon's `A × 1.5` with modeled
    park inputs (entry-cost cuts, credit wedges, site infrastructure, port access), estimate
    `ρ_j`, and ask whether the model *reproduces* the SDID event study as an (un)targeted
    moment.
12. **Discipline the free parameters with data (§4.4–§4.5).** `θ`/`κ` from the MMS
    firm-size distribution; `ν` and `δ_od` by gravity on O–D flows; `D̃_{j,t}` from world
    import demand (the current `×1.15` is an order of magnitude too timid); external `σ_j`.
    Estimate the crucial vector `(ρ_j, ι, η, v_j, adoption cost)` by indirect inference and
    hold out one quasi-experimental moment as untargeted validation.

### Phase 5 — Counterfactuals that answer questions
13. Parks-only / roads-only / both (the complementarity); welfare incidence by region ×
    worker/landowner × income; persistence / big-push (remove policy after 1979, map the
    threshold); spatial-misallocation reallocations of the same fiscal envelope. Requires the
    welfare metric (item in §2 above) wired into the solver output.

### Phase 6 — Rewrite `model.tex` as a submission model section
14. Primitives → preferences (with the shock structure) → technology → market structure →
    formal equilibrium definition → propositions (existence; cutoff ordering; welfare) with
    proofs and cutoff derivations in an appendix (§6). Every asserted equation (e.g. the
    `σ^{1/(σ−1)}` cutoff factor) must be derived. Also: real author/title (§7.1), literature
    positioning (§6), and rebuild `docs/model.pdf` (currently stale — no LaTeX toolchain in
    the dev container used for the last passes).

---

## 4. Suggested next step

Phase 2 items **3 (sector-specific `σ_j`)** and **4 (split port frictions)** are the
cheapest ("an afternoon" each per the review) and remove easy referee kills without
disturbing the rest of the model — a good warm-up. **Item 1 (capital/credit)** is the
highest-value structural change but is genuinely large (new state variable + solver work);
scope it deliberately before starting. Everything in Phases 3–4 depends on a data pipeline
that does not yet exist in the repo, so budget for that first.
