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

from .preferences import expenditure_shares, migration_shares
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

    # Aggregate accounting diagnostics (for Walras / trade-balance checks)
    aggregates: Dict[str, float]


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

    sigma = params.sigma
    agri_idx = dims.agri_idx

    # ------------------------------------------------------------
    # 1) Trade block for each sector: implied P and revenues
    #    (computed first because household income now needs the export/import totals)
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
    # 2) True factor cost (subsidy accounting; model_review.md 1.3)
    #    The subsidy lowers the firm's *effective* marginal cost but not the *true*
    #    resource cost. Factor income and intermediate demand equal the true factor cost
    #    TFC = (sigma-1)/(sigma*(1-s)) * revenue, NOT the firm's private outlay
    #    (sigma-1)/sigma * revenue. The government pays the difference s*TFC.
    # ------------------------------------------------------------
    s_t = exog.s[t, :, :]  # (N,J)
    one_minus_s = 1.0 - s_t
    tfc_scale = (sigma - 1.0) / sigma / one_minus_s  # (N,J)

    tfc_total = tfc_scale * (R_trad + R_breve + R_tilde)
    tfc_trad = tfc_scale * R_trad
    tfc_new = tfc_scale * (R_breve + R_tilde)

    # ------------------------------------------------------------
    # 3) Trade aggregates and the net foreign transfer (model_review.md 1.5)
    #    Exports earn EX from abroad; imports IM leak abroad. Once the other accounting
    #    leaks are closed, the household budget and the CES resource identity together
    #    force balanced trade, so the net foreign position must be carried into household
    #    income as a transfer T = IM - EX (a deficit is financed from abroad, a surplus is
    #    lent abroad). We distribute T proportional to pre-transfer income, i.e. as a
    #    uniform income scale factor. This is robustly positive (it stays feasible as long
    #    as net exports are smaller than income) and closes income = expenditure exactly.
    # ------------------------------------------------------------
    EX = float(np.sum(R_tilde))
    import_term = np.empty((N, J), dtype=float)
    for j in range(J):
        import_term[:, j] = np.power(exog.tautilde[t, j, :] * exog.ptilde[t, j], 1.0 - sigma)
    import_share = import_term / np.maximum(np.power(P, 1.0 - sigma), eps)  # (N,J)
    IM = float(np.sum(import_share * E))
    transfer = IM - EX

    # ------------------------------------------------------------
    # 4) Household income and population (inner fixed point for land rents per capita)
    #    Disposable income now includes local land rents r_o H_o / L_o (model_review.md 1.1)
    #    and the net foreign transfer. Per-capita land rent and the income-proportional
    #    transfer both depend on the migration-implied L, which depends on income, so a
    #    small inner fixed point is solved.
    # ------------------------------------------------------------
    H_t = exog.H[t, :]
    land_income = r * H_t  # (N,) region land rent r_o H_o
    labor_reb = (1.0 - taubar + pibar) * w  # (N,) labor income + rebate, per capita

    L = L_prev.copy()
    transfer_scale = 1.0
    for _ in range(500):
        ell = land_income / np.maximum(L, eps)
        base_pc = labor_reb + ell  # pre-transfer per-capita income
        income_base = float(np.sum(base_pc * L))
        # Uniform scale that distributes the transfer proportional to income.
        transfer_scale = max(1e-8, 1.0 + transfer / max(income_base, eps))
        y_pc = base_pc * transfer_scale
        L_new, _, _ = migration_shares(
            t=t, dims=dims, params=params, exog=exog, L_prev=L_prev, y_pc=y_pc, P=P
        )
        diff = float(np.max(np.abs(L_new - L)))
        if diff < 1e-14:
            L = L_new
            break
        # Arithmetic damping preserves the population sum (both L and L_new sum to the
        # total lagged population); geometric damping would not.
        L = 0.5 * L + 0.5 * L_new
    ell = land_income / np.maximum(L, eps)
    base_pc = labor_reb + ell
    income_base = float(np.sum(base_pc * L))
    transfer_scale = max(1e-8, 1.0 + transfer / max(income_base, eps))
    y_pc = base_pc * transfer_scale

    # ------------------------------------------------------------
    # 5) Intermediate + final + government demand => implied expenditures E
    # ------------------------------------------------------------
    gamma_io_t = exog.gamma_io[t, :, :, :]  # (N,J,J)
    intermediate = np.einsum("ok,okj->oj", tfc_total, gamma_io_t)

    if agri_idx is not None:
        gammabreve_io_t = exog.gammabreve_io[t, :, :, :]
        # Replace the agriculture-output-sector contribution (trad vs new tech shares)
        old_contrib = tfc_total[:, agri_idx][:, None] * gamma_io_t[:, agri_idx, :]
        new_contrib = (
            tfc_trad[:, agri_idx][:, None] * gamma_io_t[:, agri_idx, :]
            + tfc_new[:, agri_idx][:, None] * gammabreve_io_t[:, agri_idx, :]
        )
        intermediate = intermediate - old_contrib + new_contrib

    # Final consumption demand
    final_cons = np.empty((N, J), dtype=float)
    for o in range(N):
        psi = expenditure_shares(y_pc[o], P[o, :], params.alpha_j, params.v_j, params.eta)
        final_cons[o, :] = psi * y_pc[o] * L[o]

    # Government infrastructure demand: G^infra buys goods (model_review.md 1.4) rather than
    # vanishing. Default allocation: heavy-manufacturing + services (equal weights when both
    # present; whichever is present otherwise; expenditure shares as a last resort), spread
    # across regions by population share. Totals to G^infra since populations sum to 1.
    G_infra = float(exog.tax_spending_on_building_H_and_roads[t])
    sector_weights = np.zeros(J, dtype=float)
    infra_targets = [idx for idx in (dims.heavy_idx, dims.services_idx) if idx is not None]
    if infra_targets:
        for idx in infra_targets:
            sector_weights[idx] = 1.0 / len(infra_targets)
    else:
        sector_weights = np.asarray(params.alpha_j, dtype=float)
    E_gov = G_infra * L[:, None] * sector_weights[None, :]

    E_implied = intermediate + final_cons + E_gov

    # ------------------------------------------------------------
    # 6) Factor markets => implied (w, r)
    #    Factor income = labor/land share of true factor cost TFC; labor additionally
    #    receives the fixed-cost bill Phi^F (fixed costs are paid in local labor, not
    #    destroyed; model_review.md 1.2).
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
            labor_payment += (1.0 - beta_t[:, j]) * gamma_t[:, j] * tfc_trad[:, j]
            labor_payment += (1.0 - betabreve_t[:, j]) * gammabreve_t[:, j] * tfc_new[:, j]

            land_payment += beta_t[:, j] * gamma_t[:, j] * tfc_trad[:, j]
            land_payment += betabreve_t[:, j] * gammabreve_t[:, j] * tfc_new[:, j]
        else:
            labor_payment += (1.0 - beta_t[:, j]) * gamma_t[:, j] * tfc_total[:, j]
            land_payment += beta_t[:, j] * gamma_t[:, j] * tfc_total[:, j]

    F_t = exog.F[t, :, :]
    Ftilde_t = exog.Ftilde[t, :, :]
    Fbreve_t = exog.Fbreve[t, :, :]
    phi_fixed = np.sum(
        num_firms * F_t + num_exporters * Ftilde_t + num_adopters * Fbreve_t, axis=1
    )  # (N,) regional fixed-cost labor bill
    labor_payment += phi_fixed

    L_safe = np.maximum(L, eps)
    H_safe = np.maximum(H_t, eps)

    w_implied = labor_payment / L_safe
    r_implied = land_payment / H_safe

    # ------------------------------------------------------------
    # 7) Profits, pibar and government budget
    # ------------------------------------------------------------
    wage_bill = float(np.sum(w * L))
    wage_bill = max(wage_bill, eps)

    # Operating profit is Y/sigma; fixed costs are netted here and re-appear as labor
    # income above, so they are a transfer rather than a leak. Profits (hence pibar) may be
    # negative (model_review.md 2.4).
    profit = (1.0 / sigma) * gross_output - num_firms * F_t - num_exporters * Ftilde_t - num_adopters * Fbreve_t
    total_profit = float(np.sum(profit))
    pibar_implied = total_profit / wage_bill

    # Subsidy outlay uses the true factor cost (grossed up by 1/(1-s); model_review.md 1.3).
    subsidy_spending = float(np.sum(s_t * tfc_total))
    infra_spending = G_infra

    taubar_implied = (subsidy_spending + infra_spending) / wage_bill

    # ------------------------------------------------------------
    # Residuals
    # ------------------------------------------------------------
    def logdiff(x: np.ndarray, x_imp: np.ndarray) -> np.ndarray:
        return np.log(np.maximum(x, eps)) - np.log(np.maximum(x_imp, eps))

    res_w = logdiff(w, w_implied)
    res_r = logdiff(r, r_implied)
    res_P = logdiff(P, P_implied)
    res_E = logdiff(E, E_implied)

    # taubar and pibar are updated in levels (pibar can be negative), so their residuals
    # are arithmetic rather than log deviations (model_review.md 2.4).
    res_taub = float(taubar - taubar_implied)
    res_pib = float(pibar - pibar_implied)

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

    # Aggregate accounting diagnostics for Walras / trade-balance checks.
    income_independent = (1.0 - taubar + pibar) * float(np.sum(w * L)) + float(np.sum(land_income)) + transfer
    expenditure_final = float(np.sum(final_cons))
    aggregates: Dict[str, float] = {
        "gross_output": float(np.sum(gross_output)),
        "absorption": float(np.sum(E_implied)),
        "EX": EX,
        "IM": IM,
        "transfer": transfer,
        # Resource constraint: sum(Y) == sum(E) + EX - IM (CES bookkeeping).
        "resource_residual": float(np.sum(gross_output)) - (float(np.sum(E_implied)) + EX - IM),
        # Income == final expenditure (guards land-rent / transfer inclusion).
        "income": income_independent,
        "expenditure_final": expenditure_final,
        "income_minus_expenditure": income_independent - expenditure_final,
        # Government budget: tau*W == subsidies + infra.
        "gov_budget_residual": taubar_implied * wage_bill - (subsidy_spending + infra_spending),
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
        aggregates=aggregates,
    )
