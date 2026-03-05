# Deciphering the Miracle on the Han

This repo is a **solver-ready** and **modular** implementation of the Korea spatial GE model.

It is a refactor of the original `baseline.py` into a package that is suitable for a Git workflow:

- Clear module boundaries (`preferences`, `production`, `trade`, `equilibrium`, `solver`)
- Dataclasses for model inputs and results
- A robust (damped) fixed-point solver for the per-period static equilibrium
- A sequential solver for the dynamic path when the only state is lagged population

## Quick start

```bash
pip install -e .
python scripts/solve_toy.py
python scripts/simulate_policy_shock.py
```

The toy example creates a small (N=3 regions, J=2 sectors, T=2 periods) economy and runs the dynamic equilibrium solver.

The policy simulation script creates a (N=3 regions, J=2 sectors, T=5 periods) economy, applies a large **Busan-only, agriculture-only** industrial policy at `t=4`, and writes comparison plots to:

- `outputs/target_policy_mechanisms.png`
- `outputs/regional_policy_effects.png`
- `outputs/exports_and_sectoral_shares.png`

The policy channels from `t>=4` are:

- Agri subsidy in Busan: `s` rises to `0.35`
- Agri productivity in Busan: `A` is multiplied by `1.20`
- Agri fixed cost in Busan: `F` is multiplied by `0.55`
- Agri outbound trade costs from Busan: `tau` to non-Busan destinations falls from `1.20` to `1.05`

## Where to plug in your data

Create a `korea_growth.types.ModelInputs` object with:

- **Dimensions**: times, region names, sector names
- **Parameters**: (sigma, theta, kappa, xi, rho_j, iota, eta, nu, alpha_j, v_j)
- **Exogenous/policy paths**: arrays for productivity, fixed costs, subsidies, trade/migration costs, amenities, etc.

Then call:

```python
from korea_growth.solver import solve_dynamic_equilibrium
path = solve_dynamic_equilibrium(inputs)
```

## Notes

- The solver is written to be numerically robust, but you may need to tune damping and initial guesses for large-scale calibrations.
- For scale: the implementation avoids O(N^3) patterns in the original code by vectorizing the costly trade blocks; the remaining dominant complexity is O(J N^2) per fixed-point iteration.
