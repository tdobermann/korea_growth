# Research Agenda: Deciphering the Miracle on the Han

**Purpose.** Take stock of where the project stands, given (i) the existing model
(`docs/model.tex`, `src/korea_growth/`), (ii) the empirical draft
(`docs/paper_draft05032026.pdf`), (iii) the referee-style review (`docs/model_review.md`)
and its status (`status.md`), and (iv) the new data and team interests in
`Korea_Project_Logistics`. It proposes a portfolio: one flagship, several owned
satellites, and a sequencing that respects the September data freeze and the team's
stated constraints.

_Written 2026-07-30._

---

## 0. The one-paragraph view

The project's comparative advantage is not any single programme evaluation — it is that
**four staggered national programmes (industrial parks, motorways/paved roads, the
Green-Revolution seed–irrigation package, and administrative/fiscal investment) hit an
annual, township-level panel with plausibly independent timing and geographic
incidence.** That is a setting in which *programme complementarity* — Bookang's "sum or
product" question — is identifiable, and complementarity is precisely what neither the
existing HCI literature (Lane 2025; Kim–Lee–Shin 2021) nor the roads literature
(Donaldson–Hornbeck 2016; Faber 2014) can speak to. Everything below is organized around
protecting that asset. The most likely way to waste it is to spend 2026–27 improving the
model's internals while the *data pipeline, the boundary harmonisation, and the
identification designs* remain unbuilt.

---

## 1. Where the repo actually stands

**Done (and genuinely useful).** Phase 1 of the review: the accounting closes (Walras to
~1e-13), migration is re-derived from Gumbel shocks on a positive index, the `ξ` bug is
fixed, subsidies gross up correctly, land rents are rebated, fixed costs are paid in
labour, infrastructure buys goods. This matters — the model is now a *legitimate* GE
system rather than a leaking one.

**The binding constraint is no longer model internals.** Of the review's remaining items,
only a subset actually gates the papers we want to write. The honest statement of the
current position:

| What exists | What it can support | What it cannot |
|---|---|---|
| 5 regions, 3 sectors, 6 unevenly-spaced periods | directional storytelling | any decile gradient, any county event study, any welfare number |
| Hand-set `A`, `ρ_j`, `D̃`, `A_Agri` paths | illustrative counterfactuals | "how much of the miracle was policy" |
| No capital, no credit wedge | output-subsidy thought experiments | HCI's actual instrument or its incidence on savers |
| No welfare metric wired to output | plots | the paper's whole point |

**Implication.** Stop treating `status.md`'s Phase 2 list as a queue to work down. Three
items on it are load-bearing for every paper below (county geography with network-based
`τ_od`; annual clock; welfare metric); two more are load-bearing for the flagship only
(capital + credit wedge; forward-looking migration). The rest — Melitz-agriculture
rework, free entry, sector-specific `σ_j`, split port frictions — should be re-derived
*from the new data* rather than done as generic robustness (see §5).

**One blunt point about the empirical draft.** Its identification is cross-sectional
first differences, 1970→1990, with geography controls, `R²≈0.45`, and the "exclude the
J nearest cities" adjustment doing the heavy lifting. The 1970-tiller-stock placebo is
good and necessary but not sufficient: a single long difference cannot show pre-trends,
cannot date the response, and cannot separate the road shock from anything else that
happened to well-connected townships over twenty years. **The annual township panel is
the fix, and converting the draft's five outcome domains from long differences to
staggered event studies with township fixed effects is the highest-return single use of
the new data.** Do this before adding any model feature.

---

## 2. What the new data unlocks that the draft could not do

Reading the raw-data list against the draft, five things change qualitatively.

1. **Annual frequency → event studies with dynamics.** Population by sector of
   employment and economic status, road length (paved/unpaved), municipal expenditure,
   schools and enrolment, all annual at township level. Every reduced-form result in the
   draft becomes a dated response with pre-trends. Also: the *timing* of the service
   response relative to park openings becomes a testable object rather than an assertion.

2. **A second, orthogonal agricultural shock.** Reservoirs come with **construction
   dates**, and the Tongil high-yielding rice variety was released in 1972 with strongly
   suitability-dependent returns. Right now the draft cannot distinguish "market access →
   mechanisation → labour release" from "agricultural modernisation → labour release →
   reallocation": both arms are consistent with the same long difference. With a
   road/market-access shock *and* a seed/irrigation shock that is orthogonal to roads,
   **both arms of the chain are separately identified.** This is the difference between a
   suggestive narrative and Jeongkyung's paper.

3. **Programme interactions.** Three staggered treatments (park groundbreaking; motorway
   interchange opening; reservoir/HYV exposure) on the same annual panel means the
   *interaction* terms are estimable — the empirical analogue of the model's cross-partial.
   No existing big-push paper has this.

4. **Municipal finance.** Annual local revenue and expenditure by category (general
   administration; industry and economy; education and culture; social welfare) for a
   developing country in the 1960s–80s is close to unique. It (a) measures the fiscal
   envelope the optimal-policy counterfactual reallocates, (b) makes "administrative
   investment" a measured programme rather than a residual, and (c) lets us ask whether
   local state capacity mediated the returns to the national programmes.

5. **Service-sector entry *and exit* dates, geocoded.** This is business-dynamism data.
   It gives the non-tradable sector's extensive margin directly — which is exactly the
   free-entry margin the model has as a free parameter. Entry and exit *rates* become
   estimation moments; establishment survival becomes a micro test.

**Two things to verify immediately, because they are decisive.**
- **Education breakdowns in the population data** (the doc flags this as "need to
  check"). If township population is available by education level annually, the human
  capital paper (§3, P4) is live; if not, it rests on schools/enrolment only, which is
  supply-side and much weaker.
- **Administrative boundary harmonisation, 1960–1990.** Korean township (`eup/myeon/dong`)
  and county boundaries changed repeatedly over this period — city promotions, splits,
  annexations into expanding urban areas. A consistent spatial crosswalk with area weights
  is the single most likely hidden project-killer, and it must be inside the September
  freeze. Every design below assumes it exists.

---

## 3. The portfolio

I would run **one flagship + four owned satellites**, with the satellites deliberately
chosen so that each one estimates a parameter or validates a mechanism the flagship needs.
That way the flagship is not a separate five-year bet; it is the assembly of work that is
independently publishable.

### P0 — FLAGSHIP: "Sum or Product? Complementarity and Incidence in Korea's Big Push"

**Question.** How much of Korea's 1965–85 transformation — aggregate *and* its
distribution across space and between farm and non-farm households — is attributable to
the spatial policy package, how much of that is *complementarity* between programmes
rather than the sum of their separate effects, and would a different allocation of the
same fiscal envelope have industrialised Korea faster or shared the gains more widely?

**Why it can be top-5.** Three things nobody has:
- **A priced complementarity.** "Parks-only / roads-only / seeds-only / all" with an
  estimated interaction, disciplined by an empirical triple-difference. This is the
  formalisation of the big-push idea with credible identification behind the cross-partial.
- **Incidence.** Welfare by region × (worker / landowner) × income level. The PIGL
  machinery finally earns its keep: cheap manufactures matter more to the poor, food
  prices cut the other way. "Who paid for the miracle and who received it" is the
  question the aggregate HCI literature cannot answer.
- **Optimal spatial allocation of a measured envelope** (Gaubert-style), where the
  envelope comes from actual municipal and national finance data rather than assumption.

**The killer validation.** Run the draft's *own* estimators on model-generated data and
reproduce the Figure 8 sign reversal (non-farm MA coefficient from −1.81 at D1 to +0.63
at D10) as an **untargeted** moment. If the estimated model generates a sign reversal it
was not fitted to, that single figure carries the paper.

**The strategic tension to resolve now, not later.** If the flagship's headline is "the
spatial policy package explains X% of aggregate Korean growth," X may well be modest —
because the miracle also ran on capital accumulation under financial repression, world
demand growth, human capital, and the demographic transition. Two honest routes:
- **(a) Full growth decomposition.** Accept the accounting burden (capital + savings/
  financial repression, world demand by sector from actual trade data, demography) and
  make the credible number the contribution. "How much of the miracle was the policy" is
  a first-order question and a defensible small answer is publishable.
- **(b) Distribution-and-complementarity framing.** Keep aggregate growth as context,
  make the object of the paper the *spatial and distributional* incidence plus the
  complementarity, where the data advantage is overwhelming and the number is large.

I would go with **(b) for the flagship and (a) as a companion piece**, because (b) is
where the identification is strongest and (a) invites a fight with the Young (1995)
accumulation literature that we cannot win without capital-stock data we do not have.
Decide this before the model's counterfactual battery is built — it changes what the model
must contain.

**Owner.** Tim (theory/quantification) + Jay (spatial modelling and geography pipeline),
drawing on all satellites. Explicitly **not** anyone's dissertation chapter — too slow,
too many dependencies.

---

### P1 — "Push, Pull, and Access: Industrial Labour Demand and Agricultural Modernisation"

**This is the single most publishable standalone idea in the group's current list**, and
it is already Jeongkyung's stated direction. The chain: urban-industrial labour demand →
rural outmigration → farm labour scarcity → labour-saving technology adoption → higher
agricultural labour productivity → sustained output with fewer workers → further
reallocation.

**Why it is exciting and not incremental.** The literature mostly runs the arrow the
other way — Bustos–Caprettini–Ponticelli (2016) have agricultural technology *causing*
industrialisation. Running it in reverse (industrial pull *causing* agricultural
technology) is a distinct and under-tested mechanism, and it is the mechanism that
distinguishes East Asian structural transformation from the Latin American path. The
closest design precedent is the Bracero literature (Clemens–Lewis–Postel 2018), which
found essentially *no* mechanisation response to a labour-supply shock — Korea as a
well-identified counter-case is a real contribution, not a replication.

**Identification, upgraded from the draft.**
- Replace generic market access with a **shift-share "industrial pull"**: exposure of
  township *i* to national growth in park-targeted industries, weighted by travel time
  through the year-*t* road network. This is labour-demand pull, not a bundle of
  everything roads do, and it removes the need for the "exclude J nearest cities" hack.
- **Instrument the road network properly.** The current design does not use the strongest
  available variation: motorways were built to connect endpoints, so use
  **interchange-opening dates** (the treatment is the interchange, not the line) with
  least-cost-path / straight-line placebo networks as the excluded instrument
  (Faber 2014; Banerjee–Duflo–Qian).
- **Close the loop with the orthogonal ag shock.** Tongil-rice suitability × post-1972,
  and reservoir completion dates, give an agricultural-productivity shock independent of
  roads. Estimating both arms — pull → adoption, and adoption → release of labour — with
  two different shocks is what makes the chain causal rather than a story consistent with
  one correlation.
- **Use the annual age-cohort data.** The draft's Table 8 (retention concentrated at ages
  25–49 in 1970) becomes a dated, cohort-specific migration response — and directly
  disciplines age-specific migration costs in the flagship.

**Feeds the flagship.** Adoption-cost level and elasticity; migration elasticity `ν` and
the `δ_od` gravity matrix from O–D flows; age-specific migration costs.

**Owner.** Jeongkyung (thesis chapter 3, ~1.5 years — realistic). Bookang on the
collectivism heterogeneity as a distinct section.

---

### P2 — "What Makes Industrial Policy Work? Site Selection, Agglomeration, and Displacement"

**The under-exploited asset here is the park data's `selection process` field.** If the
records document candidate or runner-up sites and the criteria used, this supports a
**counterfactual-sites design** (Greenstone–Hornbeck–Moretti 2010): compare realised park
counties to the sites that were considered and rejected. That is a large credibility jump
over "treated county vs. 175 donors," and it is the difference between a good SDID paper
and a top-5 place-based-policy paper. **Auditing whether the selection documentation
supports this is a high-priority, low-cost task for August.**

**Three results the MMS panel can deliver that the current draft does not.**
1. **Decomposition of the park effect** into direct policy inputs (entry-cost reductions,
   credit wedges, site infrastructure, port access) vs. agglomeration (`ρ_j`) vs. an
   unexplained TFP residual. Either answer is a headline: if measured inputs plus an
   estimated agglomeration elasticity reproduce the SDID event study, that is the result;
   if they cannot without a residual, the size of the residual is the result.
2. **Displacement.** The standard fatal criticism of place-based policy evaluation is that
   local gains are reallocation. MMS has *national* coverage at 5-digit industry × county,
   so net creation vs. spatial reallocation is measurable. Do it explicitly.
3. **Networks × space.** 5-digit codes plus an IO table let us ask whether parks worked
   because they co-located input-output-linked sectors, and whether roads made
   cross-region linkages viable (Liu 2019 on network targeting, but spatial). The
   interaction of production networks with spatial frictions in industrial policy is
   genuinely open, and this data can address it.

**Bonus, near-free given MMS is in hand.** Allocative efficiency: Hsieh–Klenow-style
decomposition with staggered park treatment. Korea appears to be the case where directed
credit did *not* wreck allocation — Kim–Lee–Shin (2021) find output gains alongside
misallocation; a spatial, staggered-treatment version is a clean satellite paper.

**Feeds the flagship.** `ρ_j` by sector, park policy inputs as measured wedges, and the
1979-cohort washout (near-zero ATT at the second oil shock) as an untargeted moment on
whether a big push requires sustained demand.

**Owner.** Jay lead; Ignacio on the "what makes it successful" heterogeneity.

---

### P3 — "Productive Urbanisation: Non-Tradables, Entry, and Local Multipliers"

The geocoded service-permit panel with entry *and exit* dates (1960–1990) is the asset
almost no comparable historical study has. Questions:
- **Local multipliers** of manufacturing shocks in the non-tradable sector (Moretti-style),
  with the timing of entry relative to park opening as the identifying detail.
- **Was rapid urbanisation productive?** Distinguish churn from net growth; measure
  establishment survival; separate demand-driven entry (income growth) from
  supply-driven (falling entry costs as roads arrive).
- **Ignacio's Seoul housing thread** — slum clearance through the 2-million-houses
  programme — is a distinct urban paper on how a city absorbs a migration surge. Keep it
  separate; it is a different literature and a different referee pool.

**Feeds the flagship.** Service entry/exit rates discipline the free-entry margin and
sunk entry cost in non-tradables — an unusually tight model–data link, and one that
converts a currently free parameter into an estimated one.

**Owner.** Ignacio.

---

### P4 — "Industrial Policy and Human Capital"

**The most novel angle relative to the existing Korea literature**, conditional on the
education breakdowns existing. Annual township schools, teachers, students, enrolment
rates, *plus* municipal education-and-culture expenditure, *plus* local industrial demand
shocks, lets us separate the **supply** of schooling (the state building schools) from the
**demand** for it (returns to schooling rising with local industrial employment).

**Framing hook.** Atkin (2016) finds Mexican export-manufacturing jobs pulled children
*out* of school. Korea is the canonical growth-with-education case. Did HCI-driven local
labour demand raise or lower schooling — and does the answer depend on whether the jobs
were skill-demanding (HCI machinery/chemicals) rather than assembly? A sign flip against
Atkin in the archetypal miracle economy is a top-5 hook.

**Second, more ambitious layer.** If human capital accumulated *in response* to industrial
policy and then enabled the next stage of industrialisation, that is a dynamic
complementarity — and a candidate answer to why Korea sustained where import-substituting
peers did not. That layer belongs in the flagship's model (a schooling-choice margin), not
in this paper.

**Ownership note.** Both Jeongkyung and Tim flagged human capital. Cleanest resolution:
Jeongkyung keeps the migration/agriculture chain (P1), Tim takes human capital as the
schooling margin *inside* the flagship, and P4 as a reduced-form paper goes to whoever has
bandwidth in 2027 — with the two of them as co-authors either way. Settle this explicitly;
overlapping claims on the same mechanism are how groups like this fracture.

---

### P5 — Satellites worth keeping, not worth leading with

- **Reforestation and the environmental transition** (Ignacio). Outmigration + household
  fuel switching (the coal-briquette policy) + forest recovery is a genuinely good story
  and Korea's reforestation is one of the great policy successes. Framed as "structural
  transformation and the environmental transition" with the identification coming from the
  same road/park shocks, it is a strong AEJ/JEEM paper and a plausible-but-not-likely top-5.
  Value to the group: it is nearly free once the pipeline exists.
- **State capacity and the returns to industrial policy** (municipal finance). Did local
  administrative and fiscal capacity mediate national programme returns? Distinguishing
  asset, hard identification. Best deployed as a *heterogeneity section* in P0/P2 first;
  promote to a paper only if a design appears.
- **A data-and-facts paper** on the MIRACLE platform. Strategically useful: it stakes
  the claim early, which matters because the platform is exactly the kind of asset another
  team can scoop by publishing descriptive work first.

---

## 4. If I had to pick three

1. **P1 (Push, Pull, and Access).** Highest probability of a top-5 outcome per unit of
   effort, incentives already aligned, and the two-orthogonal-shocks design is the piece
   that turns a correlation into a mechanism. Start here.
2. **P2 (site selection + displacement).** Highest standalone value, and the
   counterfactual-sites design is a genuine identification upgrade that costs an archival
   audit rather than a year of modelling.
3. **P0 (the flagship), but only the complementarity triple-difference first.** Before
   committing to the full structural build, run the reduced-form interaction: park opening
   × road/interchange timing × ag-suitability on the annual township panel. **If the
   interaction is there, the flagship has a spine and the model exists to price it and to
   compute counterfactual allocations. If the interaction is not there, "sum, not product"
   is itself a publishable and important negative result — and it saves two years of
   structural work aimed at quantifying something that isn't in the data.** This is the
   cheapest high-information test available and it should be run first.

The most exciting single empirical object in the whole project is that interaction. Nobody
has credibly estimated programme complementarity in a big push, and this data can.

---

## 5. What this implies for the model

Re-prioritised against `status.md`, by what the papers actually need.

**Non-negotiable, do first.**
1. **County/township geography with `τ_od` from the digitised network by year.** ~160–183
   counties, or townships for rural outcomes, aggregating up. Nothing in the portfolio
   works at 5 regions. This is a data-pipeline task before it is a model task, and it is
   Jay's natural first contribution from September.
2. **Annual clock.** Uneven 3/5/2/5/5-year periods make every per-period elasticity
   meaningless and make it impossible to match an annual event study. This is the
   prerequisite for indirect inference on the reduced-form coefficients.
3. **Welfare metric wired into solver output** (the inclusive value is derived in
   `model.tex` but not computed). Without it there is no incidence, and incidence is the
   flagship's contribution.
4. **QSE inversion** in the baseline year: back out `V̄` and `A` from observed
   populations, wages, and sectoral employment. Replaces hand-set exogenous paths — this
   is what turns simulation into quantification.

**Load-bearing for the flagship.**
5. **Capital with a credit wedge.** HCI's instrument was directed credit at negative real
   rates, not output subsidies. Without it the incidence question ("savers paid") cannot
   be asked and the fiscal-envelope counterfactual has no envelope. Genuinely large:
   second state variable, solver work. Scope deliberately.
6. **Forward-looking migration** (Caliendo–Dvorkin–Parro). Required for any big-push /
   basin-of-attraction claim and for matching the *timing* of the event studies. Myopia
   understates reallocation toward credibly-growing places, which biases exactly the
   Changwon result.
7. **Path multiplicity as economics, not nuisance.** With `ρ_j > 0` and forward-looking
   migration the dynamic system can have multiple paths. Characterising when temporary
   policy moves the economy across basins **is** the "would the miracle have happened
   anyway" counterfactual, and it is the most direct answer to "explain the Korean growth
   miracle."

**Re-specify from the new data rather than as generic robustness.**
8. **Competitive agriculture with heterogeneous land (Sotelo 2020) and a scale-dependent
   mechanisation margin.** The review flagged Melitz-agriculture as indefensible; the new
   data makes the replacement *better identified*, not just more defensible. Farm
   households by landholding size class, paddy vs. dry-field, machine holdings, and
   caloric suitability jointly identify adoption as a function of farm scale and land
   quality. That is the actual economics of tiller adoption, and the size distribution is
   an estimation moment.
9. **Non-tradable services with sunk entry costs.** Discipline entry and exit with the
   permit data. Also fixes the "services traded like steel" problem for free.
10. **Sector-specific `σ_j`, split inbound/outbound port frictions.** Cheap; do them
    while the pipeline is being built. Export promotion genuinely subsidised outbound
    logistics, so the asymmetry is substantive, not cosmetic.

**Deprioritise.** Free entry in manufacturing, land in utility as a separate exercise
(it comes along with landownership and incidence), the full Phase-6 rewrite of `model.tex`
(do it when the model is final, not before).

**Measurement consistency to fix at the same time.** The empirical MA measure imposes
trade elasticity θ=1 on travel times while the model's bilateral elasticity is σ−1. Do
not try to reconcile the regressor: **simulate the model and apply the paper's own
estimators (indirect inference)**, which sidesteps the inconsistency entirely and gives
the untargeted-validation result as a by-product. Also deflate the SDID ATTs — they are
in current-price MMS units across a decade of 15–25% inflation — and match the log
specifications.

**Moment → parameter map, to be stated explicitly in the paper** (Andrews–Gentzkow–Shapiro
sensitivity):

| Parameter | Identifying moment | Source |
|---|---|---|
| `θ`, `κ` (Pareto) | firm-size distribution | MMS establishment panel |
| `ν`, `δ_od` | gravity on migration flows | Statistics Korea O–D |
| age-specific migration costs | cohort retention gradient | annual township age panel |
| `ρ_j` (agglomeration) | SDID event-study profile | MMS + park cohorts |
| adoption cost level/elasticity | tiller adoption × MA and × farm size | township ag panel |
| services sunk entry cost | entry/exit rates, survival | service permit records |
| `D̃_{j,t}` (world demand) | sectoral world import demand | external trade data |
| `σ_j` | trade literature / tariff variation | external |
| `η`, `v_j` (PIGL) | Engel curves, sectoral shares 1960–85 | national accounts + consumption assets |
| **held out** | Figure 8 decile sign reversal; 1979 cohort washout | untargeted validation |

Note `D̃ × 1.15` in the current calibration is roughly an order of magnitude too timid —
Korea's exports/GDP went from ~9% to ~35% over the period, and world machinery demand is
a first-order confounder for Changwon (park effect vs. world demand).

---

## 6. Sequencing against real constraints

Constraints as stated: Bookang is committed to the platform build through early September
with a data freeze after, and is on the job market this autumn; Jay has one day/week from
September; Jeongkyung one day/week now, thesis chapter within ~1.5 years; Ignacio's
Korea time is contingent on it looking promising, with two submissions and a revision
competing; Tim from October, prefers theory, weak short-run speed incentives.

**Now → early September (before the freeze). No new empirics; protect the freeze.**
- **The variable request list to Bookang.** Highest-value action available this month.
  Must include: annual township employment by sector *and* economic status; population by
  age *and education if it exists*; paved/unpaved road length; municipal expenditure by
  category; schools/teachers/students/enrolment; farm households by size class × paddy/dry;
  reservoir names, locations, capacities and construction dates; and — separately and
  explicitly — **the administrative boundary crosswalk with area weights, 1960–1990**.
  Missing variables after a freeze cost a year.
- **Audit the park `selection process` documentation** for a counterfactual-sites design
  (P2). Low cost, potentially decisive.
- **Verify the motivating macro fact** Tim flagged: rural–urban income divergence then
  convergence. If it holds in the data, it is the flagship's opening figure and one of the
  best narrative assets in the project — it connects the paper to Kuznets and to current
  policy debates. If it does not hold, we need to know before it is in an abstract.
- **Geography pipeline** (Jay, ramping): travel-time matrices from the 1967/1975/1987
  paved networks and annual motorway shapefiles; interchange opening dates; distance to
  port; least-cost-path placebo networks.
- **Model** (Tim, ramping / can be scaffolded now): county-dimension refactor, annual
  clock, welfare metric in solver output, `σ_j` and port-friction splits. These need no
  new data.

**September → December.**
- P1 estimation on the annual panel: event studies replacing long differences; shift-share
  industrial pull; Tongil/reservoir shocks; cohort responses.
- **The complementarity triple-difference** (§4, item 3). Run it early; it is a go/no-go
  for the flagship's framing.
- P2: SDID re-run with counterfactual sites if available; displacement accounting.
- P3: service entry/exit descriptives and local multipliers.

**2027.** QSE inversion and indirect inference; capital/credit block; the flagship's
counterfactual battery (parks-only / roads-only / seeds-only / all; incidence; persistence
after the 1979 wind-down; reallocation of the same envelope). `model.tex` rewritten as a
submission model section last.

---

## 7. Risks

- **Boundary harmonisation.** Named again because it is the most likely silent failure.
- **Scooping.** Lane (2025) has HCI and linkages; Kim–Lee–Shin have plant-level HCI;
  Choi–Levchenko have temporary-subsidy persistence. Differentiation must be *spatial +
  rural + distributional + complementarity*, and it should be stated in the first
  paragraph of every draft. A descriptive data paper stakes the platform early.
- **Flagship gravity.** A five-year structural project with four part-time authors, one of
  whom is on the job market, is the classic setup for a paper that is always eighteen
  months out. The mitigation is structural, not motivational: every satellite must be
  independently submittable, and the flagship must be assembly rather than a from-scratch
  bet.
- **Assuming the conclusion.** The current calibration hard-codes the empirical findings
  it should generate (`A_Agri` and `β_Agri` paths imposed to match Tables 2/4; Changwon
  handed `A × 1.5`). This is the criticism that kills structural papers at top-5. Every
  quantitative result in the flagship needs an explicit statement of what was targeted and
  what was not.
- **Overlapping claims.** Human capital (Jeongkyung/Tim) and industrial policy
  (Jay/Ignacio) are each claimed twice in the logistics doc. Partition ownership in writing
  now, while it is cheap.
