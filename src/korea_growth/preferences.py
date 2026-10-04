r"""Household preferences, expenditure shares, and migration.

This module mirrors the household block in `baseline.py`:

- Indirect utility V(y, P) and the exact PIGL equivalent income Y^eq
- Non-homothetic expenditure shares psi_j(y, P)
- Migration shares mu_{o,d}, the implied population distribution L_t, and welfare by
  origin (the inclusive value)
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


def log_equivalent_income(
    y_pc: float,
    P_row: np.ndarray,
    alpha_j: np.ndarray,
    v_j: np.ndarray,
    eta: float,
    P_ref: np.ndarray | None = None,
) -> float:
    r"""Log of the exact PIGL equivalent income at reference prices P_ref.

    Y^eq is the income that, at the reference price vector P_ref, attains the indirect
    utility V(y_pc, P_row) (Boppart 2014). Inverting V at P_ref gives

        Y^eq = P0 * [eta * (V + z0)]^(1/eta),   P0 = prod_j P_ref_j^alpha_j,
                                                 z0 = sum_j v_j log P_ref_j,

    and Y^eq = P0 * exp(V + z0) in the eta -> 0 limit. It is a monotone transform of V for
    every eta, so migration choices and welfare rank destinations the same way as V does,
    and its income elasticity is the PIGL one,
    d log Y^eq / d log x = x^eta / (x^eta - eta (z - z0)) with x = y_pc / P(P_row) and
    z = sum_j v_j log P_row_j.

    It replaces the index (y_pc / P) * exp(-z), which equals Y^eq only when eta -> 0 or
    z = z0 (docs/review_fresh_look.md 2.3). Default reference: unit sectoral prices (the
    foreign numeraire), so P0 = 1 and z0 = 0.

    V + z0 <= 0 means utility is below what any positive income attains at P_ref, i.e.
    Y^eq = 0; the bracket is floored at a tiny positive number so the log stays finite.
    """

    if P_ref is None:
        log_P0, z0 = 0.0, 0.0
    else:
        log_P0 = float(np.sum(np.asarray(alpha_j) * np.log(P_ref)))
        z0 = float(np.sum(np.asarray(v_j) * np.log(P_ref)))
    V = indirect_utility(y_pc, P_row, alpha_j, v_j, eta)
    if abs(eta) < 1e-14:
        return float(log_P0 + V + z0)
    bracket = max(eta * (V + z0), 1e-300)
    return float(log_P0 + np.log(bracket) / eta)


def log_equivalent_income_matrix(
    y: np.ndarray,
    P: np.ndarray,
    alpha_j: np.ndarray,
    v_j: np.ndarray,
    eta: float,
) -> np.ndarray:
    """Vectorised ``log_equivalent_income`` (unit reference prices) for incomes y (N, K)
    at location price rows P (N, J)."""
    logP = np.log(P)
    log_comp = logP @ np.asarray(alpha_j)  # (N,)
    z = logP @ np.asarray(v_j)  # (N,)
    log_x = np.log(np.asarray(y, dtype=float)) - log_comp[:, None]
    if abs(eta) < 1e-14:
        return log_x - z[:, None]
    V = np.exp(eta * log_x) / eta - z[:, None]
    return np.log(np.maximum(eta * V, 1e-300)) / eta


def equivalent_income(
    y_pc: float,
    P_row: np.ndarray,
    alpha_j: np.ndarray,
    v_j: np.ndarray,
    eta: float,
    P_ref: np.ndarray | None = None,
) -> float:
    """Exact PIGL equivalent income at reference prices (see ``log_equivalent_income``)."""
    return float(np.exp(log_equivalent_income(y_pc, P_row, alpha_j, v_j, eta, P_ref)))


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

    psi = raw_expenditure_shares(y_pc, P_row, alpha_j, v_j, eta)
    if np.any(psi < 0.0):
        # Outside the PIGL domain (income too low for the Engel shifters): a numerical guard
        # for transient solver iterates. ``checks.pigl_share_violation`` verifies that it does
        # not bind at a solved equilibrium.
        psi = np.maximum(psi, 0.0)
        psi = psi / psi.sum()
    return psi


def raw_expenditure_shares(
    y_pc: float,
    P_row: np.ndarray,
    alpha_j: np.ndarray,
    v_j: np.ndarray,
    eta: float,
) -> np.ndarray:
    """PIGL shares alpha_j + v_j (y / P)^(-eta) without the domain guard."""
    prices = composite_price(P_row, alpha_j)
    scale = (y_pc / prices) ** (-eta) if abs(eta) >= 1e-14 else 1.0
    return np.asarray(alpha_j) + np.asarray(v_j) * scale


def occupation_incomes(dims: ModelDimensions, y: np.ndarray) -> np.ndarray:
    """Per-worker income by occupation (N, O) from income by occupation (N, O), by sector
    (N, J; sectors of one occupation share it) or by location (N,)."""
    y = np.asarray(y, dtype=float)
    O, J = dims.O, dims.J
    if y.ndim == 1 or y.shape[1] == 1:  # one income per location
        return np.repeat(y.reshape(-1, 1), O, axis=1)
    if y.shape[1] == O:
        return y
    if y.shape[1] == J:
        first = [int(np.flatnonzero(dims.occ_idx == o)[0]) for o in range(O)]
        return y[:, first]
    raise ValueError(f"income array of shape {y.shape} matches neither O={O} nor J={J}")


def occupation_choice(
    *,
    t: int,
    dims: ModelDimensions,
    params: ModelParameters,
    exog: ModelExogenousPaths,
    y: np.ndarray,
    P: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Occupation shares, location inclusive values and equivalent incomes.

    ``y`` is per-worker income by occupation (N, O), by sector (N, J) or by location (N,).
    With ``params.eps_occ`` set (model.tex, eq. occshare),

        pi_{o|d}   = (b_do Y_do)^eps / sum_o' (b_do' Y_do')^eps,
        log Phi_d  = (1/eps) log sum_o (b_do Y_do)^eps,

    where Y_do is the PIGL equivalent income of y_do at location-d prices. With an
    integrated labour market (eps_occ None) incomes do not differ across occupations,
    log Phi_d = log Y_d, and the returned shares are uniform placeholders (employment is
    then set by labour demand, not by choice).

    Returns (pi (N, O), log_Phi (N,), log_Y (N, O)).
    """

    y_occ = occupation_incomes(dims, y)
    N, O = y_occ.shape
    log_Y = log_equivalent_income_matrix(y_occ, P, params.alpha_j, params.v_j, params.eta)
    if params.eps_occ is None:
        # Integrated market: every column carries the same income.
        return np.full((N, O), 1.0 / O), log_Y[:, 0], log_Y

    eps_occ = params.eps_occ
    log_b = np.zeros((N, O)) if exog.b_occ is None else np.log(exog.b_occ[t])
    z = eps_occ * (log_b + log_Y)
    zmax = z.max(axis=1, keepdims=True)
    ez = np.exp(z - zmax)
    pi = ez / ez.sum(axis=1, keepdims=True)
    log_Phi = (zmax[:, 0] + np.log(ez.sum(axis=1))) / eps_occ
    return pi, log_Phi, log_Y


def migration_values(
    *,
    t: int,
    dims: ModelDimensions,
    params: ModelParameters,
    exog: ModelExogenousPaths,
    L_prev: np.ndarray,
    y_pc: np.ndarray,
    P: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Deterministic values W_{o,d} of model.tex eq. (Wod) and the location term log Phi_d.

        W_{o,d} = log Vbar_d + iota log L_{d,t-1} + log Phi_d - log delta_{o,d},

    where log Phi_d is the occupation inclusive value (``occupation_choice``); with an
    integrated labour market it is log Y^eq_d. ``y_pc`` is (N,) or per-worker income by
    occupation (N, O) or sector (N, J). Migration shares and welfare are both built from these values, so they
    use the same expenditure function.
    """

    _, log_Phi, _ = occupation_choice(t=t, dims=dims, params=params, exog=exog, y=y_pc, P=P)
    W_common = np.log(exog.Vbar[t, :]) + params.iota * np.log(L_prev) + log_Phi  # (N,)
    W_od = W_common[None, :] - np.log(exog.delta[t, :, :])  # (N,N)
    return W_od, log_Phi


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
    separable value whose real-income term is the exact PIGL equivalent income
    ``equivalent_income`` (a positive, monotone transform of indirect utility). The
    resulting shares are

        mu_{o,d} propto (Vbar_d * L_{d,t-1}^iota * Y^eq_d / delta_{o,d})^nu.

    Parameters
    ----------
    y_pc:
        Per-capita disposable income by region (N,), already including labor income, the
        profit rebate, local land rents, and any net foreign transfer.

    Returns
    -------
    (L_t, Yeq_d, U_common_d)
        L_t is the implied population, Yeq_d the equivalent income per destination (the
        occupation inclusive value Phi_d with sector-specific wages), and
        U_common_d = Vbar_d * g_d * Yeq_d the non-idiosyncratic value before origin costs.
    """

    W_od, log_Y = migration_values(
        t=t, dims=dims, params=params, exog=exog, L_prev=L_prev, y_pc=y_pc, P=P
    )

    # mu_{o,d} = exp(nu W_od) / sum_d exp(nu W_od), computed stably in logs.
    z = params.nu * W_od
    z = z - z.max(axis=1, keepdims=True)
    ez = np.exp(z)
    mu_od = ez / ez.sum(axis=1, keepdims=True)

    # L_d = sum_o mu_{o,d} * L_prev_o
    L_t = (mu_od.T @ L_prev).reshape(-1)

    Yeq_d = np.exp(log_Y)
    U_common_d = exog.Vbar[t, :] * np.power(L_prev, params.iota) * Yeq_d
    return L_t, Yeq_d, U_common_d


def expected_utility(
    *,
    t: int,
    dims: ModelDimensions,
    params: ModelParameters,
    exog: ModelExogenousPaths,
    L_prev: np.ndarray,
    y_pc: np.ndarray,
    P: np.ndarray,
) -> np.ndarray:
    """Welfare by origin: the inclusive value of model.tex eq. (welfare).

        E U_o = (1/nu) log sum_d exp(nu W_{o,d}) + gamma_E / nu,

    built on the same W_{o,d} as ``migration_shares``, so d E U_o / d W_{o,d} = mu_{o,d}.
    With occupation choice, d E U_o / d log Y_{d,k} = mu_{o,d} pi_{k|d} (nested logit), k an
    occupation.
    """

    W_od, _ = migration_values(
        t=t, dims=dims, params=params, exog=exog, L_prev=L_prev, y_pc=y_pc, P=P
    )
    z = params.nu * W_od
    zmax = z.max(axis=1)
    lse = zmax + np.log(np.exp(z - zmax[:, None]).sum(axis=1))
    return (lse + np.euler_gamma) / params.nu


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
