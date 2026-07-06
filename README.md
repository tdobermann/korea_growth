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

With the current `scripts/simulate_policy_shock.py` calibration, the 1985 policy-minus-baseline
comparison is:

- aggregate agriculture share: `-0.0413`
- aggregate heavy-manufacturing share: `+0.0570`
- aggregate services share: `-0.0157`
- Changwon wage: `+0.1436`
- Changwon manufacturing share: `+0.2293`
- Seoul population share: `-0.0258`
- Rural population share: `+0.0328`
- Rural income per capita: `+0.1986`
- Rural services share: `+0.1064`
- Daegu services share: `+0.1057`

These are directional diagnostics from the current calibration, not final estimated moments.
They reflect the corrected accounting described in [docs/model.tex](docs/model.tex) (land
rents rebated to residents, consistent subsidy accounting, fixed costs paid in labor,
infrastructure buying goods, and a net-foreign-transfer trade closure); the aggregate
heavy-manufacturing effect is now smaller than the earlier `+0.1269`, consistent with the
review's point that the previous number over-attributed the structural shift to policy.

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
  `alpha_j`, `v_j`
- exogenous paths: `A`, `F`, `Fbreve`, `Ftilde`, `s`, `tau`, `tautilde`,
  `delta`, `Vbar`, `H`, `Dtilde`, `ptilde`, `M`, and the technology-share arrays

Then solve:

```python
from korea_growth.solver import solve_dynamic_equilibrium

path = solve_dynamic_equilibrium(inputs=inputs)
```

For a single period, use `solve_static_equilibrium`.

## Testing

The current tests cover:

- convergence of the toy model
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
