"""Equilibrium mapping and residuals.

This module builds a *per-period* static equilibrium mapping of the form:

    x = F(x)

where x includes (w, r, P, E, taubar, pibar) at a fixed time t, taking the
lagged population L_{t-1} as given.

The fixed point is solved by the routines in `korea_growth.solver`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np

from .preferences import expenditure_shares, population_update
from .trade import SectorState, compute_sector_state
from .types import ModelInputs


@dataclass(frozen=True)
class StaticImplied:
    """Implied values computed from a guess of the static equilibrium variables."""

    # Core objects
    L: np.ndarray  # (N,)
    y_pc: np.ndarray  # (N,)

    w: np.ndarray  # (N,)
    r: np.ndarray  # (N,)
    P: np.ndarray  # (N, J)
    E: np.ndarray  # (N, J)
    taubar: float
    pibar: float

    # Diagnostics
    max_residual: float
    residuals: Dict[str, np.ndarray | float]


def compute_implied_static(
    *,
    inputs: ModelInputs,
    t: int,
    L_prev: np.ndarray,
    w: np.ndarray,
    r: np.ndarray,
    P: np.ndarray,
    E: np.ndarray,
    taubar: float,
    pibar: float,
    eps: float = 1e-14,
) -> StaticImplied:
    """Compute the implied static equilibrium mapping x -> F(x).

    All implied quantities are computed using the *current guess* (w,r,P,E,taubar,pibar).
    """

    dims = inputs.dims
    params = inputs.params
    exog = inputs.exog

    N, J = dims.N, dims.J

    # ------------------------------------------------------------
    # 1) Population given migration (depends on destination utility)
    # ------------------------------------------------------------
    L, _, _ = population_update(
        t=t,
        dims=dims,
        params=params,
        exog=exog,
        L_prev=L_prev,
        w=w,
        P=P,
        taubar=taubar,
        pibar=pibar,
    )

    # Per-capita disposable income (used in preferences, but also convenient for reporting)
    y_pc = (1.0 - taubar + pibar) * w

    # ------------------------------------------------------------
    # 2) Trade block for each sector: implied P and revenues
    # ------------------------------------------------------------
    sector_states: list[SectorState] = []
    P_implied = np.empty((N, J), dtype=float)

    # Revenues needed for intermediate demand + factor demands
    R_trad = np.zeros((N, J), dtype=float)
    R_breve = np.zeros((N, J), dtype=float)
    R_tilde = np.zeros((N, J), dtype=float)
    gross_output = np.zeros((N, J), dtype=float)

    num_firms = np.zeros((N, J), dtype=float)
    num_exporters = np.zeros((N, J), dtype=float)
    num_adopters = np.zeros((N, J), dtype=float)

    for j in range(J):
        st = compute_sector_state(
            t=t,
            j=j,
            dims=dims,
            params=params,
            exog=exog,
            L_prev=L_prev,
            w=w,
            r=r,
            P=P,
            E=E,
            eps=eps,
        )
        sector_states.append(st)
        P_implied[:, j] = st.P_implied

        R_trad[:, j] = st.R_trad
        R_breve[:, j] = st.R_breve
        R_tilde[:, j] = st.R_tilde
        gross_output[:, j] = st.gross_output

        num_firms[:, j] = st.num_firms
        num_exporters[:, j] = st.num_exporters
        num_adopters[:, j] = st.num_adopters

    # ------------------------------------------------------------
    # 3) Intermediate + final demand => implied expenditures E
    # ------------------------------------------------------------
    sigma = params.sigma

    # Variable costs by (o,j). For non-agriculture: vc = (sigma-1)/sigma * (R_domestic + R_export)
    vc_total = (sigma - 1.0) / sigma * (R_trad + R_breve + R_tilde)

    # For agriculture, we need two blocks (traditional vs new/export) because technology shares differ.
    vc_trad = (sigma - 1.0) / sigma * R_trad
    vc_new = (sigma - 1.0) / sigma * (R_breve + R_tilde)

    gamma_io_t = exog.gamma_io[t, :, :, :]  # (N,J,J)
    intermediate = np.einsum("ok,okj->oj", vc_total, gamma_io_t)

    agri_idx = dims.agri_idx
    if agri_idx is not None:
        gammabreve_io_t = exog.gammabreve_io[t, :, :, :]
        # Replace the agriculture-output-sector contribution
        old_contrib = vc_total[:, agri_idx][:, None] * gamma_io_t[:, agri_idx, :]
        new_contrib = (
            vc_trad[:, agri_idx][:, None] * gamma_io_t[:, agri_idx, :]
            + vc_new[:, agri_idx][:, None] * gammabreve_io_t[:, agri_idx, :]
        )
        intermediate = intermediate - old_contrib + new_contrib

    # Final consumption demand
    final_cons = np.empty((N, J), dtype=float)
    for o in range(N):
        psi = expenditure_shares(y_pc[o], P[o, :], params.alpha_j, params.v_j, params.eta)
        final_cons[o, :] = psi * y_pc[o] * L[o]

    E_implied = intermediate + final_cons

    # ------------------------------------------------------------
    # 4) Factor markets => implied (w, r)
    # ------------------------------------------------------------
    labor_payment = np.zeros(N, dtype=float)
    land_payment = np.zeros(N, dtype=float)

    beta_t = exog.beta[t, :, :]  # (N,J)
    gamma_t = exog.gamma[t, :, :]

    if agri_idx is not None:
        betabreve_t = exog.betabreve[t, :, :]
        gammabreve_t = exog.gammabreve[t, :, :]
    else:
        betabreve_t = None
        gammabreve_t = None

    for j in range(J):
        if agri_idx is not None and j == agri_idx:
            labor_payment += (1.0 - beta_t[:, j]) * gamma_t[:, j] * vc_trad[:, j]
            labor_payment += (1.0 - betabreve_t[:, j]) * gammabreve_t[:, j] * vc_new[:, j]

            land_payment += beta_t[:, j] * gamma_t[:, j] * vc_trad[:, j]
            land_payment += betabreve_t[:, j] * gammabreve_t[:, j] * vc_new[:, j]
        else:
            labor_payment += (1.0 - beta_t[:, j]) * gamma_t[:, j] * vc_total[:, j]
            land_payment += beta_t[:, j] * gamma_t[:, j] * vc_total[:, j]

    L_safe = np.maximum(L, eps)
    H_safe = np.maximum(exog.H[t, :], eps)

    w_implied = labor_payment / L_safe
    r_implied = land_payment / H_safe

    # ------------------------------------------------------------
    # 5) Profits, pibar and government budget
    # ------------------------------------------------------------
    wage_bill = float(np.sum(w * L))
    wage_bill = max(wage_bill, eps)

    profit = (1.0 / sigma) * gross_output - num_firms * exog.F[t, :, :] - num_exporters * exog.Ftilde[t, :, :] - num_adopters * exog.Fbreve[t, :, :]
    total_profit = float(np.sum(profit))
    pibar_implied = total_profit / wage_bill

    subsidy_spending = float(np.sum((sigma - 1.0) / sigma * exog.s[t, :, :] * gross_output))
    infra_spending = float(exog.tax_spending_on_building_H_and_roads[t])

    taubar_implied = (subsidy_spending + infra_spending) / wage_bill

    # ------------------------------------------------------------
    # Residuals (log deviations)
    # ------------------------------------------------------------
    def logdiff(x: np.ndarray, x_imp: np.ndarray) -> np.ndarray:
        return np.log(np.maximum(x, eps)) - np.log(np.maximum(x_imp, eps))

    res_w = logdiff(w, w_implied)
    res_r = logdiff(r, r_implied)
    res_P = logdiff(P, P_implied)
    res_E = logdiff(E, E_implied)

    res_taub = float(np.log(max(taubar, eps)) - np.log(max(taubar_implied, eps)))
    res_pib = float(np.log(max(pibar, eps)) - np.log(max(pibar_implied, eps)))

    max_res = float(
        max(
            np.max(np.abs(res_w)),
            np.max(np.abs(res_r)),
            np.max(np.abs(res_P)),
            np.max(np.abs(res_E)),
            abs(res_taub),
            abs(res_pib),
        )
    )

    residuals: Dict[str, np.ndarray | float] = {
        "w": res_w,
        "r": res_r,
        "P": res_P,
        "E": res_E,
        "taubar": res_taub,
        "pibar": res_pib,
        "max": max_res,
    }

    return StaticImplied(
        L=L,
        y_pc=y_pc,
        w=w_implied,
        r=r_implied,
        P=P_implied,
        E=E_implied,
        taubar=float(taubar_implied),
        pibar=float(pibar_implied),
        max_residual=max_res,
        residuals=residuals,
    )
