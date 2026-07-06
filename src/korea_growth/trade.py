"""Trade block: price indices, revenues, cutoffs.

This module provides a vectorized implementation of the expensive parts of the
prototype `baseline.py`:

- Entry/export/adoption cutoffs (phi-bar, phi-tilde, phi-breve)
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
        Factor prices (N,).
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

    F_o = exog.F[t, :, j]
    Fbreve_o = exog.Fbreve[t, :, j]
    Ftilde_o = exog.Ftilde[t, :, j]

    tautilde_o = exog.tautilde[t, j, :]
    Dtilde_j = float(exog.Dtilde[t, j])
    ptilde_j = float(exog.ptilde[t, j])

    # Agglomeration term f_{o,j} = L_{o,t-1}^{rho_j}
    f_o = agglomeration(L_prev, float(params.rho_j[j]))

    # Unit cost for domestic production
    C_o = unit_cost_bundle(r=r, w=w, P=P, beta=beta_o, gamma=gamma_o, gamma_io=gamma_io_o)

    # Unit cost and shares for new tech (only matters for agriculture)
    if is_agri:
        betabreve_o = exog.betabreve[t, :, j]
        gammabreve_o = exog.gammabreve[t, :, j]
        gammabreve_io_o = exog.gammabreve_io[t, :, j, :]
        CBREVE_o = unit_cost_bundle(r=r, w=w, P=P, beta=betabreve_o, gamma=gammabreve_o, gamma_io=gammabreve_io_o)
    else:
        betabreve_o = None
        gammabreve_o = None
        gammabreve_io_o = None
        CBREVE_o = None

    # Demand shifter S_o = sum_d tau_{o,d}^{1-sigma} * P_{d,j}^{sigma-1} * E_{d,j}
    demand_dest = np.power(P[:, j], sigma - 1.0) * E[:, j]  # (N,)
    S_o = tau_pow @ demand_dest
    S_o = np.maximum(S_o, eps)

    # -------- Entry cutoff phi_bar --------
    term_bar = (
        (sigma / (sigma - 1.0))
        * (1.0 - s_o)
        / (A_o * f_o)
        * np.power(sigma, 1.0 / (sigma - 1.0))
        * C_o
        * np.power(F_o / S_o, 1.0 / (sigma - 1.0))
    )
    phi_bar = np.maximum(1.0, term_bar)

    # -------- Adoption cutoff phi_breve (agriculture only) --------
    if is_agri:
        # benefit term = ((xi*C/CBREVE)^(sigma-1) - 1)^(1/(1-sigma))
        ratio = xi * C_o / CBREVE_o
        benefit = np.power(ratio, sigma - 1.0) - 1.0
        # If benefit<=0 adoption is never profitable; set benefit_term=+inf => phi_breve huge
        benefit_term = np.where(benefit > 0.0, np.power(benefit, 1.0 / (1.0 - sigma)), np.inf)

        term_breve = (
            (sigma / (sigma - 1.0))
            * (1.0 - s_o)
            / (A_o * f_o)
            * np.power(sigma, 1.0 / (sigma - 1.0))
            * C_o
            * benefit_term
            * np.power(Fbreve_o / S_o, 1.0 / (sigma - 1.0))
        )
        phi_breve = np.maximum(1.0, term_breve)

        upper_trad = np.minimum(phi_breve, kappa)
    else:
        phi_breve = None
        upper_trad = kappa * np.ones(N, dtype=float)

    # -------- Export cutoff phi_tilde --------
    if is_agri:
        # extra term for agriculture exporters: CBREVE/C/xi
        extra = (CBREVE_o / C_o) / xi
    else:
        extra = 1.0

    term_tilde = (
        (sigma / (sigma - 1.0))
        * (1.0 - s_o)
        / (A_o * f_o)
        * np.power(sigma, 1.0 / (sigma - 1.0))
        * C_o
        * np.power(Ftilde_o / (np.power(tautilde_o, 1.0 - sigma) * Dtilde_j), 1.0 / (sigma - 1.0))
        * extra
    )
    phi_tilde = np.maximum(1.0, term_tilde)

    # -------- Productivity aggregates --------
    I_trad = integral_phi_sigma_minus_1(phi_bar, upper_trad, sigma=sigma, theta=theta, kappa=kappa)
    Zbar = A_o * f_o * np.power(I_trad, 1.0 / (sigma - 1.0))

    if is_agri:
        I_breve = integral_phi_sigma_minus_1(phi_breve, kappa, sigma=sigma, theta=theta, kappa=kappa)
        # Adopters produce with effective productivity xi*phi in ALL markets (this is the
        # premise of the adoption benefit term B). The xi factor must therefore appear in
        # the domestic mechanized aggregate exactly as it does in the export aggregate
        # Ztilde below. (model_review.md 2.1; model.tex eq. Zbreve.)
        Zbreve = A_o * f_o * xi * np.power(I_breve, 1.0 / (sigma - 1.0))
    else:
        Zbreve = None

    I_tilde = integral_phi_sigma_minus_1(phi_tilde, kappa, sigma=sigma, theta=theta, kappa=kappa)
    xi_or_1 = xi if is_agri else 1.0
    Ztilde = A_o * f_o * xi_or_1 * np.power(I_tilde, 1.0 / (sigma - 1.0))

    # -------- Price index P implied --------
    common_pref = M_j * np.power((sigma / (sigma - 1.0)) * (1.0 - s_o), 1.0 - sigma)

    base_trad = common_pref * np.power(Zbar / C_o, sigma - 1.0)

    if is_agri:
        base_breve = common_pref * np.power(Zbreve / CBREVE_o, sigma - 1.0)
    else:
        base_breve = np.zeros(N, dtype=float)

    base_total = base_trad + base_breve

    domestic_integrals_d = base_total @ tau_pow  # (N,)
    import_term_d = np.power(exog.tautilde[t, j, :] * ptilde_j, 1.0 - sigma)
    P_implied = np.power(domestic_integrals_d + import_term_d, 1.0 / (1.0 - sigma))

    # -------- Revenues --------
    R_trad = base_trad * S_o
    R_breve = base_breve * S_o
    R_domestic_total = base_total * S_o

    # Export revenue
    if is_agri:
        cost_export = CBREVE_o
    else:
        cost_export = C_o

    base_export = (
        M_j
        * np.power((sigma / (sigma - 1.0)) * (1.0 - s_o) * tautilde_o, 1.0 - sigma)
        * np.power(Ztilde / cost_export, sigma - 1.0)
    )
    R_tilde = base_export * Dtilde_j

    gross_output = R_domestic_total + R_tilde

    # -------- Counts --------
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
    )
