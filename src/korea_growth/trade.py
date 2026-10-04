"""Trade block: price indices, revenues, cutoffs.

This module provides a vectorized implementation of the expensive parts of the
prototype `baseline.py`:

- Entry/export/adoption cutoffs (phi-bar, phi-tilde, phi-breve), from a nested discrete
  choice (exporters and adopters are active firms)
- CES-relevant productivity aggregates (Zbar, Ztilde, Zbreve)
- Domestic price indices P_{d,j}
- Domestic revenues and export revenues

The core workhorse is :func:`compute_sector_state` which computes all objects
for a single (t, j) sector across all regions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy.optimize import brentq

from .distributions import integral_phi_sigma_minus_1, pareto_survival
from .production import agglomeration, unit_cost_bundle
from .types import ModelDimensions, ModelParameters, ModelExogenousPaths


@dataclass(frozen=True)
class SectorState:
    """Precomputed sector objects at (t, j) for all regions."""

    j: int

    # Costs
    C: np.ndarray  # (N,)
    CBREVE: Optional[np.ndarray]  # (N,) or None

    # Cutoffs
    phi_bar: np.ndarray  # (N,)
    phi_breve: Optional[np.ndarray]  # (N,) or None
    phi_tilde: np.ndarray  # (N,)

    # Productivity aggregates
    Zbar: np.ndarray  # (N,)
    Zbreve: Optional[np.ndarray]  # (N,) or None
    Ztilde: np.ndarray  # (N,)

    # Price index implied by the trade block
    P_implied: np.ndarray  # (N,)

    # Revenues
    R_trad: np.ndarray  # (N,)
    R_breve: np.ndarray  # (N,)
    R_tilde: np.ndarray  # (N,)
    R_domestic_total: np.ndarray  # (N,)
    gross_output: np.ndarray  # (N,)

    # Counts
    num_firms: np.ndarray  # (N,)
    num_exporters: np.ndarray  # (N,)
    num_adopters: np.ndarray  # (N,)

    # Optional diagnostics
    S_o: np.ndarray  # (N,) demand shifter used in cutoffs and domestic revenues
    B_domestic: np.ndarray  # (N,) sum over domestic varieties of factory-gate p^(1-sigma)
    D_export: float  # effective foreign demand shifter (= Dtilde when sigma_x = sigma)

    # Fixed costs per firm in numeraire units (N,)
    F_cost: np.ndarray
    Fbreve_cost: np.ndarray
    Ftilde_cost: np.ndarray

    @property
    def fixed_cost_bill(self) -> np.ndarray:
        """Regional fixed-cost bill (N,): paid to local labour."""
        return (
            self.num_firms * self.F_cost
            + self.num_exporters * self.Ftilde_cost
            + self.num_adopters * self.Fbreve_cost
        )


def nested_cutoffs(slopes: np.ndarray, costs: np.ndarray, *, sigma: float) -> np.ndarray:
    """Productivity thresholds of a nested discrete choice with profits linear in phi^(sigma-1).

    Option k (k = 0..K, row k) yields profit ``slopes[k] * x - costs[k]`` with
    x = phi^(sigma-1). Row 0 is exit (zero slope and cost); slopes and costs are ordered so
    that higher options are weakly more expensive. The firm picks the upper envelope, whose
    option index is nondecreasing in x, so "choose an option >= k" is the set x >= X_k with

        X_k = min_{k' >= k} max_{i < k'} (costs[k'] - costs[i]) / (slopes[k'] - slopes[i]),

    the crossing being +inf when option k' never beats i. Returns phi_k =
    max(1, X_k^(1/(sigma-1))) for k = 0..K (row 0 is 1), shape (K+1, N).
    """

    slopes = np.asarray(slopes, dtype=float)
    costs = np.asarray(costs, dtype=float)
    K1 = slopes.shape[0]
    lo = np.zeros_like(slopes)
    for k in range(1, K1):
        cross = np.full(slopes.shape[1:], -np.inf)
        for i in range(k):
            ds = slopes[k] - slopes[i]
            dc = costs[k] - costs[i]
            with np.errstate(divide="ignore", invalid="ignore"):
                c_ik = np.where(ds > 0.0, dc / np.where(ds > 0.0, ds, 1.0), np.inf)
            cross = np.maximum(cross, c_ik)
        lo[k] = cross
    X = np.minimum.accumulate(lo[::-1], axis=0)[::-1]
    X[0] = 0.0
    with np.errstate(over="ignore"):
        phi = np.power(np.maximum(X, 0.0), 1.0 / (sigma - 1.0))
    return np.maximum(1.0, phi)


def compute_sector_state(
    *,
    t: int,
    j: int,
    dims: ModelDimensions,
    params: ModelParameters,
    exog: ModelExogenousPaths,
    L_prev: np.ndarray,
    w: np.ndarray,
    r: np.ndarray,
    P: np.ndarray,
    E: np.ndarray,
    eps: float = 1e-14,
) -> SectorState:
    """Compute all trade objects for a given time t and sector j.

    Parameters
    ----------
    t, j:
        Time and sector index.
    L_prev:
        Lagged population (N,).
    w, r:
        Wages (N,) or by location and sector (N, J); land rents (N,).
    P, E:
        Current guess of price indices and expenditures (N, J).
    eps:
        Numerical floor.
    """

    sigma, theta, kappa, xi = params.sigma, params.theta, params.kappa, params.xi
    N = dims.N

    is_agri = (dims.agri_idx is not None) and (j == dims.agri_idx)

    # Exogenous objects at (t,j)
    M_j = float(exog.M[t, j])
    tau_j = exog.tau[t, j, :, :]  # (N,N)
    tau_pow = np.power(tau_j, 1.0 - sigma)  # (N,N)

    s_o = exog.s[t, :, j]  # (N,)

    A_o = exog.A[t, :, j]
    beta_o = exog.beta[t, :, j]
    gamma_o = exog.gamma[t, :, j]
    gamma_io_o = exog.gamma_io[t, :, j, :]  # (N,J)

    # Sector-j wage: firms hire labour in their own sector (w is (N,) with an integrated
    # labour market, (N, J) with sector-specific wages).
    w = np.asarray(w, dtype=float)
    w_j = w[:, j] if w.ndim == 2 else w

    # Fixed costs in numeraire units (labour requirements times the local wage if
    # params.fixed_costs_in_labor).
    fc_unit = w_j if params.fixed_costs_in_labor else 1.0
    F_o = exog.F[t, :, j] * fc_unit
    Fbreve_o = exog.Fbreve[t, :, j] * fc_unit
    Ftilde_o = exog.Ftilde[t, :, j] * fc_unit

    tautilde_o = exog.tautilde[t, j, :]
    Dtilde_j = float(exog.Dtilde[t, j])
    ptilde_j = float(exog.ptilde[t, j])

    # Agglomeration term f_{o,j} = L_{o,t-1}^{rho_j}
    f_o = agglomeration(L_prev, float(params.rho_j[j]))

    # Unit cost for domestic production
    C_o = unit_cost_bundle(r=r, w=w_j, P=P, beta=beta_o, gamma=gamma_o, gamma_io=gamma_io_o)

    # Unit cost and shares for new tech (only matters for agriculture)
    if is_agri:
        betabreve_o = exog.betabreve[t, :, j]
        gammabreve_o = exog.gammabreve[t, :, j]
        gammabreve_io_o = exog.gammabreve_io[t, :, j, :]
        CBREVE_o = unit_cost_bundle(r=r, w=w_j, P=P, beta=betabreve_o, gamma=gammabreve_o, gamma_io=gammabreve_io_o)
    else:
        betabreve_o = None
        gammabreve_o = None
        gammabreve_io_o = None
        CBREVE_o = None

    # Demand shifter S_o = sum_d tau_{o,d}^{1-sigma} * P_{d,j}^{sigma-1} * E_{d,j}
    demand_dest = np.power(P[:, j], sigma - 1.0) * E[:, j]  # (N,)
    S_o = tau_pow @ demand_dest
    S_o = np.maximum(S_o, eps)

    # -------- Nested entry / adoption / export choice --------
    # Variable profit of a firm with draw phi is linear in x = phi^(sigma-1) under every
    # option, so each option is a line (slope a, fixed cost c) in x, and a firm picks the
    # upper envelope. Options are nested: a firm must be active (pay F) to adopt or export,
    # and in agriculture exporters use the mechanised technology (the xi and CBREVE terms in
    # the export block), so exporting also requires adoption (pay Fbreve). The earlier code
    # computed each cutoff from its own pairwise zero-profit condition, so that whenever
    # phi_tilde or phi_breve fell below phi_bar, firms exported or adopted without entering
    # (docs/fresh_look.md 2.4; docs/review_fresh_look.md 1.3 item 6).
    K0 = np.power((sigma / (sigma - 1.0)) * (1.0 - s_o), 1.0 - sigma)  # (N,)
    a_trad = K0 * np.power(A_o * f_o / C_o, sigma - 1.0) * S_o / sigma
    if is_agri:
        a_mech = K0 * np.power(A_o * f_o * xi / CBREVE_o, sigma - 1.0) * S_o / sigma
        cost_export = CBREVE_o
        prod_export = xi
    else:
        a_mech = None
        cost_export = C_o
        prod_export = 1.0
    # Export variable profit per unit of foreign demand shifter.
    a_export_unit = (
        K0 * np.power(A_o * f_o * prod_export / (tautilde_o * cost_export), sigma - 1.0) / sigma
    )
    # Delivered-price CES aggregate of export varieties per unit of Ztilde^(sigma-1).
    base_export_unit = (
        M_j
        * np.power((sigma / (sigma - 1.0)) * (1.0 - s_o) * tautilde_o, 1.0 - sigma)
        * np.power(1.0 / cost_export, sigma - 1.0)
    )

    def choices(D_x: float):
        a_x = a_export_unit * D_x
        if is_agri:
            slopes = np.stack([np.zeros(N), a_trad, a_mech, a_mech + a_x])
            costs = np.stack([np.zeros(N), F_o, F_o + Fbreve_o, F_o + Fbreve_o + Ftilde_o])
        else:
            slopes = np.stack([np.zeros(N), a_trad, a_trad + a_x])
            costs = np.stack([np.zeros(N), F_o, F_o + Ftilde_o])
        phis = nested_cutoffs(slopes, costs, sigma=sigma)
        phi_tilde_ = phis[-1]
        I_tilde_ = integral_phi_sigma_minus_1(phi_tilde_, kappa, sigma=sigma, theta=theta, kappa=kappa)
        Ztilde_ = A_o * f_o * prod_export * np.power(I_tilde_, 1.0 / (sigma - 1.0))
        base_export_ = base_export_unit * np.power(Ztilde_, sigma - 1.0)
        return phis, Ztilde_, base_export_

    # -------- Foreign demand for exports --------
    # Foreign buyers substitute among Korean export varieties at sigma (so markups are
    # unchanged) and between the Korean bundle and foreign goods at sigma_x, so the aggregate
    # export demand elasticity is sigma_x. The effective demand shifter is
    #     D_x = Dtilde * (P^X / ptilde)^(sigma - sigma_x),
    # with P^X the CES index of Korean delivered export prices. sigma_x = sigma (default)
    # gives D_x = Dtilde; otherwise D_x solves a scalar fixed point.
    sigma_x = params.sigma_x
    nontraded = exog.is_nontraded(j)
    if nontraded:
        # No foreign demand: the export option has the slope of the option below it and a
        # higher fixed cost, so no firm exports.
        D_x = 0.0
        phis, Ztilde, base_export = choices(D_x)
    elif sigma_x is None or sigma_x == sigma:
        D_x = Dtilde_j
        phis, Ztilde, base_export = choices(D_x)
    else:
        def gap(u: float) -> float:
            _, _, be = choices(float(np.exp(u)))
            log_PX = np.log(max(float(np.sum(be)), 1e-300)) / (1.0 - sigma)
            return u - np.log(Dtilde_j) - (sigma - sigma_x) * (log_PX - np.log(ptilde_j))

        # Bracket the root in u = log D_x, widening additively with a doubling step.
        u0 = float(np.log(Dtilde_j))
        step = 1.0
        lo, hi = u0 - step, u0 + step
        g_lo, g_hi = gap(lo), gap(hi)
        while g_lo * g_hi > 0.0:
            step *= 2.0
            if step > 512.0:
                raise RuntimeError(f"export-demand fixed point not bracketed (t={t}, j={j})")
            lo, hi = u0 - step, u0 + step
            g_lo, g_hi = gap(lo), gap(hi)
        D_x = float(np.exp(brentq(gap, lo, hi, xtol=1e-14, rtol=1e-14)))
        phis, Ztilde, base_export = choices(D_x)

    phi_bar = phis[1]
    if is_agri:
        phi_breve = phis[2]
        phi_tilde = phis[3]
        upper_trad = np.minimum(phi_breve, kappa)
    else:
        phi_breve = None
        phi_tilde = phis[2]
        upper_trad = kappa * np.ones(N, dtype=float)

    # -------- Productivity aggregates --------
    I_trad = integral_phi_sigma_minus_1(phi_bar, upper_trad, sigma=sigma, theta=theta, kappa=kappa)
    Zbar = A_o * f_o * np.power(I_trad, 1.0 / (sigma - 1.0))

    if is_agri:
        I_breve = integral_phi_sigma_minus_1(phi_breve, kappa, sigma=sigma, theta=theta, kappa=kappa)
        # Adopters produce with effective productivity xi*phi in ALL markets (this is the
        # premise of the adoption benefit term B). The xi factor must therefore appear in
        # the domestic mechanized aggregate exactly as it does in the export aggregate
        # Ztilde. (model_review.md 2.1; model.tex eq. Zbreve.)
        Zbreve = A_o * f_o * xi * np.power(I_breve, 1.0 / (sigma - 1.0))
    else:
        Zbreve = None

    # -------- Price index P implied --------
    common_pref = M_j * np.power((sigma / (sigma - 1.0)) * (1.0 - s_o), 1.0 - sigma)

    base_trad = common_pref * np.power(Zbar / C_o, sigma - 1.0)

    if is_agri:
        base_breve = common_pref * np.power(Zbreve / CBREVE_o, sigma - 1.0)
    else:
        base_breve = np.zeros(N, dtype=float)

    base_total = base_trad + base_breve

    domestic_integrals_d = base_total @ tau_pow  # (N,)
    if nontraded:
        import_term_d = np.zeros(N, dtype=float)
    else:
        import_term_d = np.power(exog.tautilde[t, j, :] * ptilde_j, 1.0 - sigma)
    # Floor: a non-traded sector with no active firms at the current iterate would have an
    # infinite price. A large finite price raises the demand shifter S, so firms enter at the
    # next iterate. The floor is far below any equilibrium value of the sum.
    P_implied = np.power(np.maximum(domestic_integrals_d + import_term_d, 1e-12), 1.0 / (1.0 - sigma))

    # -------- Revenues --------
    R_trad = base_trad * S_o
    R_breve = base_breve * S_o
    R_domestic_total = base_total * S_o
    R_tilde = base_export * D_x

    gross_output = R_domestic_total + R_tilde

    # -------- Counts (nested: exporters, adopters <= active firms) --------
    num_firms = M_j * pareto_survival(phi_bar, theta=theta, kappa=kappa)
    num_exporters = M_j * pareto_survival(phi_tilde, theta=theta, kappa=kappa)

    if is_agri:
        num_adopters = M_j * pareto_survival(phi_breve, theta=theta, kappa=kappa)
    else:
        num_adopters = np.zeros(N, dtype=float)

    return SectorState(
        j=j,
        C=C_o,
        CBREVE=CBREVE_o,
        phi_bar=phi_bar,
        phi_breve=phi_breve,
        phi_tilde=phi_tilde,
        Zbar=Zbar,
        Zbreve=Zbreve,
        Ztilde=Ztilde,
        P_implied=P_implied,
        R_trad=R_trad,
        R_breve=R_breve,
        R_tilde=R_tilde,
        R_domestic_total=R_domestic_total,
        gross_output=gross_output,
        num_firms=num_firms,
        num_exporters=num_exporters,
        num_adopters=num_adopters,
        S_o=S_o,
        B_domestic=base_total,
        D_export=float(D_x),
        F_cost=np.broadcast_to(F_o, (N,)).astype(float),
        Fbreve_cost=np.broadcast_to(Fbreve_o, (N,)).astype(float),
        Ftilde_cost=np.broadcast_to(Ftilde_o, (N,)).astype(float),
    )
