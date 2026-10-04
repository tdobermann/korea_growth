# A Fresh Look at the Model: What It Needs to Tell the Macro Story

**Question this memo answers.** The project's stated goal is now the *macro* story: how Korea
escaped poverty between 1960 and 1990, and through which mechanisms — industrial parks, roads,
rural transformation, and the rest. What does the model need to become to tell that story, and
what should the township panel being digitised (population and employment, agriculture,
municipal finance, infrastructure, schools; annual, 1960–1990) do inside it?

It complements [`model_review.md`](model_review.md) (referee report), [`../status.md`](../status.md)
(roadmap) and [`research_agenda.md`](research_agenda.md) (paper portfolio). Diagnostics in §2
are reproducible with `python scripts/macro_scorecard.py`.

_Written 2026-09-29. Revised 2026-10-03 after the referee report
[`review_fresh_look.md`](review_fresh_look.md). The revision refreshes the §2 numbers after the
nested entry–adoption–export choice and the measurement fixes, adds an identification caveat to
§3.1, restates "Matsuyama in space" as a model-generated prediction (§3.4), re-specifies the
reservoir design (§4), adds a novelty section (§3.7), and moves the agriculture block to the
front of the build (§7)._

---

## 0. Bottom line

The model was built to answer "did HCI's spatial policies reach the countryside?" by
perturbing a calibrated economy. The macro question needs something different: a model
whose **baseline is the historical growth path**, so that mechanisms can be *subtracted from
history* rather than added to a stationary economy. Running the current code against that
standard turns up five problems (§2). Four of them are new relative to the earlier review.

1. **The equilibrium was indeterminate.** The trade closure (`transfer = IM − EX`) admitted a
   continuum of equilibria. From different initial guesses the solver converged, to residual
   ~1e-12, to wage levels that differ by 65%, trade deficits of 37–67% of absorption, and mean
   real income that differs 3.6×. Every reported number was a point the solver happened to
   pick. **Fixed in this commit:** net exports are now pinned exogenously (default: balanced
   trade), a regression test checks that the solution does not depend on the initial guess,
   and the README numbers are refreshed.
2. **The calibrated 1965 economy was not Korea on any macro margin** (items 2–3 describe the
   3-sector economy; the history-calibrated baseline of §2.6 now reproduces the 1965–85
   transformation in farm employment, manufacturing, growth, exports and urbanisation). Exports are 73% of GDP
   (data: ~9%). Agriculture has 11% of employment counted in workers (data: ~59%): food
   imports supply 58% of food spending. More than half the population leaves the "Rural"
   region in the first period, and rural real income is 18% *above* urban.
3. **There is no growth engine.** Baseline real GDP per capita (double-deflated) rises 12%
   over 1965–85 (the data: roughly fourfold). The HCI package supplies about two-thirds of all
   the growth the model has, so by construction policy explains most of what moves.
4. **The mechanisation and export margins were not nested and are still at a corner.** The
   cutoffs were computed one margin at a time, and at the calibrated parameters φ̃ < φ̆ < φ̄
   everywhere, so farms exported or mechanised without entering. **Fixed:** the cutoffs come
   from a nested choice, and the agricultural margin is recalibrated (§2.4). Mechanisation is
   now mainly labour-saving (ξ = 1.2), fixed costs are in labour units, and farm foreign demand
   and the adoption cost hit a 1965 traditional output share of 0.97. That share falls to 0.956
   by 1985 in the baseline and to 0.931 with HCI. Diffusion is slow because baseline wages
   barely grow (item 3).
5. **The headline effects were artifacts of the closure.** With a determinate closure, the
   1985 effect on the heavy-manufacturing *gross-output* share is +0.104, not +0.057. With the
   nested choice it is +0.095. After the agricultural recalibration it is +0.103 (value-added
   share +0.088, employment share +0.092). The
   pre-accounting-fix code gave +0.127 and was itself guess-invariant, so the accounting fixes
   lowered the effect by about 0.02. The fall to +0.057 was the indeterminate closure picking
   a point (§2.1).

**Recommendation.** Re-architect around five principles (§3):

| # | Principle | Replaces |
|---|---|---|
| 1 | **Baseline = history.** Use an annual clock (1962–90). Each year, invert the fundamentals so the model reproduces the observed township and county panel, once identification of the inversion is demonstrated (§3.1). Model the programmes as measured shocks, and decompose outcomes with Shapley values. | Hand-set exogenous paths; six unevenly spaced periods; "policy − baseline" deltas |
| 2 | **Simplify production.** Use CES gravity (Armington or Eaton–Kortum) with sector-specific external economies on employment density. | Melitz–Chaney in every sector, with un-nested cutoffs |
| 3 | **Put people in sectors.** Nest the occupation choice, including non-employment, inside the location choice. | A single regional wage; no farm/non-farm distinction; no non-participation |
| 4 | **Put agriculture on observed land.** Competitive farm households on paddy and dry fields, with observed farm-size classes, irrigation, HYV rice, and a farm-size threshold for mechanisation driven by w / p_machine. | Monopolistically competitive "farms" with a fixed-cost adoption margin |
| 5 | **Include the growth engines the story cannot omit.** Capital, with HCI credit wedges and foreign saving; schooling; demography; world demand. Report poverty and welfare as solver outputs. | Output subsidies as the only HCI instrument; fixed population; no welfare output |

**Build order.** Start small: a spatial model with agriculture, non-farm production, land, goods
trade and labour mobility, together with the reservoir event studies (§4), comes before the
growth-engine blocks (§7).

Keep the current model's strengths: PIGL demand (the food problem and services), input–output
linkages (HCI → cheaper machinery and fertiliser → farm modernisation, the most interesting
macro linkage already in the code), local land ownership, government spending that buys
output, and Gumbel migration with its welfare formula.

---

## 1. What the macro story asks of a model

### 1.1 Facts the model must *generate*, not assume

These are order-of-magnitude values for orientation; each needs to be replaced from source.
The scorecard uses a subset of them.

| Margin | ~1960/65 | ~1985/90 | Source to use |
|---|---|---|---|
| Real GDP per capita | 1 | ×~4 by 1985, ×~6–7 by 1990 (≈7%/yr) | Maddison / PWT |
| Agriculture share of employment | 63% (1963), 59% (1965) | 25% (1985), 18% (1990) | EAPS |
| Urban population share | 28% (1960) | 65% (1985), 74% (1990) | WDI; draft §1 |
| Farm household population | ~14m | <6m | draft Fig. 2C |
| Population | 25m (1960) | 43m (1990) | Census |
| Exports / GDP | ~3% (1960), ~9% (1965) | ~30–35% | BoK national accounts |
| Exports (US$) | $100m passed in 1964 | $1bn in 1970, $10bn in 1977 | trade statistics |
| Investment / GDP | ~10–15% | ~30% | BoK; foreign saving financed a large share in the 1960s–70s |
| Schooling | middle-school enrolment well under half (mid-1960s) | near-universal by ~1980; high school ~90% by 1990 | KEDI (verify) |
| Fertility (TFR) | ~6 | ~1.6 | vital statistics |
| Rural electrification | roughly 1 in 8 rural households (mid-1960s) | near-universal by ~1979 | KEPCO (verify) |
| Power tillers per farm household | ≈0 | substantial by the mid-1980s | agricultural statistics |
| Rural / urban household income | gap opens late 1960s, near parity mid-1970s, reopens | — | Farm Household Economy Survey vs Urban Household Survey (verify; flagged in research_agenda §6) |
| Absolute poverty | roughly two-fifths (mid-1960s) | around a tenth (1980) | KDI / Suh estimates (verify) |

### 1.2 The mechanism chain, and what each link needs

```
world demand ── light-mfg exports (1960s) ─┐
HCI credit + industrial parks (1970s) ─────┴─► urban/industrial labour demand
                                                      │
roads (Gyeongbu 1970; local paving; bridges) ─► lower goods and migration costs
                                                      │
        ┌──────────────── rural labour ───────────────┴───────────────┐
   PULL: industrial jobs                         PUSH: land-augmenting ag technology
   (migration, local non-farm jobs)              (irrigation/reservoirs, Tongil HYV, fertiliser)
        └─► rising rural wages + cheaper machines (HCI) ─► labour-saving mechanisation
                                                      │
rural non-farm economy (commerce, services, construction), electrification, schooling
                                                      │
aggregation: capital accumulation, demography, world prices ─► GDP, structural change, poverty
```

Each arrow needs four things: a model block, a **measured** shock, an **identified**
elasticity, and an aggregate counterfactual that switches it off. §4 and §5 build that table.

### 1.3 The identification logic: from township variation to macro numbers

The township and county designs (SDID, event studies with township and year fixed effects)
identify **relative** effects. The year effects absorb national general-equilibrium
responses — national prices, food prices, migration to cities, fiscal cost — which is exactly
the part the macro story is about (the "missing intercept": Nakamura–Steinsson 2018;
Adão–Arkolakis–Esposito 2019; Buera–Kaboski–Townsend 2023). The model's job is to

- be **estimated so that it reproduces the relative effects**, by running the paper's own
  estimators on model-generated data (indirect inference), and
- **supply the intercept** through general equilibrium.

Parameters that relative variation cannot identify must come from national time series or
the literature, with explicit sensitivity reporting (Andrews–Gentzkow–Shapiro 2017). Examples
are the aggregate trade elasticity against the rest of the world, the national saving
response, and economy-wide labour supply.

---

## 2. What the current model actually does

The numbers are from the 5-region policy simulation. §2.1 uses the pre-fix code (commit
`bce51c7`). Everything else uses the fixed closure, the nested entry–adoption–export choice
(§2.4) and the corrected measurement (employment in workers; double-deflated real GDP).
Reproduce with `scripts/macro_scorecard.py`.

### 2.1 The equilibrium was indeterminate (fixed here)

**Why.** Aggregate household income plus goods-market clearing already imply that the net
foreign transfer satisfies T = IM − EX at any fixed point. Setting `T = IM − EX` from the
current guess therefore replaced an equilibrium condition with an identity. In a small open
economy with a foreign numeraire, the missing condition is external balance, which pins
domestic prices relative to foreign ones (the real exchange rate). The system was one equation
short, which leaves a one-dimensional continuum of equilibria indexed by the trade deficit.

A one-good example makes the point. With domestic expenditure share d(w), the market-clearing condition
d(w)E + X(w) = wL and the budget E = wL + T with T = (1 − d)E − X are the *same* equation, so
every w is an equilibrium.

**Evidence.** Static equilibrium at t = 0 of the policy-simulation baseline, solved from
initial guesses scaled by k, with residuals below 1e-11 in every case:

| guess × k | 0.5 | 0.8 | 1.0 (default) | 1.25 | 2.0 | **NX pinned at 0** (any k) |
|---|---|---|---|---|---|---|
| w_Seoul | 0.291 | 0.339 | 0.367 | 0.399 | 0.480 | 0.253 |
| (EX − IM) / absorption | −0.37 | −0.52 | −0.56 | −0.60 | −0.67 | 0.00 |
| mean real income | 0.96 | 1.56 | 1.92 | 2.33 | 3.50 | 0.42 |

At the default guess, imports were 2.3× GDP. The Walras, resource and budget tests passed
along the whole continuum: accounting identities cannot detect indeterminacy.

**Fix.** `ModelExogenousPaths.nx_gdp` (shape (T,), default `None`, meaning balanced trade)
sets T = −NX\*, with NX\* = nx_gdp · GDP. EX − IM = NX\* is now a genuine equilibrium condition,
reported as `aggregates["nx_residual"]`. The solution is invariant to the guess (the scorecard
reports a relative wage difference of 3e-13), and two new tests guard this. Korea's observed
current-account deficits, which were large in the 1960s–70s, can now be fed in directly.

**Consequences for the headline numbers** (1985, policy − baseline). National sector
shares in the first three rows are *gross-output* shares (`aggregate_output_shares`), which
include intermediate sales. Value-added and employment shares are reported separately below.

| moment | old closure (README before) | determinate closure | + nested choice | + ag recalibration (now) |
|---|---|---|---|---|
| aggregate agriculture share | −0.041 | −0.045 | −0.040 | −0.005 |
| aggregate heavy-mfg share | +0.057 | **+0.104** | **+0.095** | **+0.103** |
| aggregate services share | −0.016 | **−0.060** | −0.055 | −0.098 |
| Changwon wage | +0.144 | +0.120 | +0.122 | +0.087 |
| Changwon mfg share | +0.229 | +0.287 | +0.274 | +0.287 |
| Seoul population share | −0.026 | −0.029 | −0.030 | −0.033 |
| Rural population share | +0.033 | +0.025 | +0.027 | +0.031 |
| Rural income per capita | +0.199 | +0.171 | +0.174 | +0.121 |
| Rural / Daegu services share | +0.106 / +0.106 | +0.094 / +0.081 | +0.110 / +0.093 | +0.064 / +0.065 |

With the nested choice, the 1985 heavy-manufacturing effect was +0.095 on the gross-output
share (+0.083 value added, +0.089 employment); the nesting accounts for essentially all of
the move from +0.104. After the agricultural recalibration (§2.4) it is +0.103 / +0.088 /
+0.092. The agriculture-share effect almost vanishes, because farming is now small and
inward-looking: farm output no longer depends on exports, and food imports absorb the demand
side. Switching the migration index to
the exact PIGL equivalent income moves it by less than 10⁻⁵. All directional tests still
pass.

**The +0.127 → +0.057 claim, checked.** The pre-accounting-fix code (`cdafe29`) reproduces
+0.127. Its equilibrium is guess-invariant (relative wage difference 3 × 10⁻¹⁴): it had no
foreign transfer, and because land rents and fixed costs leaked out of household income,
it was determinate but ran an implied trade surplus of about 27% of gross output. It therefore
cannot be rerun "with `nx_gdp = 0`". The comparable sequence is +0.127 (old accounts,
determinate) → +0.104 (corrected accounts, balanced trade). The accounting corrections lower
the effect by about 0.02. The remaining fall to +0.057 (0.047 of the 0.070 drop) was the
indeterminate closure's selection.

**Sensitivity to the trade-balance default** (from the referee report): an exogenous deficit
of 5% or 10% of GDP moves the effect to +0.102 or +0.100. The insensitivity is itself a
symptom. When exports are 80–95% of GDP, a 10-point swing in the deficit barely moves the real
exchange rate.
In an economy with Korea's 9% export share the closure would matter far more.

**Sensitivity to the export demand elasticity.** External balance now pins the wage level
through the elasticity of foreign demand for Korean exports. That elasticity is now a separate
parameter, `sigma_x` (default σ = 4), and the headline depends on it heavily:

| `sigma_x` | 2 | 4 (default) | 6 |
|---|---|---|---|
| 1985 heavy-mfg gross-output share effect | +0.021 | +0.103 | +0.137 |
| 1985 heavy-mfg employment share effect | +0.017 | +0.092 | +0.117 |

(Current calibration. σ_x = 6 needs solver damping 0.1; the default 0.25 cycles at t = 1.)

With a low aggregate elasticity, the export expansion that HCI induces depresses its own terms
of trade and the reallocation is small. `sigma_x` must be calibrated externally (§1.3), and
the headline reported with its sensitivity to it.

### 2.2 The calibrated 1965 economy is not Korea

| 1965 | model | data |
|---|---|---|
| Exports / GDP (= imports / GDP under balanced trade) | 0.73 (0.82 before the ag recalibration, 0.95 before the nested choice) | ~0.09 / ~0.16 |
| Agriculture share of employment (workers) | 0.11 (0.25 before the ag recalibration) | ~0.59 |
| Agriculture share of value added | 0.12 (0.31 before) | ~0.38 |
| Food imports / food expenditure | 0.58 | small (grain imports were mainly aid-financed; verify) |
| Share outside "Rural" | 0.82 (L0 = 0.45; Rural falls from 0.55 to 0.18 within the first period) | ~0.32 urban |
| Rural / urban equivalent income | 1.18 | < 1 |
| Farm output share of traditional (non-mechanised) technology | 0.97 (calibrated; 0.00 before) | ~1 |

*Measurement.* Employment counts workers: (variable + fixed-cost labour payments) / local
wage, which sums to population. The earlier scorecard summed variable labour *payments*. It
left out fixed-cost labour and over-weighted high-wage regions. On the pre-nesting code it gave
23.5% for 1965 against 28.0% in workers. Real GDP is a chained Fisher double-deflated index
(region–sector producer prices for output, local purchaser prices for intermediates). GDP over
a consumption deflator, which the scorecard used before, is a purchasing-power measure. It is
now reported separately as real consumption per capita.

Why this matters for the macro story, beyond fit:

- **The economy is in the wrong regime.** With 95% openness, food is imported and there is no
  food problem, so the agricultural labour share is set by comparative advantage. The food
  problem (Gollin–Parente–Rogerson 2007) is switched off. In
  Matsuyama's (1992) terms the model sits in the *open-economy* case, where
  agricultural-productivity growth *retards* industrialisation — the opposite sign to the
  closed-economy case the Korean narrative usually assumes. Which regime a township is in is
  a substantive question that roads change (§3.4). It should not be set by accident of
  calibration.
- **The rural premium has the wrong sign.** Migration equalises utility including amenities
  (Rural 0.85, Seoul 1.18), so model rural residents must be *richer* than urban ones. As
  calibrated, "escaping rural poverty" cannot even be posed.
- **Urbanisation is a period-one jump.** It is a disequilibrium adjustment from L0, not the
  1965–85 process.

The fix is not re-tuning. It is inversion (§3.1), plus targeting observed import shares by
sector.

### 2.3 There is no growth engine

| 1965 → 1985 | baseline | HCI package | data |
|---|---|---|---|
| real GDP per capita (double-deflated) | ×1.118 | ×1.377 | ×~4 |
| real consumption per capita | ×1.104 | ×1.405 | — |
| agriculture share of employment, workers (pp) | −1.0 | −1.1 | −34 |
| traditional share of farm output | 0.970 → 0.956 | 0.970 → 0.931 | ~1 → well below 1 |

The baseline generates under a tenth of the observed log growth. Adding the full HCI package
brings it to under a quarter, so policy accounts for roughly two-thirds of all the growth the
model has. Every policy effect is measured against a Korea that does not grow. As a result, PIGL
Engel effects, the value of mechanising, and the wage path that drives migration are all
evaluated at 1965 income levels. The review's worry (§4.6) that HCI is over-credited is
structural, not a calibration detail.

### 2.4 The mechanisation and export margins were not nested (fixed) and are at a corner (not fixed)

Each cutoff was computed from its own zero-profit condition, and the cutoffs were never nested.
Firms therefore exported or mechanised without paying the entry cost whenever that secondary
margin was more attractive than entry, although a firm must be active before it can export or
adopt. At the calibrated parameters this was the normal state:

| Agriculture, Rural region (pairwise cutoffs, before) | 1965 | 1985 |
|---|---|---|
| entry φ̄ / adoption φ̆ / export φ̃ | 2.80 / 1.91 / 1.50 | 2.89 / 1.91 / 1.52 |
| traditional-tech share of farm output | 0.00 | 0.00 |
| adopters ÷ active farms (national) | 5.9 | 7.7 (14.3 with policy) |
| exporters ÷ active farms (national) | 16–36 by region | same |
| share of farm output exported | 0.64 | 0.60 |

Services showed the same pattern: 56–63% of output was exported, and exporters outnumbered
active firms 3–9×. That is where the 95% export ratio came from.

**Fixed: the nested choice.** Profits under every option are linear in φ^{σ−1}, so the firm
picks the upper envelope of {exit, traditional, mechanised, mechanised exporter} (agriculture)
or {exit, domestic, exporter} (other sectors). A firm must be active to adopt or export.
Agricultural exporters use the mechanised technology, so they also adopt
(`trade.nested_cutoffs`; `model.tex` eq. `nested`). The fixed-cost bill is now consistent:
every exporter and adopter also pays F.

**The calibration corner (now recalibrated).** With the earlier F̆ and F̃, the marginal
entrant preferred to mechanise and export, so all three cutoffs coincided:

| Agriculture, Rural region (nested, now) | 1965 | 1985 | 1985, HCI |
|---|---|---|---|
| entry = adoption = export cutoff | 2.04 | 2.05 | 1.96 |
| adopters ÷ active farms; exporters ÷ active farms | 1 ; 1 | 1 ; 1 | 1 ; 1 |
| traditional-tech share of farm output | 0.00 | 0.00 | 0.00 |
| share of farm output exported | 0.55 | 0.52 | 0.43 |

Services: every active firm exports, and 48–55% of output is exported. Channel 3 (cutting F̆)
acted on real farms but could not produce the 1965–85 diffusion of power tillers from ≈0,
because adoption was already universal in 1965.

*Why.* A traditional segment needs F̆/F > Δ and (F̆ + F̃)/F > Δ + a_X/a_T, where
Δ = (ξ c/c̆)^{σ−1} − 1 is the profit gain from mechanising (`model.tex` eq. `interior`). At the
old calibration Δ = 0.54–0.72 against F̆/F = 0.25. Farm foreign demand (D̃ = 0.5) made the
export market worth about twice the domestic one (a_X/a_T = 1.6–2.6), and exporting requires
mechanising, so the second condition failed by a factor of 5–6. Mechanising was also a
productivity gift: at ξ = 1 it *lost* money everywhere (c/c̆ ≈ 0.8, machines being expensive
relative to wages), and only ξ = 1.5 made it pay.

*Recalibration* (`scripts/calibrate_agriculture.py`, since superseded by §2.6):
1. ξ = 1.2, close to the 1965–85 range of c̆/c (1.13–1.30). Mechanising then pays only once
   wages rise and HCI machinery gets cheaper, which is the induced-innovation channel.
2. Fixed costs are labour requirements (`fixed_costs_in_labor`), converted from the old
   numeraire values at the 1965 mean wage, so they rise with wages.
3. D̃_Agri = 0.220 and F̆_Agri = 4.28 (labour units) solve for a 1965 traditional share of
   0.97 and farm exports of 1% of farm output (both placeholders to replace with data).

| Agriculture (recalibrated) | 1965 | 1985 | 1985, HCI |
|---|---|---|---|
| traditional share of farm output | 0.970 | 0.956 | 0.931 |

The corner is gone, and HCI speeds diffusion about 2.7× through higher rural wages, cheaper
machinery and channel 3. The 1965 mechanised fringe is export-led, since mechanising for the
home market alone does not yet pay. Diffusion is slow because the baseline has almost no wage
growth (§2.3). It cannot approach the mid-1980s tiller stock until the model has a growth
engine.

*Side effects.* (i) Farm employment falls from 25% to 11% (data ~59%). Exports had been
sustaining farm output, and food imports supply 58% of domestic food spending. Protecting food
imports, as Korea's grain import controls did, is the natural next lever: doubling τ̃_Agri
cuts the food import share to 13% and raises farm employment to 23%. The 1965 calibration
would then need re-solving. (ii) Exports remain 73% of GDP, now driven by services and
manufacturing; their foreign demand needs the same treatment. The durable fix for
agriculture is still §3.4: competitive farms on observed land with a farm-size threshold.

### 2.6 History-calibrated baseline: matching the structural transformation (2026-10-04)

§2.2–2.4 describe the 3-sector economy, which could not deliver Korea's structural
transformation: there was no growth engine, food was mostly imported, and urbanisation was a
first-period jump. The baseline is now rebuilt around reproducing that transformation
(`scripts/korea_baseline.py`; the §2.4 farm calibration script is superseded).

*Structure.*
- **Rice**: protected (import controls and, from 1969, procurement), so internationally
  non-traded. It carries the mechanisation margin.
- **OtherAg**: wheat, barley, feed grains and other farm output. It competes with imports at
  world prices, so grain import dependence is an equilibrium outcome. It is not exported.
- **Manufacturing**: traded, and the export sector.
- **Services**: internationally non-traded.
- **Growth engine**: sectoral TFP growth, plus growing foreign demand for manufactures.
- **Population**: the 1965 population is made an equilibrium by inverting amenities
  (`korea_growth.inversion`), so later urbanisation is generated by the model.

*Calibration* (`scripts/calibrate_history.py`): 8 parameters are fitted to 8 targets. The
parameters are TFP growth for manufacturing and for farm and services (tied together), the PIGL
η and food shifter, the manufacturing final-demand weight, the level and growth of foreign
demand, and an urban non-farm TFP premium. The targets come from `scripts/data_targets.py`, where
each value carries its provenance. Only the manufacturing value-added shares (15% → 30%) and the
1980 urban share (57%) are sourced in the repository, through the paper draft. The rest are the
unverified §1.1 approximations.

| 1965 → 1985 | data | model | |
|---|---|---|---|
| agriculture employment share (workers) | 0.59\* → 0.25\* | 0.605 → 0.229 | targeted |
| manufacturing value-added share | 0.15 → 0.30 | 0.192 → 0.298 | targeted |
| real GDP per capita (double-deflated) | ×4\* | ×4.00 | targeted |
| exports / GDP | 0.09\* → 0.33\* | 0.078 → 0.330 | targeted |
| urban share, 1980 | 0.57 | 0.547 | targeted |
| urban share, 1985 | 0.65\* | 0.629 | untargeted |
| agriculture value-added share | 0.38\* → 0.13\* | 0.595 → 0.239 | untargeted |
| import share of other-farm demand | — | 0.095 → 0.764 | no data |
| traditional share of rice output | ~1 → <1 | 1.000 → 0.515 | no data (F̆ assumed) |

\* unverified approximation. PIGL shares stay in [0, 1] along the whole path, and the
solution is guess-invariant (5 × 10⁻¹²).

**What this establishes.** The model can generate a transformation of the observed size.
Farm employment falls 38 points through Engel effects on rising income (η = 0.39), import
competition in grains and rural–urban migration, while the economy grows fourfold and
urbanises from 0.32 to 0.63. The calibrated growth rates are 4.1%/yr for manufacturing TFP and
3.2%/yr for farm and services TFP. Foreign demand for manufactures grows 24%/yr, which with σ = 4
takes exports from 8% to 33% of GDP.

**Mechanical limits found.**
1. **Agricultural productivity gap.** With one wage per region, farm value added per worker is
   roughly equal to non-farm (rural wage 0.76 of urban in 1965). The unverified 0.38 / 0.59
   value-added / employment shares imply farm value added per worker at about 0.43 of non-farm.
   The integrated model could reach that only with a rural/urban wage ratio of about one-third.
   **Addressed in the theory (2026-10-04):** sector-specific wages through nested occupation
   choice (§2.7; `model.tex`, section "Occupation choice and sector-specific wages"). Not yet
   recalibrated.
2. **1965 manufacturing share** (0.19 vs 0.15). The manufacturing final-demand weight sits at its
   lower bound (0.02). The stylised input–output coefficients alone over-produce manufacturing,
   so they need replacing with Korean input–output tables.
3. **No relative-price channel.** PIGL with a Cobb–Douglas price aggregator moves expenditure
   shares only through real income. Farm productivity growth releases labour only through
   income and import competition, not through the Baumol channel. If the data call for it,
   non-homothetic CES (Comin–Lashkari–Mestieri) would add it.

**HCI under this baseline.** The package now *lowers* the 1985 national manufacturing share
(value added −0.013, employment −0.026) and raises services. Without the rural-services channel
the manufacturing value-added effect is −0.004; without farm modernisation it is −0.007. So the
sign comes from the baseline, not from one channel. Income gains go to non-traded services, and
manufacturing has almost no domestic final demand (limit 2). The package was tuned for the
3-sector economy and has not been re-tuned. Until the input–output structure comes from data,
read the HCI aggregate effect as unresolved, not as a finding. The directional test for it is a
strict expected failure.

**Assumptions without data** (all in `scripts/korea_baseline.py`): rice is half of food demand;
urban farm TFP is 0.4 of rural; the food asymptote α_food is 0.05; the 1965 city split is
stylised; the rice mechanisation fixed cost is not identified; services TFP growth equals farm.
`scripts/data_targets.MISSING` lists the data that would replace each one.

### 2.7 Sector-specific wages (theory, 2026-10-04)

Principle 3 (§3.3), without non-employment yet. Within each location, workers choose an
occupation (farming, manufacturing, services) with taste shocks of dispersion 1/ε, nested
inside the location choice (ν ≤ ε). Each occupation has its own wage, and b is a non-pecuniary
value of the occupation (attachment to farming, barriers to leaving it). The full derivation is
in `model.tex`: choice probabilities and inclusive value, labour-market clearing by
occupation, exact PIGL aggregation over income groups, welfare, the integrated limit, and the
wage-gap decomposition
log(Y_A/Y_N) = (1/ε) log(L_A/L_N) − log(b_A/b_N).
Rice and other crops are one occupation: they are products, not labour markets. Treating them
as two would give farming double taste mass in the logit.

*What it does in the Korea baseline.* This is an illustration, **not recalibrated**: the 1965
amenities are re-inverted for each case, and every other parameter is the integrated-market
calibration.

| case | ag emp 65 | ag VA 65 | w_farm/w_nonfarm 65 | APG 65 | ag emp 85 | ag VA 85 | w_farm/w_nonfarm 85 | APG 85 |
|---|---|---|---|---|---|---|---|---|
| integrated (ε = ∞) | 0.605 | 0.595 | 0.827 | 0.958 | 0.229 | 0.239 | 0.868 | 1.053 |
| ε = 10, b_farm = 1 | 0.561 | 0.584 | 0.951 | 1.100 | 0.219 | 0.236 | 0.905 | 1.103 |
| ε = 5, b_farm = 1 | 0.530 | 0.578 | 1.051 | 1.214 | 0.218 | 0.236 | 0.908 | 1.107 |
| ε = 5, b_farm = 1.5 | 0.627 | 0.610 | 0.802 | 0.930 | 0.314 | 0.268 | 0.676 | 0.803 |
| ε = 5, b_farm = 2 | 0.680 | 0.617 | 0.653 | 0.758 | 0.399 | 0.297 | 0.545 | 0.638 |

(APG = farm value added per worker over non-farm. The wage ratios are national,
employment-weighted, so they include the rural/urban composition.)

Three findings:
1. **b = 1 is not neutral.** It implies equal occupation shares at equal pay, so a 60% farm
   share needs a *higher* farm wage. The productivity gap needs b_farm > b_other. That is the
   economic content of a farm wedge, and the decomposition prices it.
2. **With a farm wedge, the gap appears and then widens** during the transformation (b_farm = 2:
   relative farm wage 0.65 → 0.55, APG 0.76 → 0.64). Falling farm labour demand lowers the farm
   wage faster than workers leave. The integrated model cannot produce this.
3. **The wedge also slows the transformation.** Farm employment in 1985 is 0.40 rather than 0.23
   at unchanged parameters. A recalibration would trade b_farm and ε off against the Engel
   parameters, and identifying them separately needs farm and non-farm earnings data
   (`scripts/data_targets.MISSING`).

*Extensions noted in `model.tex`:*
- Fréchet efficiency draws, i.e. selection (Lagakos–Waugh). PIGL aggregation stays closed-form
  there, and it predicts different earnings changes for sector switchers.
- Non-employment as an occupation.

### 2.5 Smaller specification issues that bite once the model grows and gets geography

- **Agglomeration depends on total lagged population** (L^{ρ_j}), not on sectoral employment
  or density. A park therefore cannot create a heavy-manufacturing cluster in a small county,
  and agriculture enjoys agglomeration from population.
- **Fixed costs are in numeraire units.** With growth, entry, exporting and adoption become
  mechanically cheaper in real terms. They should be in labour units.
- **There is one land market** for farmland, industry and housing. Farmland capitalisation and
  urban conversion near cities, which are central to rural incidence, cannot be separated.
- **Total population is fixed at 1.** Population grew ~75% between 1960 and 1990 under a
  steep fertility decline, so per-capita and aggregate effects are conflated.
- **Infrastructure spending is allocated by population**, not where roads and parks were
  built.

---

## 3. Proposed architecture

### 3.1 Principle 1 — baseline = history

- **Annual, 1962–1990** (starting after the 1962 currency reform and the First Five-Year Plan;
  1960–61 serve as pre-periods).
- **Invert each year, once the inversion is shown to be identified.** The aim is to recover
  productivities Ā_{ik,t}, amenities B_{i,t} and occupation wedges b_{ik,t} so the model
  reproduces the observed data. The data are township population and employment by sector and
  status, county manufacturing (MMS), and national aggregates. This is the standard QSE
  inversion (Allen–Arkolakis 2014; Redding–Rossi-Hansberg 2017).

  **The inversion as written is not identified.** Per township-year, the unknowns are K
  productivities, K − 1 wedges (after normalisation) and one amenity, 2K in all. The
  observables are population and K − 1 employment shares, K in all. In
  π_{k|i} ∝ (b_ik w_ik)^ε, a higher A_ik raises w_ik and hence π_{k|i} exactly as a higher b_ik
  does. Without wages, output, prices or trade flows, A and b cannot be separated. Before
  `inversion.py` is built, write down the unknowns, observables, normalisations and
  restrictions, and demonstrate identification analytically or by a numerical rank/recovery
  exercise on synthetic data. Candidate restrictions are wedges common within county or
  province, or constant over time up to a trend. Candidate additional data are county MMS
  wages and value added, provincial farm wages, and crop output and prices. Wages then become
  inversion inputs rather than validation.
- **Structural event studies.** Treat the inverted fundamentals as outcomes. Regress them, in
  event-study form, on measured programme shocks: park groundbreakings, interchange openings,
  paving, reservoir completions, electrification, school openings. The model already accounts
  for endogenous responses such as migration and prices. What remains is each programme's
  *direct* effect on productivity or amenity, which is the elasticity the counterfactual
  needs. Caveats: inverted fundamentals absorb anything the model omits. Unless capital and
  human capital are modelled (principle 5), township "productivity" is TFP times factor
  deepening. Regressions on inverted fundamentals are *not* causal policy effects by
  themselves. They need the same credible assignment design as any event study, and their
  standard errors must carry the inversion's uncertainty.
- **Exact fit is not validation.** Anything used as an inversion input (township sectoral
  employment, for instance) is fitted by construction, so its national sum cannot also
  validate the model. Holding observed capital or schooling paths fixed while removing HCI
  excludes policy effects that run through those paths. That is a *conditional* counterfactual
  and must be labelled as such. A Shapley decomposition allocates interactions consistently
  but resolves neither problem.
- **Counterfactuals subtract measured shocks** from history, holding all other fundamentals at
  their inverted values, with exact hat algebra (Dekle–Eaton–Kortum 2008;
  Caliendo–Dvorkin–Parro 2019) so that few objects must be calibrated in levels.
- **Decompose, don't difference.** Shapley values over drivers, with interactions reported
  explicitly (§6).
- **Templates.** Spatial decompositions of growth miracles in this style exist: Tombe–Zhu
  (2019) and Hao–Sun–Tombe–Zhang (2020) for China, Eckert–Peters for spatial structural change
  in the US, Budí-Ors–Pijoan-Mas for Spain's rural exodus, and Fan–Peters–Zilibotti (2023) for
  PIGL demand with local services in space.

### 3.2 Principle 2 — CES gravity with sectoral external economies

$$
\pi_{in,k,t}=\frac{\left(\tau_{in,k,t}\,c_{ik,t}/A_{ik,t}\right)^{-\theta_k}}
{\sum_{l}\left(\tau_{ln,k,t}\,c_{lk,t}/A_{lk,t}\right)^{-\theta_k}+\left(\tilde\tau_{n,k,t}\,\tilde p_{k,t}\right)^{-\theta_k}},
\qquad
A_{ik,t}=\bar A_{ik,t}\left(\frac{L_{ik,t}}{\text{area}_i}\right)^{\rho_k}
$$

- **What is kept and lost.** With Pareto heterogeneity, Melitz aggregates to this form with a
  scale elasticity tied to (θ, σ) (Kucheryavyy–Lyn–Rodríguez-Clare 2023), so the macro content
  survives. What is lost is the firm-level exporter margin, which the macro story does not
  use. Keep it for the MMS satellite (P2).
- **What is gained.** No cutoffs, kinks or corners. Uniqueness conditions become checkable
  (Allen–Arkolakis–Li). Speed becomes adequate for roughly 1,500 locations × 29 years ×
  hundreds of counterfactual solves.
- **Sectors, mapped to the township employment categories:**

  | Model sector | Township categories |
  |---|---|
  | agriculture (paddy staples; dry-field crops and livestock) | agriculture |
  | light manufacturing, heavy & chemical manufacturing | manufacturing, split with county MMS shares |
  | construction | construction; it absorbs roads, reservoirs and Saemaul spending |
  | local services | commerce + services + transportation + other |

  Local services are near-non-traded: a high τ, and demand from local PIGL income.
- **Trade costs** come from the digitised network plus local access:
  τ_{in,k,t} = exp(φ_k · time_{in,t}) · a_{i,t} a_{n,t}, where a_{i,t} depends on the
  township's unpaved share and its bridges. Port frictions are split inbound and outbound.

### 3.3 Principle 3 — nested location × occupation choice

$$
\pi_{k\mid n,t}=\frac{(b_{nk,t}\,w_{nk,t})^{\varepsilon}}{\sum_{k'}(b_{nk',t}\,w_{nk',t})^{\varepsilon}},
\qquad
\Phi_{n,t}=\Big[\sum_{k}(b_{nk,t}\,w_{nk,t})^{\varepsilon}\Big]^{1/\varepsilon},
\qquad
\mu_{in,t}\propto\left(\frac{B_{n,t}\,\Phi_{n,t}}{\mathcal P_{n,t}\,\delta_{in,t}}\right)^{\nu},
\quad \varepsilon\ge\nu .
$$

- **Non-employment.** k = 0 is non-employment, valued at home production. The observed
  inactive and unemployed shares pin it down, and it absorbs underemployment — Lewis's (1954)
  surplus labour.
- **The agricultural productivity gap.** The occupation wedges b_{nk} rationalise the gap
  (Gollin–Lagakos–Waugh 2014) and the frictions of leaving farming (cf. Hsieh–Hurst–Jones–Klenow
  2019; Lagakos–Waugh 2013 on selection; Lagakos–Mobarak–Waugh 2023 on migration frictions). If roads and schooling lower them, that is a
  mechanism of structural change in its own right.
- **New model outputs.** Township employment by sector; farm versus non-farm population (the
  draft's outcomes); the productivity gap; and the timing of the rural wage take-off (the
  Lewis turning point; its dating is debated, from the late 1960s to the mid-1970s — e.g.
  Bai 1982; see also Kim–Topel 1995). The last
  is an untargeted moment.
- **Dynamics.** Forward-looking annual migration (Caliendo–Dvorkin–Parro 2019), with young,
  prime and old age groups and age-specific δ. The draft's Table 8 cohort gradient becomes a
  moment. Natural increase is exogenous by location.

### 3.4 Principle 4 — agriculture on observed land

- **Farm households.** Competitive owner-operators; the post-1950 land reform left small owned
  farms under a 3-ha ceiling. Land rents accrue to local farm households, which gives the
  incidence the review asked for. There are two land types, **paddy** and **dry-field**, both
  observed.
- **Crops and prices.** Rice and other staples are traded nationally at a policy-wedged price:
  government procurement under the dual grain-price policy from 1969, plus import controls. It
  is financed by the Grain Management Fund, so price support is a *measured programme*. There
  are high-value products — vegetables, fruit, livestock — with high τ (perishable) and high
  income elasticity. This produces von Thünen commercialisation near cities, tested with the
  crop and livestock data.
- **Land-augmenting shocks.** Irrigation from reservoir capacity and completion dates; Tongil
  HYV (release in 1972, suitability-driven adoption, collapse in 1978–80); fertiliser, priced
  off HCI chemicals.
- **Labour-saving shock: mechanisation with an indivisible machine.** A tiller cuts labour per
  hectare by a fraction χ and costs u_t = p_{m,t}(r_t + d) per year. A farm of size ℓ adopts iff

  $$
  \chi\,\lambda_0\,\ell\,w_{iA,t}\ \ge\ u_t
  \;\Longleftrightarrow\;
  \ell\ \ge\ \ell^{*}_{it}=\frac{p_{m,t}(r_t+d)}{\chi\,\lambda_0\,w_{iA,t}},
  \qquad
  \text{adoption}_{it}=1-F_i\!\left(\ell^{*}_{it}\right),
  $$

  where F_i is the **observed** landholding distribution, and custom hiring smooths the
  threshold. Adoption now responds to local wages (industrial pull, which is P1's mechanism),
  to machine prices (the HCI machinery sector, through input–output linkages), and to the
  farm-size distribution (the land-reform legacy): Hayami–Ruttan induced innovation, with a
  micro-founded extensive margin.
- **Why the distinction matters** (Bustos–Caprettini–Ponticelli 2016). Labour-saving change
  releases labour. Land-augmenting change can absorb it.
- **Matsuyama in space, restated.** *Hypothesis:* agricultural productivity growth induces
  commercialisation where access to crop demand dominates, and labour release where access to
  non-farm opportunities dominates (cf. Matsuyama 1992; Gollin–Rogerson 2014; Sotelo 2020;
  Foster–Rosenzweig 2004). A connectivity-dependent sign reversal of the farm-employment
  response is one *derivable implication*, not the test itself. The model, with θ, φ and the
  PIGL parameters estimated elsewhere, predicts an interaction coefficient of X. The data give
  Y. That comparison is a held-out moment (§5). The earlier, sharper version ("the sign of
  reservoir × market access should flip") conflated three forces:

  1. *It is a demand-elasticity test, and gravity builds in the answer.* Under Armington or
     Eaton–Kortum, a connected township's farm output faces demand elasticity θ. An isolated
     one faces roughly the local PIGL food elasticity. Labour is retained iff the faced
     elasticity exceeds one, so with θ ≈ 4–8 and food inelastic the flip holds by
     construction. The data identify *where* on the access distribution the crossing occurs,
     which disciplines φ and the Engel parameters, not "which Matsuyama regime Korea was in".
     Matsuyama's open case also needs a homogeneous traded good, and Armington removes it.
     With Q_i = (B_i T_i)^α L_Ai^{1−α} and competitive farms,
     d log L_Ai / d log B_i = 1 + (1/α)(d log p_Ai / d log B_i − d log w_i / d log B_i). The sign
     turns on the local crop-price response relative to the opportunity-wage response, and
     connectivity moves both.
  2. *Connectivity moves goods-market and labour-market access together.* Connected
     townships also have non-farm jobs, cheaper machinery and lower migration costs.
     Industrial pull releases farm labour, the opposite sign to comparative-advantage
     retention. A null interaction is uninterpretable unless shift-share industrial pull is
     controlled for separately, and even then the coefficient is a composite. This is the
     argument for generating the coefficient from the model (indirect inference) rather than
     reading a sign.
  3. *Irrigation is not Hicks-neutral land augmentation.* Korean paddy irrigation plus
     Tongil HYV raised labour per hectare through double cropping and transplanting intensity.
     A labour-complementary shock retains labour everywhere, open or closed. Bustos–Caprettini–
     Ponticelli rely on a soy-versus-maize contrast that Korean reservoirs lack. Either find a
     cleanly land-augmenting shock or estimate the factor bias jointly with the openness
     interaction.

  Two reconciliations are needed. (i) *Rice-price support.* If procurement at a policy price
  from 1969 insulated farm-gate prices from local supply, the isolated-township price channel
  is weaker than the closed-economy benchmark. The price-policy block and the prediction must
  be derived together. (ii) *Township retention is not aggregate retardation.* Local
  agricultural retention can coexist with national industrialisation and higher welfare.
  Matsuyama's growth conclusion needs manufacturing learning-by-doing in addition, so a
  township employment response does not establish the aggregate growth effect.

  *Why Korea is a good setting.* After 1969 the rice market was nationally closed and
  policy-priced. A township was open to the nation while the nation was closed to the world, so
  the "regime" is township-level by construction. The spatial version of the question is better
  posed in Korea than in most settings.

### 3.5 Principle 5 — the growth engines the story cannot omit

- **Capital and credit.** Sector–location rental wedges (1 + s^K_{k,t}) represent directed
  credit, HCI's actual instrument. Accumulation follows K_{t+1} = (1 − d)K_t + I_t, where I_t is
  national saving plus the *observed* current-account deficit. Start with an observed
  aggregate investment path and an endogenous allocation. Move to Kleinman–Liu–Redding (2023)
  for forward-looking accumulation in space.

  Financial repression — negative real deposit rates, and rural savings channelled through
  cooperatives and postal savings (a hypothesis worth checking) — is the incidence side ("who
  paid for HCI"). It connects to Itskhoki–Moll (2019) and Buera–Shin (2013).
- **Human capital.** Build a cohort schooling stock per location from enrolment by level and
  school supply: h_c = exp(ψ·S_c). Migrants carry h. HCI's skill demand is a pull for
  schooling (P4).
- **Demography.** Exogenous natural increase by location and age.
- **World demand and prices by sector.** The light-manufacturing export boom is the no-policy
  growth engine of the 1960s and the main confounder for the parks. On open-economy structural
  change in Korea, see Uy–Yi–Zhang (2013) and Teignier (2018).
- **Residual national TFP by sector.** This is the honest residual (catch-up and imported
  technology). Report it; do not assign it to programmes.

### 3.6 Welfare and poverty as solver outputs

- **Welfare.** Compute the inclusive value by origin (the formula is already in `model.tex`)
  for farm households by land class and for urban workers.
- **Poverty.** Model income by (location, occupation, land class), with within-cell lognormal
  dispersion σ_c calibrated to the household surveys (Farm Household Economy Survey; Urban
  Household Income and Expenditure Survey), gives a headcount at a fixed real line z:

$$
H_t=\sum_{c}\omega_{c,t}\;\Phi\!\left(\frac{\ln z-\ln \bar y_{c,t}}{\sigma_c}+\frac{\sigma_c}{2}\right).
$$

"How Korea escaped poverty" then becomes a model object with a decomposition. Poverty was
concentrated in rural areas, so it is also the outcome on which parks, roads and rural
programmes should matter most. That reconciles research_agenda's options (a) aggregate growth
and (b) distribution: carry the growth engines so that the decomposition is credible, and make
poverty and structural transformation the headline outcomes alongside GDP.

### 3.7 Novelty

Cheung and Yang, "Transportation Networks, Technology Adoption, and Structural
Transformation" ([SSRN 4768158](https://ssrn.com/abstract=4768158), 2024; reportedly
forthcoming in the *Journal of International Economics*, to verify), show for India that
transport improvements lower non-labour input prices relative to wages and induce
labour-saving agricultural technology and structural transformation. That overlaps directly
with the roads → machinery → labour-release link in §1.2, so transport-induced mechanisation
alone will not distinguish this project. The stronger contribution is to separately identify
agricultural productivity shocks, industrial labour-demand shocks and connectivity, and to
explain where their interaction produces commercialisation and where it produces labour
release (§3.4). The Korean panel suits that unusually well. Whether it delivers depends on
treatment variation and measurement of the mechanisms, not on how large the final model is.

---

## 4. What the township data does inside the model

Roles: **I** = inversion input; **E** = estimation moment; **S** = measured programme shock;
**V** = held-out validation.

| Block | Variable | Model object | Role |
|---|---|---|---|
| Population | population | L_{i,t} (amenities B_{i,t}); with natural increase → net migration | I |
| | economic status: inactive / employed / unemployed | non-employment share π_{0\|n}; home-production value | I, E (response to labour-demand shocks; Lewis) |
| | employment by sector (ag, mfg, commerce, services, transport, construction, other) | π_{k\|n}; A_{ik}, b_{nk} | I, E, V (Figure 8 gradient) |
| Agriculture | registered / unregistered land area | land endowment by type; unregistered land = reclamation or informal tenure (measurement flag; possible tenure-security channel) | I |
| | farm households by landholding size, paddy vs dry | F_i(ℓ), the farm-size distribution | I (mechanisation threshold), E (adoption by class) |
| | reservoirs: name, location, capacity, construction date | irrigation shock → paddy land quality | S; elasticity from completion event studies |
| | crop types, livestock | output and crop mix; yields; Tongil if varieties are recorded | E (von Thünen response to market access), V (yields), S (HYV) |
| | wholesale and retail stores | extensive margin of local commerce; penetration of manufactured goods | E, V (with the P3 permit data) |
| Municipal finance | revenue: taxes, central subsidies, other | local fiscal capacity; central→local transfers as spatial redistribution | I (local budget), S |
| | expenditure: administration, industry & economy, education & culture, welfare | measured local public investment by function (Saemaul, extension and local roads sit in "industry & economy"); the fiscal envelope for reallocation counterfactuals | S; state-capacity heterogeneity |
| Infrastructure | road length, paved / unpaved | local access a_{i,t}; **annual dating of paving between the 1967/75/87 map snapshots** | S |
| | bridges | network edges (river crossings) | S |
| | ports | τ̃ inbound / outbound | S |
| | electricity | electrified share → services and manufacturing productivity; home production and participation (Dinkelman 2011) | S |
| | transportation, post offices, communication | local access and commuting; information/migration-cost shifter | S (secondary) |
| | medical facilities | amenity; mortality → natural increase | S / control |
| Schools | primary / middle / high schools; students; teachers; enrolment rates | schooling supply shock; cohort human capital h | S, I, E (enrolment response to local industrial demand, P4) |

**Five designs the new data enables** — each estimates a model elasticity:

1. **Reservoir completions** → the irrigation elasticity and its heterogeneity (§3.4). The
   reservoir × market-access interaction mixes the two mechanisms the paper should separate.
   - *Separate access measures.* Estimate event-study responses by **predetermined** access to
     crop markets and **predetermined** access to non-farm employment, measured separately.
     Heterogeneity by initial access shows how effects differ across places. Identifying the
     causal contribution of roads additionally needs credible variation in road access.
   - *Outcomes that discriminate between channels.*

     | Channel | Evidence to seek |
     |---|---|
     | Commercialisation | marketed output, sustained farm-gate prices, agricultural labour demand, land returns |
     | Labour release | lower labour per hectare, mechanisation, movement into non-farm work or migration |
     | Local demand spillovers | rural service employment following farm-income gains |

     Farm employment alone cannot tell these apart. Measure levels, shares and labour
     intensity separately, alongside population and commuting. Use the farm employment
     *share* for the Matsuyama prediction, because migration contaminates levels.
   - *Treatment.* Follow the irrigation command area and operational water delivery, not the
     township containing the dam. Construction employment, associated roads, displacement and
     downstream effects need explicit treatment. Neither completion dates nor engineering
     suitability establishes exogeneity on its own.
   - *Placebo.* Dry-field townships, where reservoirs matter less.
   - *A positive interaction is not a sign reversal.* Show that the estimated irrigation
     effect crosses zero within the observed support, with uncertainty bands. The employment
     interaction does not identify complementarity in national welfare.
2. **Annual paving and bridges, plus interchange openings** → the local-access and network
   trade-cost elasticities. This replaces the single 1970→90 long difference with dated
   responses and pre-trends.
3. **Farm-size class × industrial pull (shift-share) × machine prices** → the mechanisation
   threshold (χ, λ₀, u).
4. **Electrification and school openings** → effects on local services and non-farm
   productivity; cohort schooling.
5. **Central transfers and "industry & economy" spending** → the local public-investment
   elasticity (Saemaul: the uniform 1970–71 cement allocation followed by performance-based
   allocation is a natural design; verify it in the finance data).

---

## 5. Identification and estimation

| Parameter | Governs | Identified from |
|---|---|---|
| θ_k, φ (τ in travel time) | how roads change market access | price gaps across markets if local prices are digitised (Donaldson 2018); otherwise indirect inference on the market-access event studies, with θ from the literature |
| ν, δ(travel time), by age | how roads and jobs move people | O–D gravity (Statistics Korea); township net migration around interchange openings; Table 8 cohorts |
| ε, b_{nk} | how easily farm labour moves locally | sectoral employment responses to shift-share industrial pull |
| ρ_k | park persistence; the big push | park SDID and event studies; the post-1979 wind-down |
| χ, λ₀, u (mechanisation) | labour release from agriculture | adoption by farm-size class × wage and market-access shocks; tiller price series |
| irrigation and HYV elasticities | land-augmenting growth | reservoir event studies; Tongil suitability × post-1972 |
| η, v_j (PIGL) | food problem; the rise of services | household-survey Engel curves; national expenditure shares |
| capital shares; credit wedges s^K | accumulation vs TFP; HCI's instrument | national accounts; policy-loan vs curb-market rates; MMS assets |
| ψ | the human-capital contribution | Mincer returns; enrolment responses to school openings |

**Held out as untargeted validation:** the Figure 8 decile gradient; the 1979-cohort washout;
the timing of the rural wage take-off; the rural–urban income V-shape; the reservoir ×
access interaction coefficient (§3.4); the national paths of agricultural employment and
urbanisation, *only* if the township series that sum to them are not inversion inputs (§3.1). A cheap stress test is to
estimate on 1962–79 and predict 1980–90 from measured shocks alone. The 1980 combination of
oil shock, political crisis and harvest failure is a natural out-of-sample test.

**Two-step estimation.** Step 1 is the exact year-by-year inversion. Step 2 combines the
structural event studies on the inverted fundamentals with indirect inference of the remaining
elasticities on the reduced-form coefficients, using the same estimators and samples.

---

## 6. Counterfactuals that tell the story

1. **Decomposition of 1962–90 growth and poverty reduction.** Drivers:
   D = {world demand, capital (domestic vs foreign saving), human capital, demography, HCI credit
   wedges, parks, roads, rural programmes (irrigation, HYV, rice price, electrification,
   Saemaul), residual TFP}. Outcomes: GDP per capita, agricultural employment share,
   urbanisation, poverty headcount, the rural/urban gap, and welfare by origin. The
   order-invariant Shapley share of driver d is

   $$
   \phi_d=\sum_{S\subseteq D\setminus\{d\}}\frac{|S|!\,(|D|-|S|-1)!}{|D|!}\,\big[Y(S\cup\{d\})-Y(S)\big].
   $$

   With 10 drivers this takes 1,024 dynamic solves, so design the solver for it (hat algebra,
   vectorised or JAX, warm starts). Alternatively, group the drivers into 5 blocks, which
   takes 32 solves.
2. **Complementarity.** Pairwise interactions come from the same runs:
   Y(a,b) − Y(a) − Y(b) + Y(∅). The pairs are parks × roads, roads × rural programmes, and
   schooling × HCI. Compare them with the reduced-form triple difference (research_agenda §4) —
   the "sum or product" question, priced.
3. **Sequencing.** Roads before or after parks; the Green Revolution before mechanisation. Also:
   rural programmes without industrial pull (would rural transformation have happened?) and
   industrial pull without rural programmes (would the food problem or rural poverty have
   bound?).
4. **Incidence.** Who escaped poverty, by origin-township type and land class, and what
   financial repression cost savers.
5. **Persistence and the big push.** Remove the HCI wedges after 1979 and map the basins of
   attraction (Choi–Levchenko; Rodrik 1995).

---

## 7. Staged build — each stage is independently useful

The first version of this memo put the agriculture block at Stage 3, after occupation choice,
capital, forward-looking migration and human capital. That delayed the mechanism behind §3.4
until most of a large model existed. Revised order:

| Stage | Content | Deliverable |
|---|---|---|
| **0 — now, no new data** | Closure fix ✅; macro scorecard ✅. Measurement fixes ✅: employment in workers, double-deflated real GDP, gross-output / value-added / employment shares reported separately. Exact PIGL equivalent income for migration and welfare ✅. Nested entry–adoption–export choice ✅. Separate export demand elasticity `sigma_x` ✅. A data schema (location × year × variable) with loaders, the boundary crosswalk, and a synthetic township panel for CI | A current model whose reported numbers measure what their labels say |
| **1 — small spatial agriculture model** | Agriculture (paddy and dry field, competitive farms, irrigation as an explicit factor-biased shock), non-farm production, land, goods trade and labour mobility. Derive the conditions for each employment response (§3.4), and the model-predicted reservoir × access coefficients | The commercialisation-versus-release prediction, with θ, φ and η taken from elsewhere |
| **2 — reservoir event studies** | Audit irrigation exposure (command areas, water delivery); differentiated event studies by crop-market and non-farm access, with prices, wages and labour intensity (§4, design 1) | The empirical side of §3.4 — standalone |
| **3 — expand the quantitative model** around the mechanisms that survive | Annual clock; gravity with external economies; inversion *after* identification is demonstrated (§3.1); occupation choice with non-employment; structural event studies for parks, interchanges and paving | "Where and when productivity and amenities changed, and which programmes moved them" |
| **4** | Capital, schooling, demography, poverty distributions and the national growth decomposition, *when the chosen counterfactual requires them*; counterfactual battery; welfare and poverty incidence | The macro paper |

Annual timing, competitive agriculture and a simpler trade block are sensible from Stage 1.

**Engineering notes.**

- **Module layout.** New modules: `trade.py` becomes vectorised gravity shares;
  `agriculture.py`, `dynamics.py` (CDP value functions, capital), `inversion.py`,
  `decompose.py` (Shapley) and `data/` (schema, crosswalk, loaders) are added.
- **Solver.** Use Newton–Krylov or Anderson acceleration, or JAX with autodiff for the
  estimation gradients. Year-by-year inversions run in parallel.
- **Tests.** Replace the directional "calibration" tests with (i) recovery of known
  fundamentals from synthetic data by the inversion (an identification test, not just exact
  fit), (ii) invariance to the initial guess, and (iii) scorecard moments that are
  *reported*, not asserted.

---

## 8. Asks for the digitisation team (time-sensitive: cheap now, expensive after the freeze)

1. **Urban units** — dong, gu and si with the same variables. Without the destination side of
   every flow, the inversion is impossible for cities. MMS covers only county manufacturing.
2. **An annual boundary crosswalk with area weights**, 1960–90. This is repeated from
   research_agenda; it remains the likeliest silent failure.
3. **Metadata per variable-year**: units, definitions (especially "employed" and "unemployed",
   and whether they are by residence or workplace), and the source volume and page.
   Double-enter a random sample to measure transcription error.
4. **Currency and prices.** Convert pre-June-1962 hwan to won (10 hwan = 1 won) and record
   deflators. **Digitise any local prices** — rice, barley, fertiliser, tillers, farm wages —
   because price gaps identify trade costs.
5. **Agriculture detail.** Irrigated versus rain-fed paddy; area and output by crop *and rice
   variety* (Tongil); machinery stocks (tillers, threshers, sprayers); fertiliser use; owner
   versus tenant; landholding classes at full granularity; fisheries, if they are in "other".
6. **Electrification** — households electrified — as an annual series if it exists.
7. **Population by age and sex** (at least the census years 1966/70/75/80/85/90), plus births
   and deaths for natural increase. Economic status by sex, for female participation.
8. **The municipal finance chart of accounts in full**, including central transfers (local
   shared tax, subsidies) and any itemised Saemaul spending.
9. **Schools**: entrants and graduates by level, not only stocks, because graduates are
   cohort human-capital flows.
10. **Transport and communication**: bus routes and stops, rail stations, vehicles, telephone
    subscribers.

---

## 9. Decisions for the team

1. **Framing.** Adopt "baseline = history + decomposition", with poverty and structural
   transformation as the headline outcomes and GDP alongside? This changes what the model must
   contain: capital, human capital, world demand. (Recommended.)
2. **Melitz.** Drop it in the flagship macro model and keep firm heterogeneity for the MMS
   satellite? (Recommended.)
3. **Capital.** Observed aggregate investment with endogenous allocation first, and
   endogenous saving (KLR) later? (Recommended.)
4. **Geography.** Townships plus urban units, with counties for manufacturing productivity.
   This needs the urban coverage in ask 1 confirmed. Consider commuting zones around cities,
   because township data are by residence.
5. **Closure data.** Feed the observed NX/GDP path into `nx_gdp`, or keep balanced trade in the
   toy economies? (Observed path, once the model is annual.)

---

## Appendix A — reproducing §2

- `python scripts/macro_scorecard.py` prints the macro scorecard, the first-period population
  jump, the cutoff-ordering violation and the guess-sensitivity check under the current code.
- `python scripts/simulate_policy_shock.py` prints the 1985 policy effects on gross-output,
  value-added and employment shares side by side.
- The +0.127 check: run the policy simulation's `calibration_moments` on commit `cdafe29`,
  and the guess-sensitivity check there.
- The indeterminacy under the old closure: check out `bce51c7`, then solve
  `solve_static_equilibrium` for `build_baseline_inputs()` at t = 0 from
  `initial_guess(...)` with `w`, `r` and `E` scaled by 0.5 and 2.0, and compare `eq.w`.
  `tests/test_accounting.py::test_equilibrium_is_invariant_to_initial_guess` fails on that
  commit and passes now.

## Appendix B — references added by this memo

Adão, Arkolakis & Esposito (2019) General equilibrium effects in space · Allen & Arkolakis
(2014 QJE) · Allen, Arkolakis & Li (2020 WP) uniqueness in network models · Andrews, Gentzkow
& Shapiro (2017 QJE) · Bai (1982, *Developing Economies*) Korea's turning point · Buera,
Kaboski & Townsend (2023 JEL) From micro to macro development · Buera & Shin (2013 JPE) ·
Bustos, Caprettini & Ponticelli (2016 AER) · Cheung & Yang (2024, SSRN 4768158) Transportation
networks, technology adoption, and structural transformation · Caliendo, Dvorkin & Parro (2019 ECMA) · Dekle,
Eaton & Kortum (2008) · Dinkelman (2011 AER) · Donaldson (2018 AER) · Budí-Ors & Pijoan-Mas
(WP) Macroeconomic development, rural exodus, and uneven industrialisation · Eckert & Peters
(WP) Spatial structural change · Fan, Peters & Zilibotti (2023 ECMA) · Foster & Rosenzweig (2004
EDCC) · Gollin, Lagakos & Waugh (2014 QJE) · Gollin, Parente & Rogerson (2007 JME) the food
problem · Gollin & Rogerson (2014 JDE) · Hao, Sun, Tombe & Zhang (2020) The geography of
development · Hayami & Ruttan (1971) · Hsieh, Hurst, Jones & Klenow (2019 ECMA) · Itskhoki &
Moll (2019 ECMA) · Kim & Topel (1995, NBER volume) Korea's labour markets · Kleinman, Liu &
Redding (2023 ECMA) · Kucheryavyy, Lyn & Rodríguez-Clare (2023 AEJ:Macro) · Lagakos & Waugh
(2013 AER) · Lagakos, Mobarak & Waugh (2023 ECMA) · Lewis (1954) · Matsuyama (1992 JET) ·
Nakamura & Steinsson (2018 JEP) · Redding & Rossi-Hansberg (2017 ARE) · Sotelo (2020 JPE) ·
Teignier (2018 JDE) trade and structural transformation (Korea) · Tombe & Zhu (2019 AER) ·
Uy, Yi & Zhang (2013 JME).
