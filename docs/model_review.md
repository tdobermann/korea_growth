# Red-Team Review of `model.tex`: From Solver Primer to Top-5 Model

**Scope.** This is a referee-style evaluation of `docs/model.tex` in light of (i) the
empirical draft (`docs/paper_draft05032026.pdf`, "The Miracle on the Han"), (ii) the code
the tex documents (`src/korea_growth/`), and (iii) the state of the art in quantitative
spatial economics and the industrial-policy literature on Korea. The standard applied is
that of a QJE/AER/ECMA/JPE/ReStud referee.

**Verdict up front.** The ingredient list is genuinely well chosen — PIGL non-homothetic
demand, migration, heterogeneous firms with an endogenous agricultural-mechanization
margin, IO linkages, and policy wedges is exactly the right chassis for a "did the
miracle reach the countryside" paper. But the current model would be desk-rejected at a
top-5 for three reasons, in increasing order of difficulty to fix:

1. **The economy does not add up.** Walras's law fails in at least four places (land
   rents, fixed costs, subsidy accounting, infrastructure spending), so no welfare or
   counterfactual number produced by this system is currently interpretable.
2. **The theory contradicts itself** in the mechanization block (the adoption cutoff and
   the aggregation of adopters use different technologies) and the migration block (the
   choice probabilities are not invariant to how utility is cardinalized, and can be
   undefined).
3. **The model does not yet digest its own empirics.** The calibration hard-codes the
   paper's findings (regional productivity boosts, factor-share shifts) instead of
   letting the model's own endogenous margins generate them — so counterfactuals assume
   their conclusions. The paper's most novel empirical object (the sign reversal of
   market-access effects by industrial-park distance, Figure 8) cannot even be expressed
   in a 5-region geography.

Everything below is organized as: §1 fatal consistency problems, §2 theory–code
contradictions, §3 modeling choices that will not survive review, §4 failures of
empirical integration, §5 a concrete roadmap to a top-5 paper, §6 literature the paper
must engage, §7 minor and expositional issues.

---

## 1. Fatal: the accounting does not close

A quantitative GE paper lives or dies on its budget constraints. Here aggregate income
and aggregate expenditure are not linked by any adding-up condition, and the leaks are
*policy-dependent*, so they contaminate exactly the counterfactuals the paper cares
about.

### 1.1 Land rents vanish from the economy

Households receive `y_pc = (1 − τ̄ + π̄) w` (model.tex eq. (1); `preferences.py:100`).
Land income `r_o H_o` is computed to clear the land market
(`equilibrium.py:193-194`) but is **paid to no one**: it enters no household's income,
no government budget, and no rebate. In a paper whose central question is rural
incidence, this is disqualifying twice over — once because expenditure ≠ income, and
once because *land-value capitalization is the canonical welfare metric for
market-access improvements* (Donaldson–Hornbeck 2016). Agricultural modernization that
raises rural land rents currently produces welfare gains the model literally throws
away.

### 1.2 Fixed costs are resource destruction

Entry, export, and adoption fixed costs (`F`, `F̃`, `F̆`) are subtracted from aggregate
profits (model.tex, Π equation; `equilibrium.py:202`) but are not paid *to* anything —
no labor, no goods. In Melitz, fixed costs hire workers; here they are pure waste. This
matters directionally: the HCI counterfactual cuts `F` and `F̆`, which mechanically
raises rebated profits without any offsetting reallocation of the resources those fixed
costs previously absorbed.

### 1.3 Subsidy accounting is internally inconsistent

Prices embed the subsidy: `p = σ/(σ−1) · (1−s) · c/φ`. Under that pricing rule, the
physical input bundle costs `(σ−1)/(σ(1−s)) · R`, of which the firm pays
`(σ−1)/σ · R` and the government pays the rest. But the code and tex use
`VC = (σ−1)/σ · R` as **total** factor payments (`equilibrium.py:135`) and compute
government subsidy outlays as `s · (σ−1)/σ · Y` (`equilibrium.py:206`; model.tex
government-budget equation), both missing the `1/(1−s)` factor. Consequences:

- factor demands are understated by a factor `1/(1−s)` in subsidized sectors — with the
  calibrated `s = 0.25` at Changwon, labor and land demand there are understated by 33%;
- the taxed subsidy revenue never reaches factor owners: households are taxed `τ̄` for
  spending that then disappears.

Since the size of the leak scales with `s·Y` — i.e., with the policy itself — the HCI
counterfactual results are biased in a way that is not signable ex ante.

### 1.4 Infrastructure spending is a pure tax

`G^infra` raises `τ̄` but purchases no goods and hires no one (model.tex §6). Road
spending should either buy construction output (creating demand somewhere) or be
explicitly modeled as the resource cost of the `τ` declines. As written, the "roads"
counterfactual combines a *free* trade-cost reduction with an unrelated lump-sum tax.

### 1.5 No trade balance, no numeraire

Exports earn revenue from an exogenous foreign demand shifter `D̃_j`; imports are
whatever CES demand allocates to the foreign variety. Nothing requires these to balance,
no deficit enters any budget, and the numeraire is never stated (implicitly the foreign
price `p̃`). A small-open-economy treatment is fine, but it must be explicit: state the
numeraire, define the trade deficit, and say whose income absorbs it.

**Fix for all of §1.** Write the model's aggregate resource constraint, prove income =
expenditure under the stated ownership structure, and add a unit test that asserts
Walras's law at the solved equilibrium to numerical tolerance. This is a week of work
and is non-negotiable — every referee who checks the accounting (one always does) will
find these in an afternoon.

---

## 2. Theory–code contradictions (bugs the tex has absorbed)

### 2.1 Mechanized agriculture loses its efficiency gain in domestic aggregation

The adoption cutoff `φ̆` is derived from the benefit term
`B = [(ξ c/c̆)^{σ−1} − 1]^{1/(1−σ)}`, i.e., adopters produce with effective productivity
`ξφ` **in all markets**. But the domestic supply aggregate for adopters is
`Z̆ = A f · I(φ̆, κ)^{1/(σ−1)}` with **no ξ** (model.tex productivity-aggregates block;
`trade.py:202-203`), while the export aggregate `Z̃` does include ξ. So adopters pay the
full adoption fixed cost, are selected on a cutoff that assumes the ξ gain domestically,
and are then aggregated into the domestic price index and revenues *without* it. Both
the price-index benefit of mechanization and mechanized revenue are understated by
`ξ^{σ−1}`. Given that agricultural mechanization is the paper's headline rural channel
(Table 2: +272 tiller-owning households; Table 4: +0.70 log points productivity), this
bug directly attenuates the mechanism the model exists to quantify.

### 2.2 The export block silently assumes exporters are adopters

For agriculture, export cost is `c̆` and the cutoff carries `χ = (c̆/c)/ξ` — i.e., every
exporter uses the mechanized technology. Nothing enforces `φ̃ ≥ φ̆`
(`trade.py:179-195`): with cheap-enough exporting or expensive-enough adoption, the model
happily creates "mechanized exporters" below the adoption cutoff who never paid `F̆` and
are simultaneously counted as traditional producers domestically. The joint
adoption–export decision (a genuine complementarity: exporting raises the return to
adopting) is also assumed away. Either prove the parameter restrictions under which the
ordering `φ̄ ≤ φ̆ ≤ φ̃` holds and enforce them in `checks.py`, or solve the discrete
technology–export choice correctly.

### 2.3 Migration probabilities are not invariant to utility cardinalization — and can be undefined

Migration shares are `μ_od ∝ (V̄_d · L_{d,t−1}^ι · V_d / δ_od)^ν` (model.tex §2.2;
`preferences.py:111-120`). Three problems:

1. **This is not "multinomial logit in levels"; it is a Fréchet/power form**, and it is
   only well-defined for `V_d > 0`. The PIGL indirect utility
   `V = (1/η)(y/𝒫)^η − Σ v_j log P_j` is negative for `η < 0`, or for `y < 𝒫` in the
   log case — then `U^ν` is a NaN and dividing by `δ_od ≥ 1` *raises* utility. The
   current calibration avoids this by luck, not by design.
2. **Cardinalization dependence.** PIGL utility is defined up to affine transformations;
   multiplying it by amenities and congestion and raising it to the power ν makes the
   migration elasticities depend on the arbitrary cardinalization. A referee will ask:
   what is the underlying shock structure? There isn't one.
3. **No micro-foundation for ν.** With additive Gumbel shocks on `log(real income)` you
   get `μ ∝ (real income)^ν · amenities` and welfare has a closed form (the inclusive
   value). That is the standard, and PIGL is compatible with it if the amenity and
   congestion terms enter the *expenditure-function-based* real-income measure.

**Fix.** Put extreme-value shocks on additively separable (log) utility, derive the
choice probabilities and the expected-utility welfare formula, and prove positivity.
This also gives the paper its welfare metric, which currently does not exist (see §3.9).

### 2.4 Bounded-support kinks and silent solver floors

The `max{1, ·}` truncations at the Pareto bound mean the equilibrium map has kinks where
cutoffs hit 1 or κ; combined with damped log-updates that floor `π̄` and `τ̄` at
`eps = 1e−14` (`solver.py:27-35`, `equilibrium.py:222-223`), a period with negative
aggregate profits (possible: fixed costs are subtracted from `Y/σ`) gets silently
projected to `π̄ ≈ 0` and reported as "converged." At minimum, solve for `1 + π̄` (or
update π̄ in levels), and report residuals at the true fixed point, not the floored one.

---

## 3. Modeling choices that will not survive top-5 review

### 3.1 No capital, no credit — but HCI *was* capital and credit

The empirical draft itself notes manufacturing gross fixed capital formation went from
5% to 10%+ of GDP. HCI's actual instruments were directed credit at negative real rates,
tax holidays, and public capital in the complexes — not output subsidies. A model of HCI
with no capital stock and no interest-rate wedge misrepresents the policy's incidence
(who paid: savers via financial repression) and its dynamics (capital deepening vs. TFP,
the Young (1995) accumulation debate). Minimum viable fix: sector-region capital with a
rental-rate wedge `(1 + s^K)` as the policy instrument, capital accumulation with
standard time-to-build. This also gives the model a second state variable, which is
where the interesting dynamics live.

### 3.2 Myopic migration on an unevenly-spaced clock

Periods are 1965, 1968, 1973, 1975, 1980, 1985 — gaps of 3, 5, 2, 5, 5 years. Every
"per-period" parameter (migration elasticity ν, congestion ι, agglomeration ρ_j, the
population lag itself) then has no consistent time interpretation: the model implies
migration frictions were 2.5× larger per year during 1973–75 than during 1968–73.
Moreover, workers who relocated to Changwon in 1974 did so on expectations about a
multi-decade industrialization; myopic period-by-period migration understates
reallocation toward credibly-growing places and overstates churn. The standard is
annual periods with forward-looking dynamic discrete choice (Caliendo–Dvorkin–Parro
2019). If you keep myopia for tractability, you must (i) go annual, and (ii) show a
robustness exercise with perfect-foresight migration.

### 3.3 The load-bearing parameter is assumed twice

Persistence of HCI effects — the whole policy question — runs through `ρ_j`
(agglomeration in lagged population). It is hand-set (0.03/0.12/0.06) *and* Changwon is
separately handed an exogenous `A × 1.5`. The SDID production effect is thereby assumed
twice and estimated zero times. See §4.2 for the fix; here just note that a referee will
observe that any counterfactual persistence result is an artifact of these two numbers.

### 3.4 Fixed national entrant mass, no free entry

`M_{j,t}` varies by sector-time but not region (`trade.py:102`): Seoul and Rural draw
from identical entrant pools regardless of a 7-fold population difference, so all
scale effects are forced through `L^{ρ_j}`. Either make potential entrants proportional
to local population/labor (Chaney-style with a stated ownership structure) or add free
entry with a sunk cost. Also state who owns the firms: the current rebate — aggregate
profits distributed *in proportion to wage income* (`π̄ = Π/W`) — is a strong and
distributionally loaded assumption that mutes exactly the local-income channels
(park profits enriching park regions) the paper is about.

### 3.5 Agriculture as Melitz monopolistic competition

Millions of rice farmers earning a σ/(σ−1) markup on differentiated varieties is hard to
defend; it also distorts subsidy pass-through and the adoption calculus. The literature
standard is competitive, homogeneous-good agriculture with heterogeneous land quality
(Sotelo 2020) — heterogeneity in land, not in monopoly power, should drive selective
mechanization. At minimum, justify the market structure or show robustness.

### 3.6 One σ for everything; services traded like steel

A single elasticity of substitution governs substitution across rice varieties, across
machine-tool suppliers, and across "service varieties" imported from abroad through the
same `τ̃` import channel. The README even describes services as "mostly non-traded"
while the model trades them with the same friction matrix. Sector-specific `σ_j` and
(near-)non-traded services are one afternoon of work and remove an easy referee kill.

### 3.7 τ̃ does double duty

`tautilde[t, j, :]` is simultaneously the import friction into region d
(`trade.py:224`) and the export friction out of region o (`trade.py:240`). Inbound and
outbound port frictions are conceptually different objects (and were asymmetric in
1970s Korea — export promotion literally subsidized outbound logistics). Separate them.

### 3.8 Closed, constant population with homogeneous agents

Korea's population grew ~35% over 1965–85 and the farm household population halved; the
paper's own Table 8 shows retention effects concentrated in prime working-age cohorts.
A fixed-total, homogeneous-agent migration block cannot speak to cohort selection or to
the demographic component of urbanization it will be asked about. Overlapping cohorts
with age-specific migration costs (young people move; the old don't) is the natural
extension and would let Table 8 become an estimation target instead of a limitation.

### 3.9 There is no welfare metric

The primer never defines welfare. For a policy paper this is the entire point. With
extreme-value migration shocks (§2.3) you get expected utility by origin; with PIGL you
must be careful that welfare comparisons use the expenditure function (money-metric at
which prices?). Deriving the exact welfare formula — aggregate and by origin region ×
initial income — should be a proposition in the paper, because *distributional incidence
(rural vs. urban, landowner vs. worker) is the paper's comparative advantage* over
aggregate HCI evaluations like Lane (2025).

### 3.10 No existence, uniqueness, or multiplicity discussion

Lagged agglomeration cleverly removes within-period increasing returns, but the static
system still combines IO linkages, selection cutoffs with kinks, and non-homothetic
demand. Nothing is said about existence or uniqueness (cf. Allen–Arkolakis–Li
conditions), and the dynamic system with `ρ_j > 0` can have path multiplicity — which
is not a nuisance but *the economics of big-push policy*. A top-5 version confronts
this: characterize when temporary policy shifts the economy across basins of attraction
(this is the Choi–Levchenko question, and your model is built to answer it).

---

## 4. The model does not digest its own empirical context

This is where the current draft is furthest from the frontier, and also where the
biggest payoff sits, because the empirical draft contains unusually good identifying
variation that the model wastes.

### 4.1 Channel 3 hard-codes the results it should generate

The calibration (model_update.md §4.3) imposes `A_Agri` +10%/period and `β_Agri`
+0.02/period "to match" the +0.70 productivity and −0.61 labor-intensity estimates —
*while the model contains an endogenous mechanization margin (`F̆`, `φ̆`) built for
exactly this purpose*. Roads should lower trade costs → raise `S_o` and lower effective
adoption costs → move `φ̆` → raise adoption, productivity, and land intensity
endogenously. Then Tables 2 and 4 are equilibrium outcomes to match, not inputs. As
written, the counterfactual "agricultural modernization channel" is a hand-drawn
productivity path with model wallpaper; a referee will say the conclusion was typed into
the input deck. Same criticism, slightly weaker, for the imposed factor-share drift.

### 4.2 Parks: validate against the SDID instead of assuming it

Giving Changwon `A × 1.5` assumes the SDID production effect. The publishable version
inverts this: model parks as what they physically were — entry-cost reductions,
subsidies (credit wedges, §3.1), site infrastructure, port access — estimate `ρ_j`, and
ask whether the model *reproduces* the SDID event-study profile (magnitude ~2.5–3 log
points of production over 10 years, employment co-movement, the 1979-cohort washout)
as an **untargeted** or targeted moment. If an estimated agglomeration elasticity plus
measured policy inputs can generate the observed event study, that is a headline result.
If it cannot without an exogenous TFP residual, that decomposition (how much of the park
effect is agglomeration vs. direct productivity) is *also* a headline result.

### 4.3 Five regions cannot express the paper's best fact

The sign reversal of market-access effects by industrial-park distance (non-farm
population coefficient from −1.81 in decile 1 to +0.63 in decile 10; Figure 8) is the
draft's most distinctive finding, and the mechanism — labor-demand pull near parks vs.
local productivity/service growth far from them — is precisely what a spatial GE model
exists to rationalize. A 5-region toy cannot produce a decile gradient. The model needs
county-level geography (≈160–183 units; QSE routinely handles thousands —
Donaldson–Hornbeck run 2,000+), with `τ_od` built from the digitized road network at
each date (the data exist: the draft's Figures 4–5) and parks located where they
actually were. Then equation (2)/(4) of the paper can be run *on model-generated data*
and compared coefficient-for-coefficient, including the interaction and the decile plot.

### 4.4 Elasticity and measurement misalignment

The empirical MA measure imposes trade elasticity θ = 1 on travel times; the model's
bilateral trade elasticity with respect to τ is σ − 1. If the model is estimated by
matching MA regressions, the regressor must be the *model-consistent* market access (or
the model must be simulated and the paper's exact estimator applied — indirect
inference, which sidesteps the inconsistency). Relatedly: the SDID cohort ATTs are in
current-price MMS units during a decade of 15–25% inflation; when the model is compared
to them, use the log specifications (which the draft also reports) and deflate.

### 4.5 Rich data the calibration ignores

- **Origin–destination migration flows** (Statistics Korea, draft Figure 2A): directly
  estimate ν and the δ_od matrix by gravity instead of asserting them.
- **MMS microdata**: firm-size distribution → θ and κ (currently free parameters with
  no discipline; κ especially is pure numerology now); exporter shares/premia → `F̃`.
- **Actual trade data**: Korea's exports/GDP rose roughly from ~9% (1965) to ~35%
  (1985); the calibrated `D̃ × 1.15` is an order of magnitude too timid, and export
  demand growth is a first-order confounder for the parks (Changwon's growth = park +
  world demand for machinery). Discipline `D̃_{j,t}` with world import demand by sector.
- **National accounts paths**: agriculture/manufacturing/services shares 1960–85
  (draft Figure 1), urbanization, farm population — these should be *fit*, with the
  model estimated, not eyeballed ("directional").

### 4.6 An aggregate implication that will draw fire

The README reports the policy package raises the 1985 heavy-manufacturing share by
+12.7pp — i.e., essentially the entire observed 15pp structural shift is attributed to
HCI policy. That contradicts the modern quasi-experimental literature (Lane 2025 finds
large but far-from-total effects) and the older accumulation/export-orientation
consensus. Either the calibration is overshooting (likely: the A×1.5 plus subsidies plus
demand shift stack) or the model is missing the no-policy counterfactual's own growth
engine (capital deepening, world demand). A top-5 referee will run exactly this sanity
check.

---

## 5. Roadmap: the paper this could be

**Thesis worth publishing.** "Industrial parks and roads were complements: parks created
the demand pull, roads propagated it — pulling labor out of nearby townships while
raising productivity, mechanization, and service income in remote ones. We identify the
model's agglomeration, migration, and adoption elasticities from the SDID and
market-access quasi-experiments, and use the estimated model to compute the aggregate
and distributional welfare effects of HCI's spatial design — including whether the same
budget, allocated differently across space, would have industrialized Korea faster or
shared the gains more widely."

Phased plan, ordered so each phase is independently useful:

**Phase 1 — Make the economy an economy (2–4 weeks).**
Close all §1 leaks (land rents to landowners — start with local ownership, robustness
to absentee; fixed costs in labor; consistent subsidy accounting; infrastructure buys
construction; explicit numeraire and trade-deficit treatment). Fix §2.1–2.2. Add a
Walras's-law unit test and a cutoff-ordering check. Re-derive migration from Gumbel
shocks and prove positivity (§2.3); define welfare (§3.9).

**Phase 2 — Re-specify the vulnerable blocks (1–2 months).**
Annual periods; forward-looking (or robustness-checked myopic) migration; capital with
credit-subsidy wedges as the HCI instrument; sector-specific σ_j with quasi-non-traded
services; landownership and land in utility (housing) so congestion is priced rather
than reduced-form; entrant mass proportional to population or free entry; separate
inbound/outbound port frictions.

**Phase 3 — Scale the geography and invert (1–2 months).**
County-level (~160 units) with τ_od from the digitized road network by year, parks where
and when they opened, township-level aggregation for rural outcomes. Use the standard
QSE inversion: given observed populations, wages, and sectoral employment, back out
amenities `V̄` and productivities `A` exactly in the baseline year; let policy and
estimated elasticities move them thereafter. This replaces the current hand-set
exogenous paths and is what turns a simulation into quantification.

**Phase 4 — Estimate, don't calibrate directionally (2–3 months).**
Externally set σ_j (trade literature or tariff variation), θ/κ from the MMS firm-size
distribution, gravity-estimate ν and δ from O–D flows. Then estimate the crucial vector
(ρ_j, ι, η, v_j, adoption-cost level/elasticity) by indirect inference: simulate the
model, apply the paper's *own estimators* (SDID event study; MA first-difference
regressions including the IP-distance interaction; cohort retention if Phase 2 adds age
structure), and match coefficients. Report which moment identifies which parameter
(Andrews–Gentzkow–Shapiro sensitivity). Hold out at least one quasi-experimental moment
(e.g., the Figure 8 decile gradient, or the 1979 cohort washout) as untargeted
validation — this is what separates the top-5 version from a calibrated simulation.

**Phase 5 — Counterfactuals that answer questions (1–2 months).**
1. *Decomposition*: parks only, roads only, both — quantify the complementarity the
   empirical sign-reversal suggests. This is the paper's novel object; nobody has it.
2. *Incidence*: welfare by origin region × worker/landowner, and by income level (the
   PIGL machinery finally earns its keep: cheap manufactures matter more to the poor,
   food prices cut the other way). "Who paid for the miracle and who received it."
3. *Persistence / big push*: remove all policy after 1979 (as in fact happened) — does
   the estimated ρ_j sustain Changwon? Map the threshold. Connects to Choi–Levchenko.
4. *Spatial misallocation*: reallocate the same fiscal envelope (e.g., parks in the
   Jeolla southwest, or all-roads-no-parks) — was the Gyeongbu-corridor concentration
   efficient, and at what equity cost?

**Phase 6 — Rewrite model.tex as a model section.**
The current document is an honest code memo, and it reads like one: "the implemented
indirect utility is…", "the code sets…", "is implemented as". A paper model section
runs: primitives → preferences with the shock structure stated → technology → market
structure → definition of equilibrium (formal, complete) → propositions (existence;
cutoff ordering; welfare formula) with proofs and all cutoff derivations in an appendix.
Every equation currently asserted (e.g., the `σ^{1/(σ−1)}` factor in the cutoffs) must
be derived. Keep the primer as replication documentation; do not submit it.

---

## 6. Literature the paper must position against

*Korea and industrial policy:* Lane (2025 QJE) — HCI, linkages, persistence; Kim, Lee &
Shin (2021) — plant-level HCI, output gains alongside misallocation; Choi & Levchenko —
temporary subsidies, permanent effects via dynamic scale economies; Liu (2019 QJE) —
targeting in production networks; Bartelme, Costinot, Donaldson & Rodríguez-Clare —
estimating external economies for optimal industrial policy; Rodrik (1995); Westphal
(1990); Young (1995) — accumulation vs. TFP; Connolly & Yi (2015 AEJ:Macro) — how much
of Korean growth was trade policy; Uy, Yi & Zhang (2013 JME) — structural change in
open-economy Korea.

*Quantitative spatial:* Ahlfeldt, Redding, Sturm & Wolf (2015); Redding (2016); Monte,
Redding & Rossi-Hansberg (2018); Caliendo, Dvorkin & Parro (2019); Allen & Arkolakis
(2014); Redding & Rossi-Hansberg (2017, survey).

*Roads and market access:* Donaldson & Hornbeck (2016); Faber (2014 ReStud) — note his
finding that highway connection can *hurt* peripheral counties is the mirror image of
the draft's D1 result and belongs in the framing; Asher & Novosad (2020); Morten &
Oliveira.

*Structural transformation and agriculture:* Boppart (2014 ECMA) — the PIGL system used
here, cite it and inherit its regularity conditions; Comin, Lashkari & Mestieri (2021) —
the leading alternative; Eckert & Peters — spatial structural change; Fan, Peters &
Zilibotti (2023 ECMA); Bustos, Caprettini & Ponticelli (2016 AER) — ag technology →
industrialization, the closest mechanism paper; Sotelo (2020 JPE) — competitive spatial
agriculture; Gollin, Lagakos & Waugh (2014).

*Firm heterogeneity:* Melitz (2003); Chaney (2008) — the fixed-entrant-mass structure
actually used here should be attributed to Chaney, not Melitz.

---

## 7. Minor and expositional issues in model.tex

1. `\R = 𝒩` for the region *set* invites confusion with ℕ; `\E` is defined and never
   used; title page has empty author and a "primer" title — none of this survives to a
   submission.
2. "Migration shares are multinomial-logit in levels" — wrong name; it is a power
   (Fréchet-type) share. Terminology matters to referees.
3. State the parameter restrictions under which PIGL shares lie in [0,1] over the
   equilibrium income range (Boppart's conditions), and the sign conventions (η > 0,
   v_agri > 0) that deliver Engel's law; `η ∈ ℝ` unrestricted is not enough.
4. `ι ∈ (−1,0)` hard-codes congestion; with land/housing in utility (§3.9 fix) this
   parameter becomes estimable rather than assumed negative.
5. Timing within a period is never stated (workers migrate on current-period prices,
   then produce and consume in the destination; congestion is lagged but the labor
   market clears with current L). Write the timeline.
6. The equilibrium definition (§7 of the tex) references "the equations in Section 2/3/4"
   — a formal definition must be self-contained.
7. The demand shifter `S_o` uses total expenditure `E_dj` (final + intermediate) — fine
   (roundabout production), but say so; as written it looks like final demand.
8. `max{1,·}` truncations: state what happens economically when the bound binds (all
   potential firms active; zero-cutoff-profit fails) — currently silent.
9. Fixed costs' units (numeraire? labor?) are never stated — see §1.2.
10. Document that `p̃_j` is the numeraire (or choose one), and that `L_0` sums to 1 means
    all "populations" are shares — then wages are per-share, and comparisons to won
    values in the empirical tables need an explicit bridge.

---

## Summary of severity

| # | Issue | Severity | Fix cost |
|---|-------|----------|----------|
| 1.1–1.5 | Walras's law failures (rents, fixed costs, subsidies, infra, trade) | Fatal | Low–medium |
| 2.1 | ξ missing from domestic mechanized aggregation | Fatal (headline channel biased) | Trivial |
| 2.2 | Exporter/adopter cutoff ordering unenforced | High | Low |
| 2.3 | Migration cardinalization / negative utility | Fatal for welfare | Medium |
| 3.1 | No capital/credit | High (wrong policy instrument) | High |
| 3.2 | Uneven periods + myopia | High | Medium |
| 3.3 | ρ assumed, A×1.5 assumed | Fatal for counterfactual credibility | Medium (with Phase 4) |
| 4.1–4.2 | Calibration hard-codes empirical findings | Fatal ("assumes conclusion") | Medium |
| 4.3 | 5 regions vs. decile gradient | High | High |
| 4.4–4.6 | Elasticity misalignment; wasted data; overshooting aggregate | High | Medium |
| 6, 7 | Positioning and exposition | Standard | Low |

The chassis is right and the empirical draft supplies identifying variation most
structural papers can only dream about. The distance to a top-5 paper is not the model's
ingredient list — it is (i) an economy that adds up, (ii) elasticities estimated from
the paper's own quasi-experiments instead of typed in, and (iii) counterfactuals that
exploit the one thing this setup can do that neither the reduced-form paper nor the
existing HCI literature can: price the park–road complementarity and its distributional
incidence.
