r"""Household preferences, expenditure shares, and migration.

This module mirrors the household block in `baseline.py`:

- Indirect utility V(y, P)
- Non-homothetic expenditure shares psi_j(y, P)
- Migration shares mu_{o,d} and the implied population distribution L_t
"""

from __future__ import annotations

import numpy as np

from .types import ModelDimensions, ModelParameters, ModelExogenousPaths


def composite_price(P_row: np.ndarray, alpha_j: np.ndarray) -> float:
    r"""Compute \prod_j P_j^{alpha_j} in a numerically stable manner."""
    P_row = np.asarray(P_row, dtype=float)
    alpha_j = np.asarray(alpha_j, dtype=float)
    return float(np.exp(np.sum(alpha_j * np.log(P_row))))


def indirect_utility(
    y_pc: float,
    P_row: np.ndarray,
    alpha_j: np.ndarray,
    v_j: np.ndarray,
    eta: float,
) -> float:
    r"""Consumer indirect utility V.

    Matches `baseline.py`:

        V = 1/eta * (y / \prod_j P_j^{alpha_j})^{eta} - \sum_j v_j \log P_j

    with a continuous limit for eta -> 0.
    """

    prices = composite_price(P_row, alpha_j)
    nonhom = float(np.sum(v_j * np.log(P_row)))

    if abs(eta) < 1e-14:
        # limit: (y/prices)^eta ~ 1 + eta * log(y/prices)
        return float(np.log(y_pc / prices) - nonhom)

    return float((1.0 / eta) * (y_pc / prices) ** eta - nonhom)


def real_income_index(
    y_pc: float,
    P_row: np.ndarray,
    alpha_j: np.ndarray,
    v_j: np.ndarray,
) -> float:
    r"""Money-metric real-income index used for migration (model_review.md 2.3).

    Defined by

        log Y_d = log(y_pc / prod_j P_j^{alpha_j}) - sum_j v_j log P_j,

    i.e. Y_d = (y_pc / P_composite) * prod_j P_j^{-v_j}.

    This is the PIGL money-metric welfare in the log (eta -> 0) case and a positive,
    monotone transform of indirect utility otherwise. It is strictly positive for any
    y_pc > 0, which is what makes the migration shares well-defined; the previous code
    used the indirect utility V_d directly, which can be negative (then V_d^nu is not real
    and dividing by delta >= 1 raises utility). See model.tex, eq. (realincome).
    """

    prices = composite_price(P_row, alpha_j)
    nonhom = float(np.sum(v_j * np.log(P_row)))
    return float((y_pc / prices) * np.exp(-nonhom))


def expenditure_shares(
    y_pc: float,
    P_row: np.ndarray,
    alpha_j: np.ndarray,
    v_j: np.ndarray,
    eta: float,
) -> np.ndarray:
    r"""Vector of non-homothetic expenditure shares psi_j.

    Matches `baseline.py`:

        psi_j = alpha_j + v_j * (y / \prod_k P_k^{alpha_k})^{-eta}

    Notes
    -----
    Under the restriction sum_j alpha_j = 1 and sum_j v_j = 0, shares sum to 1.
    """

    prices = composite_price(P_row, alpha_j)
    scale = (y_pc / prices) ** (-eta) if abs(eta) >= 1e-14 else 1.0
    psi = alpha_j + v_j * scale
    return psi


def migration_shares(
    *,
    t: int,
    dims: ModelDimensions,
    params: ModelParameters,
    exog: ModelExogenousPaths,
    L_prev: np.ndarray,
    y_pc: np.ndarray,
    P: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute L_t from a given per-capita income vector and lagged population.

    This is the Gumbel-shock logit of model.tex 2.2 / eq. (mu): agents draw i.i.d.
    Gumbel taste shocks (scale 1/nu) and choose the destination maximizing an additively
    separable value whose real-income term is the *positive* money-metric index
    ``real_income_index`` (not the sign-ambiguous indirect utility). The resulting shares
    are

        mu_{o,d} propto (Vbar_d * L_{d,t-1}^iota * Y_d / delta_{o,d})^nu.

    Parameters
    ----------
    y_pc:
        Per-capita disposable income by region (N,), already including labor income, the
        profit rebate, local land rents, and any net foreign transfer.

    Returns
    -------
    (L_t, Yreal_d, U_common_d)
        L_t is the implied population, Yreal_d the real-income index per destination, and
        U_common_d = Vbar_d * g_d * Yreal_d the non-idiosyncratic value before origin costs.
    """

    N = dims.N

    # Destination real-income index Y_d (strictly positive).
    Yreal_d = np.empty(N, dtype=float)
    for d in range(N):
        Yreal_d[d] = real_income_index(y_pc[d], P[d, :], params.alpha_j, params.v_j)

    # Congestion term g_d = L_{d,t-1}^iota
    g_d = np.power(L_prev, params.iota)

    # Common component before origin-specific costs
    U_common_d = exog.Vbar[t, :] * g_d * Yreal_d  # (N,)

    # U_{o,d} = U_common_d / delta_{o,d}
    delta_od = exog.delta[t, :, :]  # (N,N)
    U_od = U_common_d[None, :] / delta_od

    # mu_{o,d} = U_{o,d}^nu / sum_d U_{o,d}^nu
    U_pow = np.power(U_od, params.nu)
    denom = U_pow.sum(axis=1, keepdims=True)
    mu_od = U_pow / denom

    # L_d = sum_o mu_{o,d} * L_prev_o
    L_t = (mu_od.T @ L_prev).reshape(-1)

    return L_t, Yreal_d, U_common_d


def population_update(
    *,
    t: int,
    dims: ModelDimensions,
    params: ModelParameters,
    exog: ModelExogenousPaths,
    L_prev: np.ndarray,
    w: np.ndarray,
    P: np.ndarray,
    taubar: float,
    pibar: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Convenience wrapper: build labor-only per-capita income and call ``migration_shares``.

    This omits land rents and the foreign transfer and is used only for constructing
    coherent solver initial guesses. The equilibrium mapping in ``equilibrium.py`` builds
    the full income (with land rents and the net foreign transfer) and calls
    ``migration_shares`` directly.
    """

    y_pc = (1.0 - taubar + pibar) * w  # (N,)
    return migration_shares(
        t=t, dims=dims, params=params, exog=exog, L_prev=L_prev, y_pc=y_pc, P=P
    )
