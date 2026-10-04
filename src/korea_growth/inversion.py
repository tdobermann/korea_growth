"""Inversions that make observed data an equilibrium.

``invert_amenities`` recovers the amenities Vbar_{d,t} that make an observed population
distribution the migration equilibrium of period t. With the population pinned, the rest of
the static equilibrium (wages, prices, incomes) does not depend on amenities, so the
inversion is exact: solve the economy at the observed L, then solve the logit for Vbar.
Amenities are identified up to a common scale (normalised: first region = 1).
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from .preferences import migration_values
from .solver import solve_static_equilibrium
from .types import ModelInputs, SolverOptions, StaticEquilibrium, sector_incomes


def invert_amenities(
    *,
    inputs: ModelInputs,
    t: int,
    L_prev: np.ndarray,
    L_target: np.ndarray,
    options: SolverOptions | None = None,
    tol: float = 1e-13,
    max_iter: int = 10_000,
) -> tuple[np.ndarray, StaticEquilibrium]:
    """Amenities Vbar_t (N,) under which ``L_target`` is the period-t equilibrium.

    Returns the amenities and the static equilibrium at ``L_target``.
    """

    L_target = np.asarray(L_target, dtype=float)
    eq = solve_static_equilibrium(inputs=inputs, t=t, L_prev=L_prev, options=options, fixed_L=L_target)

    exog = inputs.exog
    # Values with unit amenities; the amenity enters additively as log Vbar_d.
    unit = replace(exog, Vbar=np.ones_like(exog.Vbar))
    W0, _ = migration_values(
        t=t, dims=inputs.dims, params=inputs.params, exog=unit, L_prev=L_prev, y_pc=sector_incomes(eq), P=eq.P
    )
    nu = inputs.params.nu
    a = np.zeros(inputs.dims.N)
    for _ in range(max_iter):
        z = nu * (W0 + a[None, :])
        z -= z.max(axis=1, keepdims=True)
        mu = np.exp(z)
        mu /= mu.sum(axis=1, keepdims=True)
        L_hat = mu.T @ L_prev
        step = (np.log(L_target) - np.log(L_hat)) / nu
        a += step
        a -= a[0]
        if np.max(np.abs(step)) < tol:
            break
    else:
        raise RuntimeError("amenity inversion did not converge")
    return np.exp(a), eq
