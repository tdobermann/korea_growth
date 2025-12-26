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
```

The toy example creates a small (N=2 regions, J=2 sectors, T=2 periods) economy and runs the dynamic equilibrium solver.

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

