# Deciphering the Miracle on the Han

This repository contains a modular quantitative spatial general equilibrium model for
studying Korea's industrialization, internal migration, and rural spillovers during the
Heavy and Chemical Industrialization period.

The codebase is organized as a reusable Python package rather than a single prototype
script. The implemented model combines:

- non-homothetic household demand
- endogenous migration across regions
- sector-specific agglomeration from lagged population
- Melitz-style firm heterogeneity with bounded Pareto productivity draws
- input-output linkages across sectors
- policy wedges through productivity, fixed costs, subsidies, trade costs, migration costs,
  and foreign demand

## What Changed

Relative to the earlier toy policy exercise, the repository now includes:

- a 3-sector structure: `Agri`, `HeavyMnf`, `Services`
- a 5-region policy simulation: `Seoul`, `Busan`, `Changwon`, `Daegu`, `Rural`
- a 6-period HCI timeline mapped to `1965`, `1968`, `1973`, `1975`, `1980`, `1985`
- a revised HCI policy package calibrated directionally to the empirical draft in
  `docs/paper_draft05032026.pdf`
- a formal model primer in [docs/model.tex](/c:/korea_growth/docs/model.tex)
- improved test coverage for policy-direction checks and numerical edge cases

## Repository Layout

- [src/korea_growth/types.py](/c:/korea_growth/src/korea_growth/types.py): core dataclasses
  for dimensions, parameters, exogenous paths, and equilibrium outputs
- [src/korea_growth/preferences.py](/c:/korea_growth/src/korea_growth/preferences.py):
  household utility, expenditure shares, and migration
- [src/korea_growth/production.py](/c:/korea_growth/src/korea_growth/production.py):
  agglomeration and unit-cost bundles
- [src/korea_growth/distributions.py](/c:/korea_growth/src/korea_growth/distributions.py):
  bounded Pareto distribution primitives
- [src/korea_growth/trade.py](/c:/korea_growth/src/korea_growth/trade.py): firm cutoffs,
  price indices, and revenue blocks
- [src/korea_growth/equilibrium.py](/c:/korea_growth/src/korea_growth/equilibrium.py):
  static equilibrium mapping
- [src/korea_growth/solver.py](/c:/korea_growth/src/korea_growth/solver.py): damped
  fixed-point solver for static and dynamic equilibrium
- [src/korea_growth/checks.py](/c:/korea_growth/src/korea_growth/checks.py): input
  validation and parameter restrictions
- [scripts/solve_toy.py](/c:/korea_growth/scripts/solve_toy.py): minimal smoke-test model
- [scripts/simulate_policy_shock.py](/c:/korea_growth/scripts/simulate_policy_shock.py):
  baseline and HCI policy simulation
- [scripts/macro_scorecard.py](scripts/macro_scorecard.py): macro moments of the simulated
  economy against approximate Korean data, plus an initial-guess invariance check
- [docs/fresh_look.md](docs/fresh_look.md): diagnostics and a proposed re-architecture for
  the macro story, including how the township panel enters the model
- [docs/review_fresh_look.md](docs/review_fresh_look.md): consolidated referee report on the
  trade-closure fix (PR #4) and the "Matsuyama in space" proposal
- [docs/model.tex](/c:/korea_growth/docs/model.tex): formal background write-up of the
  implemented model

## Quick Start

```bash
pip install -e .
python scripts/solve_toy.py
python scripts/simulate_policy_shock.py
pytest -q
```

The scripts also insert `src/` into `sys.path`, so they run directly from a checkout.

## Toy Example

[scripts/solve_toy.py](/c:/korea_growth/scripts/solve_toy.py) builds a small synthetic economy:

- `N = 3` regions
- `J = 2` sectors
- `T = 2` periods

It solves the dynamic equilibrium path and prints wages, population shares, taxes,
profit rebates, and solver residuals.

## Main Policy Simulation

[scripts/simulate_policy_shock.py](/c:/korea_growth/scripts/simulate_policy_shock.py)
builds a richer economy:

- `N = 5` regions
- `J = 3` sectors
- `T = 6` periods

The baseline is then compared to an HCI policy package with four channels:

1. industrial-park support concentrated in `Changwon` and `Busan`
2. corridor-focused road improvements along the Seoul-Busan-Changwon axis
3. agricultural modernization strongest in middle-to-remote regions
4. rural service growth through lower service entry costs and higher local demand

The script prints a directional calibration summary and writes:

- `outputs/structural_transformation.png`
- `outputs/changwon_ip_mechanisms.png`
- `outputs/regional_policy_effects.png`
- `outputs/rural_spillovers.png`

## Current Calibration Intent

The HCI scenario is designed to move in the same direction as the empirical draft:

- lower aggregate agriculture share by 1985
- higher heavy-manufacturing share by 1985
- large wage and manufacturing gains in `Changwon`
- lower `Seoul` population share
- modest rural population retention and higher rural income
- positive service-sector gains in `Daegu` and `Rural`

This calibration is directional rather than a full structural estimation. The model is
best understood as a solver-ready quantitative framework that can be re-calibrated,
extended, or matched to richer data.

## Results Snapshot

**Baseline = Korea's 1965-85 structural transformation.** The baseline
(`scripts/korea_baseline.py`; 4 sectors: protected non-traded Rice, import-competing OtherAg,
Manufacturing, non-traded Services) is calibrated by `scripts/calibrate_history.py` to the
targets in `scripts/data_targets.py`. Every target carries its provenance; values marked * are
unverified approximations awaiting the digitised series.

| 1965 -> 1985 | data | baseline | targeted |
|---|---|---|---|
| agriculture employment share (workers) | 0.59* -> 0.25* | 0.605 -> 0.229 | yes |
| manufacturing value-added share | 0.15 -> 0.30 (paper draft, WDI) | 0.192 -> 0.298 | yes |
| real GDP per capita, double-deflated | x4* | x4.00 | yes |
| exports / GDP | 0.09* -> 0.33* | 0.078 -> 0.330 | yes |
| urban population share, 1980 | 0.57 (paper draft) | 0.547 | yes |
| urban population share, 1985 | 0.65* | 0.629 | no |
| agriculture value-added share | 0.38* -> 0.13* | 0.595 -> 0.239 | no: see below |

The 1965 population is an equilibrium (amenities are inverted), so urbanisation after 1965 is
generated by the model. Two known misses: the 1965 manufacturing share (the stylised
input-output matrix over-produces manufacturing), and the agricultural productivity gap (one
wage per region cannot make farm value added per worker much lower than non-farm). See
[docs/fresh_look.md](docs/fresh_look.md), section 2.6.

**HCI policy effects (1985, policy - baseline)** under this baseline:

| national sector share | gross output | value added | employment (workers) |
|---|---|---|---|
| agriculture | `-0.0262` | `-0.0325` | `-0.0378` |
| manufacturing | `-0.0120` | `-0.0131` | `-0.0255` |
| services | `+0.0382` | `+0.0456` | `+0.0633` |

- Changwon wage: `+0.3854`; Changwon manufacturing (gross-output) share: `+0.2919`
- Seoul population share: `-0.0785`; Rural population share: `+0.0422`
- Rural income per capita: `+0.2113`
- Rural / Daegu services (gross-output) share: `+0.1346` / `+0.0863`

The package now *lowers* the national manufacturing share: services are non-traded and absorb
the income gains, and the manufacturing final-demand weight sits at its calibration bound. The
directional test for this is marked as an expected failure until real input-output data replace
the stylised coefficients. The HCI package itself was tuned for the earlier 3-sector economy and
has not been re-tuned.

`python scripts/macro_scorecard.py` prints the full scorecard with data provenance and the list
of moments with no data in the repository.

## Theory Primer

The recommended entry point for the economics is
[docs/model.tex](/c:/korea_growth/docs/model.tex). It formalizes:

- household income, utility, and migration
- firm entry, exporting, and agricultural adoption cutoffs
- price indices, revenues, expenditures, and factor prices
- government budget balance and aggregate profit rebate
- the static equilibrium system solved each period
- the sequential dynamic solution over lagged population

## Using Your Own Data

Create a `korea_growth.types.ModelInputs` object containing:

- dimensions: time labels, region names, sector names
- parameters: `sigma`, `theta`, `kappa`, `xi`, `rho_j`, `iota`, `eta`, `nu`,
  `alpha_j`, `v_j`, and optionally `sigma_x` (aggregate elasticity of foreign demand for
  exports; default `sigma`), `fixed_costs_in_labor` (fixed costs as labour requirements), and
  `eps_occ` (occupation-choice elasticity; sector-specific wages, default one wage per
  location) with occupation wedges `b_occ` and `ModelDimensions.occupation_of_sector`
- exogenous paths: `A`, `F`, `Fbreve`, `Ftilde`, `s`, `tau`, `tautilde`,
  `delta`, `Vbar`, `H`, `Dtilde`, `ptilde`, `M`, the technology-share arrays, and optionally
  `nx_gdp` (net exports as a share of GDP; default balanced trade)

Then solve:

```python
from korea_growth.solver import solve_dynamic_equilibrium

path = solve_dynamic_equilibrium(inputs=inputs)
```

For a single period, use `solve_static_equilibrium`.

## Testing

The current tests cover:

- convergence of the toy model
- Walras's law, the resource constraint, and the government budget at the solution
- invariance of the equilibrium to the solver's initial guess, and an exogenous trade balance
- the nested entry/adoption/export choice (against brute force, and exporters/adopters as
  subsets of active firms) and the separate export demand elasticity
- the exact PIGL equivalent income, and agreement of migration and welfare with indirect utility
- sector accounts: employment in workers sums to population, value added sums to GDP
- the history calibration (targets within the achieved fit, observed 1965 population), and
  faster mechanisation diffusion under HCI
- internationally non-traded sectors and the amenity inversion
- occupation choice with sector-specific wages: the integrated limit, sector-level labour
  market clearing, the nested-logit shares and wage-gap decomposition, the welfare gradient,
  and guess invariance (`tests/test_occupation.py`)
- directional policy effects in the HCI simulation
- robustness of the production block when input-output matrices contain zero shares

Run:

```bash
pytest -q
```

## Notes

- The solver uses damped geometric updates in log space for numerical stability.
- The dynamic path is sequential because lagged population is the only endogenous state.
- Input validation enforces the share restrictions required by the implemented model.
- The dominant computational cost remains the sector-region trade block, which scales
  roughly with `O(J N^2)` per fixed-point iteration.

## Natural Next Extensions

- tighter calibration to the national sectoral shares in the paper
- richer migration heterogeneity by age or farm status
- more granular regional geography
- direct moment matching to the empirical tables rather than directional calibration
