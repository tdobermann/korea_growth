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

from .preferences import expenditure_shares, migration_shares, occupation_choice
from .trade import SectorState, compute_sector_state
from .types import ModelInputs


@dataclass(frozen=True)
class StaticImplied:
    """Implied values computed from a guess of the static equilibrium variables."""

    # Core objects
    L: np.ndarray  # (N,)
    y_pc: np.ndarray  # (N,) average per-capita income

    w: np.ndarray  # (N, J) implied wages by location and sector
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

    # Sector-specific labour market at the current guess
    L_sector: np.ndarray  # (N, J) employment
    y_sector: np.ndarray  # (N, J) per-worker income


def _transfer_scale(transfer: float, income_base: float, t: int, eps: float) -> float:
    """Uniform income scale 1 + T / Y_base that distributes the foreign transfer.

    A surplus target larger than pre-transfer income is infeasible; raise rather than
    floor the scale (a floor would silently miss the NX target).
    """
    scale = 1.0 + transfer / max(income_base, eps)
    if not scale > 0.0:
        raise ValueError(
            f"Infeasible trade-balance target at t={t}: the net-export surplus "
            f"{-transfer:.4g} exceeds pre-transfer household income {income_base:.4g}."
        )
    return scale


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
    fixed_L: Optional[np.ndarray] = None,
) -> StaticImplied:
    """Compute the implied static equilibrium mapping x -> F(x).

    ``fixed_L`` pins the population instead of solving migration (used to invert amenities:
    with L given, the rest of the equilibrium does not depend on them).

    All implied quantities are computed using the *current guess* (w,r,P,E,taubar,pibar).
    ``w`` is (N, J) (wages by location and sector) or (N,) (one wage per location).
    """

    dims = inputs.dims
    params = inputs.params
    exog = inputs.exog

    N, J = dims.N, dims.J

    sigma = params.sigma
    agri_idx = dims.agri_idx
    segmented = params.eps_occ is not None
    # Occupations: with an integrated market a single one; otherwise sectors map onto
    # occupations (dims.occupation_of_sector), which each have one wage per location.
    occ = dims.occ_idx if segmented else np.zeros(J, dtype=int)
    O = int(occ.max()) + 1
    members = [np.flatnonzero(occ == o) for o in range(O)]

    w = np.asarray(w, dtype=float)
    if w.ndim == 1:
        w = np.repeat(w[:, None], J, axis=1)
    # Wage by (location, occupation); sectors of an occupation pay its wage.
    w_occ = np.stack([w[:, m].mean(axis=1) for m in members], axis=1)  # (N, O)
    w = w_occ[:, occ]

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

    fixed_bill = np.zeros((N, J), dtype=float)  # fixed costs paid, numeraire units

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

        fixed_bill[:, j] = st.fixed_cost_bill

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
    # 3) Intermediate demand (depends only on TFC; needed here for GDP)
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

    # ------------------------------------------------------------
    # 4) Trade closure (model_review.md 1.5; docs/fresh_look.md section 2.1)
    #    Households receive a net foreign transfer T that finances the trade deficit. T must
    #    be pinned exogenously. Income = expenditure and goods-market clearing already imply
    #    T = IM - EX at any fixed point, so the previous closure (T = IM - EX evaluated at the
    #    current guess) dropped the one condition tying domestic prices to the foreign
    #    numeraire and admitted a continuum of equilibria indexed by the trade deficit. We set
    #    T = -NX*, with NX* = nx_gdp_t * GDP (default: balanced trade), so EX - IM = NX* holds
    #    at the solution. T is distributed proportional to pre-transfer income (a uniform
    #    scale factor that keeps per-capita income positive).
    #    Placeholder: T is consumed. Korea's 1960s-70s foreign saving financed capital
    #    formation, so once capital enters the deficit belongs in the investment identity
    #    (docs/review_fresh_look.md 1.3 item 3).
    # ------------------------------------------------------------
    gdp = float(np.sum(gross_output) - np.sum(intermediate))
    nx_target = (0.0 if exog.nx_gdp is None else float(exog.nx_gdp[t])) * gdp

    EX = float(np.sum(R_tilde))
    import_term = np.empty((N, J), dtype=float)
    for j in range(J):
        if exog.is_nontraded(j):
            import_term[:, j] = 0.0
        else:
            import_term[:, j] = np.power(exog.tautilde[t, j, :] * exog.ptilde[t, j], 1.0 - sigma)
    import_share = import_term / np.maximum(np.power(P, 1.0 - sigma), eps)  # (N,J)
    IM = float(np.sum(import_share * E))
    transfer = -nx_target

    # ------------------------------------------------------------
    # 5) Household income and population (inner fixed point for land rents per capita)
    #    Disposable income now includes local land rents r_o H_o / L_o (model_review.md 1.1)
    #    and the net foreign transfer. Per-capita land rent and the income-proportional
    #    transfer both depend on the migration-implied L, which depends on income, so a
    #    small inner fixed point is solved.
    # ------------------------------------------------------------
    H_t = exog.H[t, :]
    land_income = r * H_t  # (N,) region land rent r_o H_o
    labor_reb = (1.0 - taubar + pibar) * w_occ  # (N,O) labour income + rebate, per worker

    def incomes(L_cur: np.ndarray):
        """Per-worker income y_do and workers by (location, occupation) given L.

        With occupation choice the workers are pi_{o|d} L_d, and pi depends on income, which
        depends on per-capita land rent (hence on L): a short inner fixed point in pi. With an
        integrated market there is one occupation and pi = 1.
        """
        ell = land_income / np.maximum(L_cur, eps)
        base = labor_reb + ell[:, None]  # pre-transfer income per worker
        pi = np.full((N, O), 1.0 / O)
        for _ in range(200 if segmented else 1):
            weights = pi * L_cur[:, None]
            income_base = float(np.sum(base * weights))
            scale = _transfer_scale(transfer, income_base, t, eps)
            y = base * scale
            if not segmented:
                break
            pi_new, _, _ = occupation_choice(t=t, dims=dims, params=params, exog=exog, y=y, P=P)
            if float(np.max(np.abs(pi_new - pi))) < 1e-15:
                pi = pi_new
                break
            pi = pi_new
        return y, pi * L_cur[:, None]

    L = L_prev.copy() if fixed_L is None else np.asarray(fixed_L, dtype=float)
    for _ in range(0 if fixed_L is not None else 500):
        y_cur, _ = incomes(L)
        L_new, _, _ = migration_shares(
            t=t, dims=dims, params=params, exog=exog, L_prev=L_prev, y_pc=y_cur, P=P
        )
        diff = float(np.max(np.abs(L_new - L)))
        if diff < 1e-14:
            L = L_new
            break
        # Arithmetic damping preserves the population sum (both L and L_new sum to the
        # total lagged population); geometric damping would not.
        L = 0.5 * L + 0.5 * L_new
    y_occ, weights = incomes(L)  # workers by (location, occupation), sum_o = L_d
    y_pc = np.sum(y_occ * weights, axis=1) / np.maximum(L, eps)
    y_sector = y_occ[:, occ]

    # ------------------------------------------------------------
    # 6) Intermediate + final + government demand => implied expenditures E
    # ------------------------------------------------------------
    # Final consumption: PIGL demand aggregates exactly over the income groups (location,
    # occupation), each with its own expenditure shares.
    final_cons = np.zeros((N, J), dtype=float)
    for o in range(N):
        for g in range(O):
            psi = expenditure_shares(y_occ[o, g], P[o, :], params.alpha_j, params.v_j, params.eta)
            final_cons[o, :] += psi * y_occ[o, g] * weights[o, g]

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
    # 7) Factor markets => implied (w, r)
    #    Factor income = labor/land share of true factor cost TFC; labor additionally
    #    receives the fixed-cost bill Phi^F (fixed costs are paid in local labor, not
    #    destroyed; model_review.md 1.2).
    # ------------------------------------------------------------
    labor_payment = np.zeros((N, J), dtype=float)  # by (location, sector)
    land_payment = np.zeros(N, dtype=float)

    beta_t = exog.beta[t, :, :]  # (N,J)
    gamma_t = exog.gamma[t, :, :]

    for j in range(J):
        if agri_idx is not None and j == agri_idx:
            betabreve_t = exog.betabreve[t, :, :]
            gammabreve_t = exog.gammabreve[t, :, :]
            labor_payment[:, j] = (
                (1.0 - beta_t[:, j]) * gamma_t[:, j] * tfc_trad[:, j]
                + (1.0 - betabreve_t[:, j]) * gammabreve_t[:, j] * tfc_new[:, j]
            )
            land_payment += beta_t[:, j] * gamma_t[:, j] * tfc_trad[:, j]
            land_payment += betabreve_t[:, j] * gammabreve_t[:, j] * tfc_new[:, j]
        else:
            labor_payment[:, j] = (1.0 - beta_t[:, j]) * gamma_t[:, j] * tfc_total[:, j]
            land_payment += beta_t[:, j] * gamma_t[:, j] * tfc_total[:, j]

    # Fixed costs are paid to labour of the same location and sector.
    labor_payment += fixed_bill

    H_safe = np.maximum(H_t, eps)
    # Each (location, occupation) labour market clears at its own wage: supply
    # S_do = pi_{o|d} L_d, demand D_do = sum_{k in o} payments_dk / w_do. Inverting supply
    # (w = payments / S) gives a map with slope ~ -eps_occ, which damping cannot stabilise
    # for large eps_occ. Instead: the location wage level clears total labour
    # (sum_o w_do S_do = sum payments, which is the whole condition with one occupation), and
    # relative wages take a log-Newton step on excess demand, log(D/S) / (1 + eps_occ), exact
    # when equivalent income is linear in the wage. A fixed point has D = S in every
    # occupation; as eps_occ -> infinity relative wages stay at one (integrated limit).
    pay_occ = np.stack([labor_payment[:, m].sum(axis=1) for m in members], axis=1)  # (N,O)
    S = np.maximum(weights, eps)
    w_bar_implied = pay_occ.sum(axis=1) / np.maximum(L, eps)
    if segmented:
        D = pay_occ / np.maximum(w_occ, eps)
        w_bar = np.sum(w_occ * S, axis=1) / np.maximum(L, eps)
        omega = w_occ / w_bar[:, None]
        omega_new = omega * np.power(np.maximum(D, eps) / S, 1.0 / (1.0 + params.eps_occ))
        omega_new = omega_new / (np.sum(omega_new * S, axis=1) / np.maximum(L, eps))[:, None]
        w_occ_implied = w_bar_implied[:, None] * omega_new
    else:
        w_occ_implied = w_bar_implied[:, None]
    w_implied = w_occ_implied[:, occ]  # (N, J)
    # Employment by sector: labour demanded at the occupation wage. At a fixed point it sums,
    # within each occupation, to the workers who chose it.
    L_sector = labor_payment / np.maximum(w_implied, eps)
    r_implied = land_payment / H_safe

    # ------------------------------------------------------------
    # 8) Profits, pibar and government budget
    # ------------------------------------------------------------
    wage_bill = float(np.sum(w_occ * weights))
    wage_bill = max(wage_bill, eps)

    # Operating profit is Y/sigma; fixed costs are netted here and re-appear as labor
    # income above, so they are a transfer rather than a leak. Profits (hence pibar) may be
    # negative (model_review.md 2.4).
    profit = (1.0 / sigma) * gross_output - fixed_bill
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
    income_independent = (1.0 - taubar + pibar) * wage_bill + float(np.sum(land_income)) + transfer
    expenditure_final = float(np.sum(final_cons))
    aggregates: Dict[str, float] = {
        "gross_output": float(np.sum(gross_output)),
        "absorption": float(np.sum(E_implied)),
        "EX": EX,
        "IM": IM,
        "GDP": gdp,
        "NX": EX - IM,
        "transfer": transfer,
        # Trade closure: EX - IM == NX* (an equilibrium condition, not an identity).
        "nx_residual": (EX - IM) - nx_target,
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
        L_sector=L_sector,
        y_sector=y_sector,
    )
