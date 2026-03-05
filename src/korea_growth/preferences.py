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
    """Compute L_t given (w_t, P_t) and lagged population.

    Returns
    -------
    (L_t, V_d, U_common_d)

    where:
    - V_d is destination-specific indirect utility
    - U_common_d = Vbar_d * g_d * V_d is the non-idiosyncratic component before dividing by delta_{o,d}
    """

    N, J = dims.N, dims.J

    # Per-capita disposable income
    y_pc = (1.0 - taubar + pibar) * w  # (N,)

    # Destination-specific utility V_d
    V_d = np.empty(N, dtype=float)
    for d in range(N):
        V_d[d] = indirect_utility(y_pc[d], P[d, :], params.alpha_j, params.v_j, params.eta)

    # Congestion term g_d = L_{d,t-1}^iota
    g_d = np.power(L_prev, params.iota)

    # Common component before origin-specific costs
    U_common_d = exog.Vbar[t, :] * g_d * V_d  # (N,)

    # U_{o,d} = U_common_d / delta_{o,d}
    delta_od = exog.delta[t, :, :]  # (N,N)
    U_od = U_common_d[None, :] / delta_od

    # mu_{o,d} = U_{o,d}^nu / sum_d U_{o,d}^nu
    U_pow = np.power(U_od, params.nu)
    denom = U_pow.sum(axis=1, keepdims=True)
    mu_od = U_pow / denom

    # L_d = sum_o mu_{o,d} * L_prev_o
    L_t = (mu_od.T @ L_prev).reshape(-1)

    return L_t, V_d, U_common_d
