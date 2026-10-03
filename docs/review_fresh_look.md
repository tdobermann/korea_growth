# Referee Report: PR #4 (trade closure) and the "Matsuyama in space" proposal

Consolidated from two independent reviews of PR #4 (`11a124c`, `a505c80`, merged as
`173e79e`) and of [`fresh_look.md`](fresh_look.md). Both reviewers reproduced the macro
scorecard and the initial-guess invariance check against the merged code. One reviewer ran the
full test suite (10 tests pass; `pytest` has to be installed separately). Numerical claims
below were re-derived from the repository unless marked otherwise.

_Written 2026-10-03._

---

## 0. Summary

| Item | Verdict |
|---|---|
| Trade-closure diagnosis and fix | Correct and important. Restores a missing equilibrium condition; the regression test is the right guard. |
| Headline policy numbers (+0.104 heavy-mfg share) | Provisional. Robust to the trade-balance default, but computed on an economy with the entry/export/adoption inconsistency still present, and the label "share" is ambiguous. |
| Scorecard measurement | Two errors: agricultural employment is mismeasured, and "real GDP" is nominal GDP over a consumption deflator. |
| Migration welfare index | The claim that it is a monotone transform of indirect utility is false for η ≠ 0. Rankings coincide in the current calibration, but the elasticity differs. |
| `model.tex` closure section | Sign error: adds NX\* to income where the code (correctly) adds −NX\*. Fixed in this PR. |
| "Matsuyama in space" | A good idea posed too sharply. The sign flip is a demand-elasticity test that the proposed gravity structure guarantees by construction; connectivity moves goods-market and labour-market access together; irrigation is not Hicks-neutral. Re-pose as a model-generated prediction with separate access measures. |
| Annual inversion (§3.1 of the memo) | Not identified as written. Productivity and occupation wedges cannot both be recovered from employment shares without wages or output. |
| Build sequence | Put the small agriculture–non-farm spatial model first; the growth-engine blocks later. |

---

## 1. The closure fix

### 1.1 The diagnosis is right

With a foreign numeraire and exogenous foreign demand, summing household budgets and
goods-market clearing gives

Σ excess demand + (EX − IM + T) = 0.

Setting T = IM − EX at the current guess makes one goods-market equation redundant and leaves
the domestic price level relative to the foreign numeraire free. The one-good example in the
memo is the right minimal demonstration. Pinning T = −NX\* exogenously restores the condition.
The fixed-point map imposes it correctly: because T is now exogenous, income = expenditure
plus clearing force EX − IM = NX\* at any fixed point, and `aggregates["nx_residual"]`
reports it. Both reviewers reproduced the guess invariance (relative wage difference
≈ 3 × 10⁻¹³). One reviewer also checked a 5% deficit and a 5% surplus in the toy model; the
target and the resource accounting held. These checks support the fix; they do not establish
global uniqueness.

### 1.2 The headline is robust to the trade-balance default

Re-running the policy simulation with an exogenous deficit path:

| `nx_gdp` | 1985 heavy-mfg share effect | baseline EX/GDP | baseline IM/GDP |
|---|---|---|---|
| 0.00 | +0.104 | 0.948 | 0.948 |
| −0.05 | +0.102 | 0.924 | 0.974 |
| −0.10 | +0.100 | 0.899 | 0.999 |

The insensitivity is itself a symptom. At 95% openness with σ = 4, a 10-point swing in the
deficit barely moves the real exchange rate. In a Korea-like economy with a 9% export share,
the same closure would matter far more. The fix matters more for the future model than for
the current numbers.

### 1.3 Issues to fix

1. **Sign error in `model.tex`.** The disposable-income equation in the "Trade" subsection
   wrote `… − τ̄W + NX*`, and the prose called NX\* "a trade deficit financed from abroad". The
   code sets the household transfer to −NX\* (a deficit, NX\* < 0, is a positive transfer).
   Corrected in this PR.
2. **The "+0.127 → +0.057 was a selection artifact" claim is asserted, not shown.** Nobody
   re-ran the pre-accounting-fix code under the determinate closure. One run on the old
   commit with `nx_gdp = 0` settles it.
3. **The transfer is consumed, not invested.** Foreign saving in 1960s–70s Korea financed
   capital formation. Distributing it proportionally to income is a placeholder; once capital
   enters (memo §3.5), the current-account deficit belongs in the investment identity. The
   `max(1e-8, …)` floor on the transfer scale also hides an infeasible surplus target
   silently; it should raise.
4. **Label the headline moment.** The +0.104 is a change in the *gross-output* share
   (`aggregate_output_shares` in `scripts/simulate_policy_shock.py`). Employment shares and
   value-added shares are different objects and should be reported separately.
5. **The aggregate trade elasticity is doing new work.** External balance now pins the wage
   level through the export demand elasticity, which is the same σ as domestic substitution.
   It should be a separate, externally calibrated parameter (memo §1.3 already says so).
6. **The entry/export/adoption inconsistency still stands.** `trade.py` counts exporters from
   φ̃ and adopters from φ̆ regardless of φ̄, and `upper_trad = min(φ̆, κ)` yields zero
   traditional output when φ̆ < φ̄, which is the calibrated state everywhere. The updated
   policy effects therefore cannot yet speak to the mechanisation mechanism.

---

## 2. Measurement and preference problems to fix before extending

### 2.1 Agricultural employment is mismeasured in the scorecard

`_sector_labor` in `scripts/macro_scorecard.py` sums *variable labour payments* across
regions. It omits fixed-cost labour (which the model pays in local labour) and does not divide
regional payments by regional wages, so high-wage regions are over-weighted. The consistent
count is

L_ij = (variable labour payments_ij + fixed-cost labour payments_ij) / w_i.

Re-computed on the merged code (the recount sums exactly to total population, confirming
labour-market clearing):

| Agricultural employment share | Scorecard (payments) | Workers, consistent |
|---|---|---|
| 1965 | 23.5% | 28.0% |
| 1985, baseline | 21.5% | 25.3% |
| 1985, HCI | 18.9% | 22.5% |

The gap to the 59% benchmark remains large, but its size changes, and the scorecard should
report workers.

### 2.2 "Real GDP" is nominal GDP over a consumption deflator

The scorecard divides nominal GDP by a population-weighted geometric mean of regional
consumption composite prices. That is a purchasing-power measure, not a production volume
index. Use a production-side deflator (or a chained Laspeyres on sectoral gross output less
intermediates) for comparison with real GDP, and report consumption purchasing power
separately.

### 2.3 The migration index is not a monotone transform of indirect utility

`real_income_index` returns Y = (y/𝒫) · exp(−Σ v_j log P_j) and its docstring claims this is
"a positive, monotone transform of indirect utility" for general η. With x = y/𝒫 and
z = Σ v_j log P_j, utility is V = x^η/η − z. The index x·e^{−z} is a monotone transform of V
only when z is constant across destinations or η → 0. The exact PIGL equivalent income at
reference prices (𝒫₀, z₀) is

Y^eq = 𝒫₀ · [η (V + z₀)]^{1/η}.

In the current calibration the three objects (V, the index, Y^eq) rank the five regions
identically in every period, so there is no ranking inversion today. But the income elasticity
differs: ∂ log Y/∂ log x = 1 for the index, whereas for Y^eq it is x^η/(x^η − η z₀), so the
estimated ν does not have the interpretation the memo gives it. Replace the index with Y^eq
(the formula is already in `model.tex` as the welfare metric) and add a test that migration
and welfare agree.

---

## 3. "Matsuyama in space"

The proposition (memo §3.4): in quasi-closed townships a land-augmenting shock (reservoir)
releases farm labour via the food-problem and Engel channel; in connected townships it retains
labour via comparative advantage; so the sign of reservoir × market access on farm employment
should flip. The intuition is legitimate, and Korea is an unusually good setting for it (§3.5
below). But as stated it conflates three forces.

### 3.1 It is a demand-elasticity test, and the proposed structure bakes in the answer

Under Armington or Eaton–Kortum (memo §3.2), a township's farm output faces demand elasticity
θ when connected and roughly the local PIGL food elasticity when isolated. Labour is retained
iff the faced elasticity exceeds one. With θ in the 4–8 range and food inelastic, the flip is
guaranteed by construction. What the data then identify is *where* on the market-access
distribution the crossing occurs, which is informative about φ_k and the Engel parameters but
not about "which Matsuyama regime Korea was in". Note also that Matsuyama's open case needs a
homogeneous traded good, which Armington removes.

A minimal diagnostic makes the condition explicit. With Q_i = (B_i T_i)^α L_Ai^{1−α} and
competitive farms,

d log L_Ai / d log B_i = 1 + (1/α) · (d log p_Ai / d log B_i − d log w_i / d log B_i).

(Illustrative, not from the repository model.) The sign depends on the local crop-price
response relative to the opportunity-wage response. Connectivity moves both.

### 3.2 Connectivity moves goods-market and labour-market access together

Connected townships also have non-farm job access, cheaper machinery and lower migration
costs. Industrial pull releases farm labour, which has the opposite sign to the
comparative-advantage retention effect. A null on the interaction is uninterpretable without
separately controlling for shift-share industrial pull, and even then the coefficient is a
composite. This is the strongest argument for the memo's own indirect-inference approach:
generate the interaction coefficient from the model and match it, rather than reading a sign.

### 3.3 Irrigation is not Hicks-neutral land augmentation

Korean paddy irrigation plus Tongil HYV raised labour per hectare (double cropping,
transplanting intensity). A labour-complementary shock retains labour everywhere, open or
closed, independently of the Engel channel. Bustos–Caprettini–Ponticelli is cited for the
labour-saving versus land-augmenting distinction, but their soy-versus-maize contrast is
exactly what Korean reservoirs lack. Either find a cleanly land-augmenting shock or estimate
the factor bias jointly with the openness interaction.

### 3.4 Two further reconciliations

- **National rice-price support.** The memo also proposes procurement at a policy-wedged
  price from 1969. If procurement insulates farm-gate prices from local supply, the
  isolated-township food-price channel weakens. The price-policy block and the sign
  prediction must be reconciled.
- **Township retention is not aggregate retardation.** Local agricultural retention can
  coexist with national industrialisation and higher welfare. Matsuyama's growth conclusion
  additionally requires manufacturing learning-by-doing. A township employment response does
  not establish the aggregate growth effect.

### 3.5 What is right about the setting

Korea's rice market was nationally closed and policy-priced after 1969. A township is open to
the nation while the nation is closed to the world, so the "regime" is township-level by
construction. The spatial Matsuyama question is better posed in Korea than in most settings.
Say so explicitly.

### 3.6 Reformulation

State the hypothesis as: *agricultural productivity growth induces commercialisation where
access to crop demand dominates, and labour release where access to non-farm opportunities
dominates.* A connectivity-dependent sign reversal is then one derivable implication, to be
stated as "the model with θ, φ, η estimated elsewhere predicts an interaction coefficient of X;
the data give Y", a held-out moment in the memo's own framework.

---

## 4. Empirical design

The proposed reservoir × market access interaction combines the two mechanisms the paper
should separate.

- **Separate access measures.** Estimate reservoir event-study responses by *predetermined*
  access to crop markets and *predetermined* access to non-farm employment, using distinct
  measures. Heterogeneity by initial access shows how effects differ across places;
  identifying roads' causal contribution additionally needs credible variation in road access.
- **Outcomes that discriminate between channels.**

  | Channel | Evidence to seek |
  |---|---|
  | Commercialisation | Marketed output, sustained farm-gate prices, agricultural labour demand, land returns |
  | Labour release | Lower labour per hectare, mechanisation, movement into non-farm work or migration |
  | Local demand spillovers | Rural service employment following farm-income gains |

  Farm employment alone will not distinguish these. Measure levels, shares and labour intensity
  separately, alongside population and commuting. Use the employment *share* for the Matsuyama
  test, since migration contaminates levels.
- **Treatment definition.** Follow the irrigation command area and operational water
  delivery, not the township containing the reservoir. Construction employment, associated
  roads, displacement and downstream effects need explicit treatment. Neither completion
  dates nor engineering suitability establishes exogeneity on their own.
- **Placebo.** Dry-field townships, where reservoirs matter less.
- **A positive interaction coefficient is not a sign reversal.** Show that the estimated
  irrigation effect crosses zero within the observed support, with uncertainty bands. The
  employment interaction does not identify complementarity in national welfare.

---

## 5. The annual inversion is not identified as written

Memo §3.1 claims productivity Ā_{ik,t}, amenities B_{i,t} and occupation wedges b_{ik,t} can be
recovered exactly from township population and sectoral employment without wages.

Count per township-year under §3.2–3.3: unknowns are K productivities, K − 1 wedges (after a
normalisation) and one amenity, 2K in all. Observables are population and K − 1 employment
shares, K in all. In π_{k|i} ∝ (b_ik w_ik)^ε, a higher A_ik raises w_ik and hence π_{k|i},
exactly as a higher b_ik does. Without wages, output, prices or trade flows, A and b are not
separately identified. Before building `inversion.py`, write down unknowns, observables,
normalisations and restrictions, and demonstrate identification analytically or by a
numerical rank/recovery exercise. Some wedges will need restrictions or additional data.

Two related claims need weakening:

- **Inverted fundamentals are not causal policy effects.** Event studies on them still need a
  credible assignment design and must propagate inversion uncertainty.
- **Exact fit is not validation.** If township sectoral employment is an inversion input, its
  national sum cannot also validate the model. Holding observed capital or schooling paths
  fixed while removing HCI excludes policy effects running through those paths; that is a
  conditional counterfactual whose interpretation must be explicit. Shapley decomposition
  allocates interactions consistently but resolves neither problem.

---

## 6. Novelty

Cheung and Yang, "Transportation Networks, Technology Adoption, and Structural
Transformation" ([SSRN 4768158](https://ssrn.com/abstract=4768158), 2024; reported by one
reviewer as forthcoming in the *Journal of International Economics*, 2026, to verify), studies
transport improvements lowering non-labour input prices relative to wages, inducing
labour-saving agricultural technology and structural transformation in India. That overlaps
directly with the roads → machinery → labour-release mechanism in the memo. Transport-induced
mechanisation alone will not distinguish this project. The stronger contribution is to
separately identify agricultural productivity shocks, industrial labour-demand shocks and
connectivity, and to explain where their interaction produces commercialisation versus labour
release. The Korean panel is unusually well suited to that; whether it delivers depends on
treatment variation and mechanism measurement, not on the breadth of the final model.

---

## 7. Build sequence

The memo places the agriculture block at Stage 3, after occupation choice, capital,
forward-looking migration and human capital. That delays the mechanism behind "Matsuyama in
space" until much of a large model exists. Preferred order:

1. Fix employment measurement (§2.1), the GDP deflator (§2.2), the migration/welfare index
   (§2.3), and the production-choice inconsistency (§1.3 item 6).
2. Build a small spatial model with agriculture, non-farm production, land, goods trade and
   labour mobility. Derive the conditions for each employment response (§3.1).
3. Audit irrigation exposure and estimate the differentiated event studies (§4), including
   prices, wages and labour intensity.
4. Expand the quantitative model around the mechanisms that survive.

Annual timing, competitive agriculture and a simpler trade block are sensible. Capital,
schooling, poverty distributions and the full national growth decomposition should enter when
the chosen counterfactual requires them.

---

## Appendix — reproducing the checks

- Scorecard and guess invariance: `python scripts/macro_scorecard.py`.
- Tests: `pip install -e .[dev] && pytest -q` (10 pass on `173e79e`).
- §1.2 and §2 numbers: solve `build_baseline_inputs()` / `with_hci_policy()` with
  `SolverOptions(max_iter=20000, tol=1e-10, damping=0.25)`; for §1.2 set `nx_gdp` to a
  constant path via `dataclasses.replace`; for §2.1 sum `(variable + fixed labour
  payments) / w` by sector from `compute_sector_state`; for §2.3 compare `indirect_utility`,
  `real_income_index` and the equivalent income 𝒫₀[η(V + z₀)]^{1/η} across regions.
