# Model Status & Roadmap

Status of the `korea_growth` model relative to the referee report in
[`docs/model_review.md`](docs/model_review.md). It records what has been fixed, the
modeling choices that still need a decision, and a sequenced plan for the remaining work.

_Last updated: 2026-07-06 (branch `claude/model-review-md-jjiaa2`)._

> **2026-09-29 update.** [`docs/fresh_look.md`](docs/fresh_look.md) re-evaluates the model
> against the macro goal (how Korea escaped poverty, 1960–90) and the township panel being
> digitised. Its findings supersede parts of this roadmap. The trade closure was
> indeterminate and is now fixed (§2 below). The calibrated economy misses Korea's 1965 macro
> margins, has no growth engine, and has no traditional agriculture. It proposes re-sequencing
> Phases 2–4 around "baseline = history": annual inversion, gravity with external economies in
> place of Melitz, occupation choice, farm-size-based agriculture, and capital and schooling.

> **2026-10-03 update.** The referee report [`docs/review_fresh_look.md`](docs/review_fresh_look.md)
> is implemented; its §8 lists what was done for each item. Code: nested entry/adoption/export
> choice, separate export demand elasticity `sigma_x`, exact PIGL equivalent income for
> migration and welfare (`expected_utility`), an error for infeasible surplus targets, and
> `accounting.py` (employment in workers, value added, double-deflated real GDP). The +0.127
> → +0.057 claim was checked on `cdafe29`. The 1985 heavy-manufacturing effect is now +0.103
> on the gross-output share (+0.088 value added, +0.092 employment), after the nested choice
> and the agricultural recalibration (traditional farming 0.97 of farm output in 1965). `fresh_look.md` is
> revised: an identification caveat on the inversion, "Matsuyama in space" restated as a
> model-generated prediction, separate access measures, and an agriculture-first build order.

> **2026-10-04 (later).** Sector-specific wages added as theory and code: nested occupation
> choice inside location choice (`model.tex` section "Occupation choice and sector-specific
> wages"; `eps_occ`, `b_occ`, `occupation_of_sector`). It removes the integrated market's
> mechanical limit on the agricultural productivity gap. Not recalibrated: the baseline still
> uses the integrated market. Illustration in `docs/fresh_look.md` §2.7.
>
> **2026-10-04 update.** The baseline now reproduces Korea's 1965–85 structural
> transformation (`scripts/korea_baseline.py`, `scripts/calibrate_history.py`): farm
> employment 0.605 → 0.229, manufacturing value added 0.192 → 0.298, real GDP ×4, exports
> 0.08 → 0.33, urbanisation 0.32 → 0.63 (0.547 in 1980). Sectors: protected Rice,
> import-competing OtherAg, Manufacturing, non-traded Services. Open: the agricultural
> productivity gap (needs sectoral wages or occupation wedges), real input–output data, and
> the HCI aggregate effect, which is negative under this baseline. See `docs/fresh_look.md` §2.6
> and `scripts/data_targets.py` for target provenance.

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
sims converge; all tests pass. The corrected accounting was reported to lower the 1985
heavy-manufacturing effect from **+0.127 → +0.057**. That number came from an indeterminate
closure (see the trade-closure item below). With a determinate closure the effect is
**+0.104** (gross-output share). Checked on `cdafe29`: the old code reproduces +0.127 and is
guess-invariant. It had no foreign transfer and leaked land rents and fixed costs, which left
an implied surplus of ~27% of gross output. So the accounting fixes lowered the effect by about
0.02; the rest of the drop to +0.057 was the indeterminate closure's selection. With the nested
entry/adoption/export choice (2026-10-03) the effect is **+0.095**; after the agricultural
recalibration it is **+0.103**.

---

## 2. Open decisions (cheap, but change results — confirm before Phase 2)

These are modeling choices currently set to a default and flagged inline as
`% [REVIEW FLAG ...]` in `model.tex`. Revisit before building on them.

- ~~**Trade closure (§1.5).**~~ **Resolved 2026-09-29.** Carrying `T = IM − EX` into income
  was not a residual closure but an indeterminate one. Income = expenditure plus goods-market
  clearing already imply `T = IM − EX`, so the external-balance condition was lost. Solutions
  then depended on the initial guess: wages differed by 65% and trade deficits ranged from 37%
  to 67% of absorption. No extra instrument is needed: `T = −NX*` with
  `NX* = nx_gdp_t · GDP` exogenous (default 0), and the domestic price level clears the
  foreign account. Tested for guess invariance. See `docs/fresh_look.md` §2.1.
- ~~**Cutoff ordering (§2.2).**~~ **Resolved 2026-10-03** by (b), the nested discrete
  choice (`trade.nested_cutoffs`): exporters and adopters are active firms, and agricultural
  exporters are adopters. The resulting corner (every active farm mechanised and exported)
  was removed by recalibration: `xi = 1.2`, fixed costs in labour units, and `Dtilde_Agri`
  and `Fbreve_Agri` set by `scripts/calibrate_agriculture.py` (since superseded by the
  history-calibrated baseline, below) to a 1965 traditional share of
  0.97 and 1% farm exports. **Still open:** farm employment is 11% (food imports are 58% of food
  spending); food import protection (τ̃_Agri) is the next lever, and services/manufacturing
  foreign demand still makes exports 73% of GDP.
- **Numeraire (§1.5).** Foreign heavy-mfg price ≡ 1. Alternative: fix aggregate income.
- **Ownership (§1.1/§3.4).** Local land + nationally-pooled wage-proportional profits.
  Incidence work may want *local* profit retention; add as a robustness switch.
- **Infra allocation (§1.4).** `G^infra` split 50/50 heavy-mfg/services by population.
  Consider a dedicated construction sector.
- ~~**Welfare wiring (§3.9).**~~ **Resolved 2026-10-03.** Migration and welfare both use the
  exact PIGL equivalent income at unit reference prices (`preferences.equivalent_income`).
  The inclusive value is computed by `preferences.expected_utility`, and a test checks that
  its gradient equals the migration shares. Not yet reported by the policy script.
- **Transfer use.** The foreign transfer financing a deficit is consumed. Once capital
  enters, it belongs in the investment identity.
- **Export demand elasticity.** `sigma_x` exists (default `sigma`) but is not yet calibrated.
  The headline depends on it heavily: the 1985 heavy-mfg gross-output effect is +0.021 /
  +0.103 / +0.137 at `sigma_x` = 2 / 4 / 6.

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
