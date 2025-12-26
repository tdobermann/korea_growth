"""Numerical solvers.

We solve the per-period static equilibrium as a fixed point:

    x = F(x)

with x = (w, r, P, E, taubar, pibar).

The mapping F is implemented in :func:`korea_growth.equilibrium.compute_implied_static`.

The dynamic equilibrium is obtained by solving sequentially over t=0...T-1
since the model uses lagged population L_{t-1} in agglomeration/congestion.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from .checks import validate_inputs
from .equilibrium import compute_implied_static
from .preferences import population_update
from .types import DynamicEquilibriumPath, ModelInputs, SolverOptions, StaticEquilibrium


def _geom_update(old: np.ndarray, new: np.ndarray, lam: float, eps: float) -> np.ndarray:
    """Geometric (log-space) damping update."""
    old = np.maximum(np.asarray(old, dtype=float), eps)
    new = np.maximum(np.asarray(new, dtype=float), eps)
    return np.exp((1.0 - lam) * np.log(old) + lam * np.log(new))


def _geom_update_scalar(old: float, new: float, lam: float, eps: float) -> float:
    return float(np.exp((1.0 - lam) * np.log(max(old, eps)) + lam * np.log(max(new, eps))))


def initial_guess(
    *,
    inputs: ModelInputs,
    t: int,
    L_prev: np.ndarray,
    taubar0: float = 0.05,
    pibar0: float = 0.10,
) -> dict:
    """Construct a conservative initial guess for a period-t solve."""

    dims = inputs.dims
    exog = inputs.exog

    N, J = dims.N, dims.J

    w0 = np.ones(N, dtype=float)
    r0 = np.ones(N, dtype=float)

    # Start price indices at (import price) => tautilde*ptilde (roughly)
    P0 = np.empty((N, J), dtype=float)
    for j in range(J):
        P0[:, j] = exog.tautilde[t, j, :] * exog.ptilde[t, j]

    # Compute implied L from migration at the guess (keeps things coherent)
    L0, _, _ = population_update(
        t=t,
        dims=dims,
        params=inputs.params,
        exog=exog,
        L_prev=L_prev,
        w=w0,
        P=P0,
        taubar=taubar0,
        pibar=pibar0,
    )

    y_pc0 = (1.0 - taubar0 + pibar0) * w0

    # Start expenditures at final consumption only (no intermediate demand yet)
    E0 = np.empty((N, J), dtype=float)
    for o in range(N):
        E0[o, :] = inputs.params.alpha_j * y_pc0[o] * L0[o]

    # Add a tiny floor so no sector has exactly 0 expenditure (helps cutoffs)
    E0 = np.maximum(E0, 1e-8)

    return {
        "w": w0,
        "r": r0,
        "P": P0,
        "E": E0,
        "taubar": float(taubar0),
        "pibar": float(pibar0),
    }


def solve_static_equilibrium(
    *,
    inputs: ModelInputs,
    t: int,
    L_prev: np.ndarray,
    guess: dict | None = None,
    options: SolverOptions | None = None,
) -> StaticEquilibrium:
    """Solve the static equilibrium at time t.

    Parameters
    ----------
    inputs:
        Model inputs (parameters + exogenous paths).
    t:
        Time index.
    L_prev:
        Lagged population distribution (N,).
    guess:
        Optional initial guess dict with keys: w,r,P,E,taubar,pibar.
    options:
        Solver options.
    """

    validate_inputs(inputs)

    opts = options or SolverOptions()

    dims = inputs.dims
    N, J = dims.N, dims.J
    eps = opts.eps

    if guess is None:
        guess = initial_guess(inputs=inputs, t=t, L_prev=L_prev)

    w = np.asarray(guess["w"], dtype=float).reshape(N)
    r = np.asarray(guess["r"], dtype=float).reshape(N)
    P = np.asarray(guess["P"], dtype=float).reshape(N, J)
    E = np.asarray(guess["E"], dtype=float).reshape(N, J)
    taubar = float(guess["taubar"])
    pibar = float(guess["pibar"])

    lam = float(opts.damping)

    last_max = np.inf
    for it in range(1, opts.max_iter + 1):
        implied = compute_implied_static(
            inputs=inputs,
            t=t,
            L_prev=L_prev,
            w=w,
            r=r,
            P=P,
            E=E,
            taubar=taubar,
            pibar=pibar,
            eps=eps,
        )

        max_res = implied.max_residual

        if opts.verbose and (it == 1 or it % 50 == 0 or max_res < opts.tol):
            print(f"[t={t}] iter={it:4d} max_res={max_res:.3e} damping={lam:.3f}")

        if max_res < opts.tol:
            # One final evaluation at the implied point (close the loop)
            implied2 = compute_implied_static(
                inputs=inputs,
                t=t,
                L_prev=L_prev,
                w=implied.w,
                r=implied.r,
                P=implied.P,
                E=implied.E,
                taubar=implied.taubar,
                pibar=implied.pibar,
                eps=eps,
            )
            return StaticEquilibrium(
                t=t,
                w=implied2.w,
                r=implied2.r,
                P=implied2.P,
                E=implied2.E,
                L=implied2.L,
                y_pc=implied2.y_pc,
                taubar=implied2.taubar,
                pibar=implied2.pibar,
                max_residual=implied2.max_residual,
                iters=it,
            )

        # Simple divergence safeguard: if residual increased a lot, reduce damping.
        if max_res > last_max * 1.2 and lam > opts.min_damping:
            lam = max(opts.min_damping, lam * 0.5)

        # Update guesses with geometric damping
        w = _geom_update(w, implied.w, lam=lam, eps=eps)
        r = _geom_update(r, implied.r, lam=lam, eps=eps)
        P = _geom_update(P, implied.P, lam=lam, eps=eps)
        E = _geom_update(E, implied.E, lam=lam, eps=eps)
        taubar = _geom_update_scalar(taubar, implied.taubar, lam=lam, eps=eps)
        pibar = _geom_update_scalar(pibar, implied.pibar, lam=lam, eps=eps)

        last_max = max_res

    raise RuntimeError(
        f"Static equilibrium did not converge at t={t} after {opts.max_iter} iterations. "
        f"Last max_residual={last_max:.3e}"
    )


def solve_dynamic_equilibrium(
    *,
    inputs: ModelInputs,
    options: SolverOptions | None = None,
    initial_guess_override: dict | None = None,
) -> DynamicEquilibriumPath:
    """Solve the full dynamic equilibrium path sequentially over time."""

    validate_inputs(inputs)

    opts = options or SolverOptions()

    dims = inputs.dims
    exog = inputs.exog

    T, N, J = dims.T, dims.N, dims.J

    w_path = np.zeros((T, N), dtype=float)
    r_path = np.zeros((T, N), dtype=float)
    P_path = np.zeros((T, N, J), dtype=float)
    E_path = np.zeros((T, N, J), dtype=float)
    L_path = np.zeros((T, N), dtype=float)
    y_path = np.zeros((T, N), dtype=float)
    taubar_path = np.zeros(T, dtype=float)
    pibar_path = np.zeros(T, dtype=float)

    iters = np.zeros(T, dtype=int)
    max_res = np.zeros(T, dtype=float)

    guess_t = initial_guess_override

    for t in range(T):
        L_prev = exog.L0 if t == 0 else L_path[t - 1, :]

        if guess_t is None:
            if t == 0:
                guess_t = initial_guess(inputs=inputs, t=t, L_prev=L_prev)
            else:
                # Warm-start from previous period
                guess_t = {
                    "w": w_path[t - 1, :].copy(),
                    "r": r_path[t - 1, :].copy(),
                    "P": P_path[t - 1, :, :].copy(),
                    "E": E_path[t - 1, :, :].copy(),
                    "taubar": float(taubar_path[t - 1]),
                    "pibar": float(pibar_path[t - 1]),
                }

        eq_t = solve_static_equilibrium(inputs=inputs, t=t, L_prev=L_prev, guess=guess_t, options=opts)

        w_path[t, :] = eq_t.w
        r_path[t, :] = eq_t.r
        P_path[t, :, :] = eq_t.P
        E_path[t, :, :] = eq_t.E
        L_path[t, :] = eq_t.L
        y_path[t, :] = eq_t.y_pc
        taubar_path[t] = eq_t.taubar
        pibar_path[t] = eq_t.pibar

        iters[t] = eq_t.iters
        max_res[t] = eq_t.max_residual

        # Warm start next period from this solution
        guess_t = {
            "w": eq_t.w.copy(),
            "r": eq_t.r.copy(),
            "P": eq_t.P.copy(),
            "E": eq_t.E.copy(),
            "taubar": float(eq_t.taubar),
            "pibar": float(eq_t.pibar),
        }

    return DynamicEquilibriumPath(
        w=w_path,
        r=r_path,
        P=P_path,
        E=E_path,
        L=L_path,
        y_pc=y_path,
        taubar=taubar_path,
        pibar=pibar_path,
        iters=iters,
        max_residual=max_res,
    )
