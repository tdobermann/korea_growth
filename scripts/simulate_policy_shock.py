"""Simulate Korea's HCI-era industrial policy and plot mechanisms.

Calibrated to empirical results from "The Miracle on the Han" (2026 draft):
- SDID estimates of industrial park effects on manufacturing (Table 1)
- Market-access-driven agricultural machinery adoption (Table 2, beta=272)
- Agricultural productivity gains (+0.70 log pts) and labour intensity
  decline (-0.61 log pts) from market access (Table 4)
- Non-farm outmigration near IPs vs. retention in remote areas (Table 6)
- Service sector growth from market access (+8.8 establishments, Table 10)
- Heterogeneous effects by IP-distance decile (Figure 8)

Model structure:
  5 regions  : Seoul, Busan, Changwon, Daegu, Rural
  3 sectors  : Agri, HeavyMnf, Services
  6 periods  : t=1 (1965) .. t=6 (1985)

Policy channels (phased):
  1) Industrial parks in Changwon/Busan (HeavyMnf productivity + entry support)
  2) Corridor-focused road infrastructure build-out
  3) Agricultural modernisation spillover in middle/remote regions
  4) Rural service growth from local-demand expansion

Run:
    py -3 scripts/simulate_policy_shock.py
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from korea_growth.checks import validate_inputs
from korea_growth.solver import solve_dynamic_equilibrium
from korea_growth.trade import compute_sector_state
from korea_growth.types import (
    DynamicEquilibriumPath,
    ModelDimensions,
    ModelExogenousPaths,
    ModelInputs,
    ModelParameters,
    SolverOptions,
)

# ---------------------------------------------------------------------------
# Empirical constants from the paper
# ---------------------------------------------------------------------------
# Table 4, preferred spec (col 3): elasticity of ag value-added to log(MA)
BETA_AG_PRODUCTIVITY = 0.70
# Table 4, col 7: elasticity of labour intensity to log(MA)
BETA_LABOUR_INTENSITY = -0.61
# Table 2, preferred spec (col 4): HH tillers per unit delta-log(MA)
BETA_MACHINERY_ADOPTION = 272.0
# Table 6, preferred spec (col 2): non-farm pop elasticity to delta-log(MA)
BETA_NONFARM_POP = -6.991
# Table 10, preferred spec (col 2): service establishments per delta-log(MA)
BETA_SERVICES = 8.779
# Table 1: large early-HCI cohort production ATT (1972 cohort, MMS units)
EARLY_HCI_PRODUCTION_ATT = 355_929
# Table 1: peak production ATT (1973 cohort, MMS units)
PEAK_PRODUCTION_ATT = 399_398
# Road network: highway coverage roughly doubled 1970-1980 (Section 2.2)
TAU_DECLINE_FACTOR = 0.50  # trade costs fall by ~50% over the HCI period

ROAD_PHASE = {1: 0.0, 2: 0.10, 3: 0.25, 4: 0.40, 5: 0.50, 6: 0.50}

# Pairwise road improvements were strongest on the Seoul-Busan-Changwon corridor.
ROAD_NETWORK_WEIGHT = np.array(
    [
        [0.0, 1.0, 0.9, 0.8, 0.5],
        [1.0, 0.0, 1.0, 0.85, 0.55],
        [0.9, 1.0, 0.0, 0.8, 0.5],
        [0.8, 0.85, 0.8, 0.0, 0.7],
        [0.5, 0.55, 0.5, 0.7, 0.0],
    ],
    dtype=float,
)

# Rural spillovers peak away from the IP hosts, consistent with Figure 8.
AG_MODERNIZATION_EXPOSURE = np.array([0.0, 0.10, 0.05, 0.55, 0.80], dtype=float)
SERVICE_DEMAND_EXPOSURE = np.array([0.05, 0.15, 0.10, 0.80, 0.95], dtype=float)
IMPORT_ACCESS_EXPOSURE = np.array([0.25, 0.50, 0.45, 0.30, 0.10], dtype=float)

BASELINE_HEAVY_MNF_FIRM_MASS = np.array([2.0, 2.1, 2.2, 2.3, 2.4, 2.5], dtype=float)
BASELINE_HEAVY_MNF_EXPORT_DEMAND = np.array([0.48, 0.58, 0.72, 0.88, 1.00, 1.10], dtype=float)

AG_PRODUCTIVITY_TARGET_SHARE = 0.30
AG_LABOUR_INTENSITY_TARGET_SHARE = 0.035
AG_ADOPTION_COST_DECLINE = 0.14
SERVICE_FIXED_COST_DECLINE = 0.32
SERVICE_PRODUCTIVITY_BOOST = 0.24
SERVICE_AMENITY_BOOST = 0.04
EXPORT_DEMAND_BOOST = 0.02
HEAVY_MNF_FIRM_MASS_BOOST = 0.04


def build_baseline_inputs() -> ModelInputs:
    """Construct a 5-region, 3-sector, 6-period baseline economy.

    Regions are ordered by proximity to industrial parks:
      Seoul (capital), Busan (port city), Changwon (IP host),
      Daegu (intermediate), Rural (remote agricultural)

    Sectors: Agri (j=0), HeavyMnf (j=1), Services (j=2)
    Periods: t=1..6 mapping to ~1965, 1968, 1973, 1975, 1980, 1985
    """
    times = [1, 2, 3, 4, 5, 6]
    regions = ["Seoul", "Busan", "Changwon", "Daegu", "Rural"]
    sectors = ["Agri", "HeavyMnf", "Services"]

    dims = ModelDimensions(times=times, regions=regions, sectors=sectors)

    # --- Parameters ---
    # sigma=4: CES elasticity (standard in Melitz-type models)
    # theta=5: Pareto shape (governs firm heterogeneity)
    # kappa=8: Pareto upper bound
    # xi=1.5: cost advantage of mechanised agriculture
    # rho_j: agglomeration elasticity by sector
    #   - Agri: 0.03 (low agglomeration, paper shows rural dispersion)
    #   - HeavyMnf: 0.12 (strong agglomeration, paper Fig 3 shows concentration)
    #   - Services: 0.06 (moderate, paper Table 10 shows local demand driven)
    # iota=-0.02: mild congestion
    # eta=0.2: non-homothetic expenditure parameter
    # nu=5.0: migration choice heterogeneity
    # alpha_j: base expenditure shares
    #   - Agri: 0.35 (1965 agriculture ~35% of GDP, Fig 1)
    #   - HeavyMnf: 0.25 (manufacturing ~15% in 1965, rising)
    #   - Services: 0.40 (services ~45% in 1965)
    # v_j: non-homothetic shifts (richer -> less ag, more services)
    params = ModelParameters(
        sigma=4.0,
        theta=5.0,
        kappa=8.0,
        xi=1.5,
        rho_j=np.array([0.03, 0.12, 0.06]),
        iota=-0.02,
        eta=0.2,
        nu=5.0,
        alpha_j=np.array([0.35, 0.25, 0.40]),
        v_j=np.array([0.03, -0.01, -0.02]),
    )

    T, N, J = dims.T, dims.N, dims.J

    # --- Initial population shares ---
    # 1965: urbanisation ~28%, Seoul dominant, Rural largest
    # Paper Fig 2: urban pop share 28% in 1960
    L0 = np.array([0.20, 0.12, 0.03, 0.10, 0.55])

    # --- Firm mass ---
    M = np.full((T, J), 1.0)
    # Heavy manufacturing has a meaningful pre-HCI base and grows with export demand.
    M[:, 1] = BASELINE_HEAVY_MNF_FIRM_MASS

    # --- Productivity shifter A ---
    A = np.ones((T, N, J))
    # The urban corridor is already Korea's manufacturing core before 1973.
    A[:, 0, 1] = 1.25
    A[:, 1, 1] = 1.45
    A[:, 2, 1] = 1.55
    A[:, 3, 1] = 1.15
    # Seoul remains productive in services, but not enough to swamp manufacturing.
    A[:, 0, 2] = 0.98
    # Rural has higher ag productivity (fertile land)
    A[:, 4, 0] = 1.1

    # --- Production shares ---
    # beta: land share in value added
    #   Agri: 0.40 (land-intensive)
    #   HeavyMnf: 0.15 (capital equipment but modelled via land/structures)
    #   Services: 0.25 (commercial real estate)
    beta = np.zeros((T, N, J))
    beta[..., 0] = 0.40  # Agri
    beta[..., 1] = 0.15  # HeavyMnf
    beta[..., 2] = 0.25  # Services

    # gamma: value-added share in gross output
    #   Agri: 0.55 (moderate IO linkages)
    #   HeavyMnf: 0.40 (heavy IO usage — steel, chemicals, etc.)
    #   Services: 0.70 (mostly value-added, few material inputs)
    gamma = np.zeros((T, N, J))
    gamma[..., 0] = 0.55
    gamma[..., 1] = 0.40
    gamma[..., 2] = 0.70

    # gamma_io: intermediate input shares (output sector j, input sector k)
    # Must satisfy: gamma[j] + sum_k gamma_io[j,k] = 1
    gamma_io = np.zeros((T, N, J, J))
    # Agri uses: own inputs 0.10, HeavyMnf inputs 0.20 (machinery/fertiliser),
    #            Services 0.15 (transport/marketing)
    gamma_io[..., 0, 0] = 0.10  # Agri->Agri
    gamma_io[..., 0, 1] = 0.20  # HeavyMnf->Agri
    gamma_io[..., 0, 2] = 0.15  # Services->Agri
    # HeavyMnf uses: Agri 0.05, own 0.35, Services 0.20
    gamma_io[..., 1, 0] = 0.05  # Agri->HeavyMnf
    gamma_io[..., 1, 1] = 0.35  # HeavyMnf->HeavyMnf
    gamma_io[..., 1, 2] = 0.20  # Services->HeavyMnf
    # Services uses: Agri 0.05, HeavyMnf 0.10, own 0.15
    gamma_io[..., 2, 0] = 0.05  # Agri->Services
    gamma_io[..., 2, 1] = 0.10  # HeavyMnf->Services
    gamma_io[..., 2, 2] = 0.15  # Services->Services

    # --- New technology (adoption) for agriculture ---
    # Mechanisation: higher HeavyMnf input share (tractors/tillers)
    # Paper Table 2: market access drives machinery adoption
    gammabreve_io = gamma_io.copy()
    # Adoption shifts HeavyMnf input share up (from 0.20 to 0.35)
    # reflecting tiller/machinery adoption from paper (272 HH tillers per
    # unit delta-logMA). Non-HeavyMnf shares stay the same per model constraint.
    gammabreve_io[..., 0, 1] = 0.35  # more machinery inputs

    gammabreve = gamma.copy()
    # Recompute VA share for agri to satisfy sum-to-one:
    # gammabreve[Agri] = 1 - sum_k gammabreve_io[Agri, k]
    gammabreve[..., 0] = (
        1.0 - gammabreve_io[..., 0, :].sum(axis=-1)
    )
    gammabreve[..., 0] = np.clip(gammabreve[..., 0], 1e-6, 0.999)

    betabreve = beta.copy()
    # Maintain gammabreve*betabreve = gamma*beta (land share consistency)
    safe_gammabreve = np.maximum(gammabreve[..., 0], 1e-10)
    betabreve[..., 0] = (gamma[..., 0] * beta[..., 0]) / safe_gammabreve

    # --- Fixed costs ---
    F = np.full((T, N, J), 0.20)
    F[:, :, 1] *= 0.52
    # Agriculture adoption cost: Fbreve
    Fbreve = np.zeros((T, N, J))
    Fbreve[..., 0] = 0.05
    # Export fixed cost
    Ftilde = np.full((T, N, J), 0.05)

    # --- Input-cost subsidies ---
    # Baseline: small agricultural subsidy only
    s = np.zeros((T, N, J))
    s[..., 0] = 0.05  # mild ag subsidy

    # --- Foreign demand and prices ---
    Dtilde = np.full((T, J), 0.50)
    # HeavyMnf has meaningful foreign demand before the HCI push.
    Dtilde[:, 1] = BASELINE_HEAVY_MNF_EXPORT_DEMAND
    ptilde = np.ones((T, J))

    # --- Amenities ---
    Vbar = np.ones((T, N))
    # Seoul has an amenity premium; Rural has lower baseline amenity.
    Vbar[:, 0] = 1.18
    Vbar[:, 4] = 0.85

    # --- Within-country trade costs tau ---
    # Pre-road baseline: high inter-regional costs, especially to/from Rural
    # Paper: Gyeongbu Expressway (Seoul-Busan) opened 1970, highway coverage
    # doubled by 1980.
    #
    # Distance matrix (iceberg cost):
    #          Seoul  Busan  Changwon  Daegu  Rural
    # Seoul      1.0   1.30    1.35    1.25    1.50
    # Busan     1.30    1.0    1.10    1.20    1.40
    # Changwon  1.35   1.10     1.0    1.15    1.35
    # Daegu     1.25   1.20    1.15     1.0    1.30
    # Rural     1.50   1.40    1.35    1.30     1.0
    base_tau_matrix = np.array([
        [1.00, 1.30, 1.35, 1.25, 1.50],
        [1.30, 1.00, 1.10, 1.20, 1.40],
        [1.35, 1.10, 1.00, 1.15, 1.35],
        [1.25, 1.20, 1.15, 1.00, 1.30],
        [1.50, 1.40, 1.35, 1.30, 1.00],
    ])
    tau = np.ones((T, J, N, N))
    for t in range(T):
        for j in range(J):
            tau[t, j, :, :] = base_tau_matrix

    # --- Import trade costs ---
    tautilde = np.full((T, J, N), 1.5)
    # Port cities have lower import costs
    tautilde[:, :, 1] = 1.3  # Busan (major port)
    tautilde[:, :, 2] = 1.35  # Changwon (near port)

    # --- Migration costs delta ---
    # Higher cost to move to/from Rural
    base_delta = np.array([
        [1.00, 1.08, 1.10, 1.08, 1.15],
        [1.08, 1.00, 1.05, 1.08, 1.12],
        [1.10, 1.05, 1.00, 1.06, 1.10],
        [1.08, 1.08, 1.06, 1.00, 1.10],
        [1.15, 1.12, 1.10, 1.10, 1.00],
    ])
    delta = np.ones((T, N, N))
    for t in range(T):
        delta[t, :, :] = base_delta

    # --- Land/structures ---
    # Rural has more land; Seoul constrained
    H = np.full((T, N), 1.0)
    H[:, 0] = 0.7   # Seoul (constrained)
    H[:, 4] = 2.0   # Rural (abundant land)

    # --- Government infrastructure spending ---
    # Increases during HCI period (road construction)
    tax_spending = np.array([0.005, 0.01, 0.02, 0.025, 0.02, 0.015])

    exog = ModelExogenousPaths(
        L0=L0,
        M=M,
        A=A,
        beta=beta,
        gamma=gamma,
        gamma_io=gamma_io,
        betabreve=betabreve,
        gammabreve=gammabreve,
        gammabreve_io=gammabreve_io,
        F=F,
        Fbreve=Fbreve,
        Ftilde=Ftilde,
        s=s,
        Dtilde=Dtilde,
        ptilde=ptilde,
        Vbar=Vbar,
        tau=tau,
        tautilde=tautilde,
        delta=delta,
        H=H,
        tax_spending_on_building_H_and_roads=tax_spending,
    )

    inputs = ModelInputs(dims=dims, params=params, exog=exog)
    validate_inputs(inputs)
    return inputs


def with_hci_policy(inputs: ModelInputs) -> ModelInputs:
    """Apply the full HCI policy package, phased over time.

    The policy is intentionally distance-sensitive:

    1) Industrial parks primarily boost heavy manufacturing in Changwon and Busan.
    2) Roads most strongly compress corridor trade costs.
    3) Agricultural modernisation is strongest in middle-to-remote regions.
    4) Rural service growth is modelled through lower service entry costs plus
       modest service productivity and amenity gains outside the IP core.
    """
    dims = inputs.dims
    exog = inputs.exog
    times = np.asarray(dims.times)

    s = exog.s.copy()
    A = exog.A.copy()
    F = exog.F.copy()
    Fbreve = exog.Fbreve.copy()
    tau = exog.tau.copy()
    delta = exog.delta.copy()
    beta = exog.beta.copy()
    Dtilde = exog.Dtilde.copy()
    M = exog.M.copy()
    Vbar = exog.Vbar.copy()
    tautilde = exog.tautilde.copy()
    tax_spending = exog.tax_spending_on_building_H_and_roads.copy()

    changwon_idx = dims.regions.index("Changwon")
    busan_idx = dims.regions.index("Busan")
    heavy_idx = dims.sectors.index("HeavyMnf")
    agri_idx = dims.sectors.index("Agri")
    services_idx = dims.sectors.index("Services")

    active_phase_total = sum(ROAD_PHASE[int(t)] for t in times if int(t) >= 3)
    machinery_scale = BETA_MACHINERY_ADOPTION / 272.0
    migration_pull_scale = abs(BETA_NONFARM_POP) / 6.991
    service_scale = BETA_SERVICES / 8.779
    changwon_park_scale = PEAK_PRODUCTION_ATT / 399_398.0
    busan_park_scale = EARLY_HCI_PRODUCTION_ATT / PEAK_PRODUCTION_ATT

    for t_idx, t_label in enumerate(times):
        phase = ROAD_PHASE.get(int(t_label), 0.0)

        if phase > 0:
            for j in range(dims.J):
                for o in range(dims.N):
                    for d in range(dims.N):
                        if o == d:
                            continue
                        gap = exog.tau[t_idx, j, o, d] - 1.0
                        close = phase * ROAD_NETWORK_WEIGHT[o, d]
                        tau[t_idx, j, o, d] = 1.0 + gap * (1.0 - close)

            for o in range(dims.N):
                for d in range(dims.N):
                    if o == d:
                        continue
                    gap = exog.delta[t_idx, o, d] - 1.0
                    pull = (0.55 if d == changwon_idx else 0.35) * migration_pull_scale
                    close = phase * ROAD_NETWORK_WEIGHT[o, d] * pull
                    delta[t_idx, o, d] = 1.0 + gap * (1.0 - close)

            for n in range(dims.N):
                import_gap = exog.tautilde[t_idx, heavy_idx, n] - 1.0
                tautilde[t_idx, heavy_idx, n] = 1.0 + import_gap * (
                    1.0 - phase * IMPORT_ACCESS_EXPOSURE[n]
                )

        if t_label >= 3:
            A[t_idx, changwon_idx, heavy_idx] *= 1.0 + 0.14 * changwon_park_scale
            F[t_idx, changwon_idx, heavy_idx] *= 1.0 - 0.18 * changwon_park_scale
            s[t_idx, changwon_idx, heavy_idx] = 0.04 * changwon_park_scale

            A[t_idx, busan_idx, heavy_idx] *= 1.0 + 0.04 * busan_park_scale
            F[t_idx, busan_idx, heavy_idx] *= 1.0 - 0.07 * busan_park_scale
            s[t_idx, busan_idx, heavy_idx] = 0.015 * busan_park_scale

            Dtilde[t_idx, heavy_idx] *= 1.0 + EXPORT_DEMAND_BOOST * phase / TAU_DECLINE_FACTOR
            M[t_idx, heavy_idx] *= 1.0 + HEAVY_MNF_FIRM_MASS_BOOST * phase / TAU_DECLINE_FACTOR

            for n in range(dims.N):
                ag_exposure = AG_MODERNIZATION_EXPOSURE[n]
                if ag_exposure > 0.0:
                    Fbreve[t_idx, n, agri_idx] *= 1.0 - (
                        AG_ADOPTION_COST_DECLINE
                        * machinery_scale
                        * phase
                        * ag_exposure
                        / TAU_DECLINE_FACTOR
                    )
                    A[t_idx, n, agri_idx] *= np.exp(
                        BETA_AG_PRODUCTIVITY
                        * AG_PRODUCTIVITY_TARGET_SHARE
                        * phase
                        * ag_exposure
                        / active_phase_total
                    )
                    beta[t_idx, n, agri_idx] = min(
                        beta[t_idx, n, agri_idx]
                        + (
                            AG_LABOUR_INTENSITY_TARGET_SHARE
                            * abs(BETA_LABOUR_INTENSITY)
                            * phase
                            * ag_exposure
                            / (active_phase_total * 0.61)
                        ),
                        0.455,
                    )

                service_exposure = SERVICE_DEMAND_EXPOSURE[n]
                F[t_idx, n, services_idx] *= 1.0 - (
                    SERVICE_FIXED_COST_DECLINE
                    * service_scale
                    * phase
                    * service_exposure
                    / TAU_DECLINE_FACTOR
                )
                A[t_idx, n, services_idx] *= 1.0 + (
                    SERVICE_PRODUCTIVITY_BOOST
                    * service_scale
                    * phase
                    * service_exposure
                    / TAU_DECLINE_FACTOR
                )
                Vbar[t_idx, n] *= 1.0 + (
                    SERVICE_AMENITY_BOOST
                    * service_scale
                    * phase
                    * service_exposure
                    / TAU_DECLINE_FACTOR
                )

            tax_spending[t_idx] *= 1.15

    gammabreve = exog.gammabreve.copy()
    gammabreve_io = exog.gammabreve_io.copy()
    betabreve = exog.betabreve.copy()

    gammabreve[..., agri_idx] = 1.0 - gammabreve_io[..., agri_idx, :].sum(axis=-1)
    gammabreve[..., agri_idx] = np.clip(gammabreve[..., agri_idx], 1e-6, 0.999)
    safe_gb = np.maximum(gammabreve[..., agri_idx], 1e-10)
    gamma = exog.gamma.copy()
    betabreve[..., agri_idx] = (gamma[..., agri_idx] * beta[..., agri_idx]) / safe_gb

    exog_policy = replace(
        exog,
        s=s,
        A=A,
        F=F,
        Fbreve=Fbreve,
        tau=tau,
        delta=delta,
        beta=beta,
        M=M,
        betabreve=betabreve,
        gammabreve=gammabreve,
        gammabreve_io=gammabreve_io,
        gamma=gamma,
        Vbar=Vbar,
        tautilde=tautilde,
        Dtilde=Dtilde,
        tax_spending_on_building_H_and_roads=tax_spending,
    )
    shocked = replace(inputs, exog=exog_policy)
    validate_inputs(shocked)
    return shocked


def collect_region_metrics(
    *,
    inputs: ModelInputs,
    path: DynamicEquilibriumPath,
    target_sector_idx: int,
) -> dict[str, np.ndarray]:
    T, N, J = inputs.dims.T, inputs.dims.N, inputs.dims.J
    eps = 1e-12

    exports_by_sector = np.zeros((T, N, J), dtype=float)
    output_by_sector = np.zeros((T, N, J), dtype=float)

    for t_idx in range(T):
        L_prev = inputs.exog.L0 if t_idx == 0 else path.L[t_idx - 1, :]
        for j_idx in range(J):
            st = compute_sector_state(
                t=t_idx,
                j=j_idx,
                dims=inputs.dims,
                params=inputs.params,
                exog=inputs.exog,
                L_prev=L_prev,
                w=path.w[t_idx, :],
                r=path.r[t_idx, :],
                P=path.P[t_idx, :, :],
                E=path.E[t_idx, :, :],
            )
            exports_by_sector[t_idx, :, j_idx] = st.R_tilde
            output_by_sector[t_idx, :, j_idx] = st.gross_output

    total_exports = exports_by_sector.sum(axis=2)
    target_sector_exports = exports_by_sector[:, :, target_sector_idx]
    total_output = output_by_sector.sum(axis=2)

    target_exp_share = path.E[:, :, target_sector_idx] / np.maximum(
        path.E.sum(axis=2), eps
    )
    target_export_share = target_sector_exports / np.maximum(total_exports, eps)
    target_output_share = output_by_sector[:, :, target_sector_idx] / np.maximum(
        total_output, eps
    )
    mnf_output_share = output_by_sector[:, :, 1] / np.maximum(total_output, eps)
    services_output_share = output_by_sector[:, :, 2] / np.maximum(total_output, eps)

    return {
        "wage": path.w,
        "pop_share": path.L,
        "income_pc": path.y_pc,
        "exports_total": total_exports,
        "exports_target_sector": target_sector_exports,
        "target_exp_share": target_exp_share,
        "target_export_share": target_export_share,
        "target_output_share": target_output_share,
        "mnf_output_share": mnf_output_share,
        "services_output_share": services_output_share,
        "output_by_sector": output_by_sector,
        "taubar": path.taubar,
        "pibar": path.pibar,
    }


def aggregate_output_shares(metrics: dict[str, np.ndarray]) -> np.ndarray:
    """Aggregate sectoral output shares using economy-wide output weights."""
    output = metrics["output_by_sector"]
    economy_total = output.sum(axis=(1, 2))
    return output.sum(axis=1) / np.maximum(economy_total[:, None], 1e-12)


def calibration_moments(
    *,
    base: dict[str, np.ndarray],
    policy: dict[str, np.ndarray],
) -> dict[str, float]:
    """Directional moments used to compare the simulation to the paper."""
    base_agg = aggregate_output_shares(base)
    policy_agg = aggregate_output_shares(policy)

    return {
        "agg_agri_share_change": float(policy_agg[-1, 0] - base_agg[-1, 0]),
        "agg_mnf_share_change": float(policy_agg[-1, 1] - base_agg[-1, 1]),
        "agg_services_share_change": float(policy_agg[-1, 2] - base_agg[-1, 2]),
        "changwon_wage_change": float(policy["wage"][-1, 2] - base["wage"][-1, 2]),
        "changwon_mnf_share_change": float(
            policy["mnf_output_share"][-1, 2] - base["mnf_output_share"][-1, 2]
        ),
        "seoul_pop_change": float(policy["pop_share"][-1, 0] - base["pop_share"][-1, 0]),
        "rural_pop_change": float(policy["pop_share"][-1, 4] - base["pop_share"][-1, 4]),
        "rural_income_change": float(policy["income_pc"][-1, 4] - base["income_pc"][-1, 4]),
        "rural_services_change": float(
            policy["services_output_share"][-1, 4] - base["services_output_share"][-1, 4]
        ),
        "daegu_services_change": float(
            policy["services_output_share"][-1, 3] - base["services_output_share"][-1, 3]
        ),
    }


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

YEAR_LABELS = {1: "1965", 2: "1968", 3: "1973", 4: "1975", 5: "1980", 6: "1985"}


def _time_labels(times: np.ndarray) -> list[str]:
    return [YEAR_LABELS.get(int(t), str(t)) for t in times]


def plot_structural_transformation(
    *,
    times: np.ndarray,
    base: dict[str, np.ndarray],
    policy: dict[str, np.ndarray],
    outpath: Path,
) -> None:
    """Plot economy-wide structural change: sectoral output shares over time.

    Mirrors Figure 1 of the paper (agriculture declining, manufacturing rising).
    """
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), constrained_layout=True)
    xlabels = _time_labels(times)
    base_agg = aggregate_output_shares(base)
    pol_agg = aggregate_output_shares(policy)

    for ax, (s_name, key) in zip(
        axes,
        [
            ("Agriculture", 0),
            ("Heavy Manufacturing", 1),
            ("Services", 2),
        ],
    ):
        ax.plot(times, base_agg[:, key], marker="o", label="No HCI")
        ax.plot(times, pol_agg[:, key], marker="s", label="HCI Policy")
        ax.axvline(3, color="grey", linestyle="--", linewidth=0.8, alpha=0.7,
                   label="HCI declaration (1973)")
        ax.set_title(f"{s_name} output share")
        ax.set_xticks(times)
        ax.set_xticklabels(xlabels, rotation=45, fontsize=8)
        ax.grid(alpha=0.2)

    axes[0].legend(loc="best", fontsize=8)
    fig.suptitle("Structural Transformation: Baseline vs HCI Policy (cf. Paper Fig 1)")
    fig.savefig(outpath, dpi=160)
    plt.close(fig)


def plot_target_mechanisms(
    *,
    times: np.ndarray,
    base: dict[str, np.ndarray],
    policy: dict[str, np.ndarray],
    target_region_idx: int,
    target_region: str,
    outpath: Path,
) -> None:
    """Plot mechanisms for the IP-hosting region (Changwon)."""
    fig, axes = plt.subplots(2, 3, figsize=(15, 8), constrained_layout=True)
    axes = axes.ravel()
    xlabels = _time_labels(times)

    panels = [
        (f"{target_region} wage", "wage"),
        (f"{target_region} population share", "pop_share"),
        (f"{target_region} per-capita income", "income_pc"),
        (f"{target_region} total exports", "exports_total"),
        (f"{target_region} HeavyMnf output share", "mnf_output_share"),
        (f"{target_region} Services output share", "services_output_share"),
    ]

    for ax, (title, key) in zip(axes, panels):
        ax.plot(times, base[key][:, target_region_idx], marker="o", label="No HCI")
        ax.plot(times, policy[key][:, target_region_idx], marker="s", label="HCI Policy")
        ax.axvline(3, color="grey", linestyle="--", linewidth=0.8, alpha=0.7)
        ax.set_title(title)
        ax.set_xticks(times)
        ax.set_xticklabels(xlabels, rotation=45, fontsize=8)
        ax.grid(alpha=0.2)

    axes[0].legend(loc="best", fontsize=8)
    fig.suptitle(f"{target_region} (IP Host): Baseline vs HCI Policy")
    fig.savefig(outpath, dpi=160)
    plt.close(fig)


def plot_regional_effects(
    *,
    times: np.ndarray,
    regions: list[str],
    base: dict[str, np.ndarray],
    policy: dict[str, np.ndarray],
    outpath: Path,
) -> None:
    """Plot policy effect (policy - baseline) across all regions."""
    fig, axes = plt.subplots(2, 3, figsize=(16, 9), constrained_layout=True)
    axes = axes.ravel()
    xlabels = _time_labels(times)

    panels = [
        ("Wage effect", "wage"),
        ("Population-share effect", "pop_share"),
        ("Income-per-capita effect", "income_pc"),
        ("HeavyMnf output-share effect", "mnf_output_share"),
        ("Agri output-share effect", "target_output_share"),
        ("Services output-share effect", "services_output_share"),
    ]

    for ax, (title, key) in zip(axes, panels):
        for r_idx, region in enumerate(regions):
            diff = policy[key][:, r_idx] - base[key][:, r_idx]
            ax.plot(times, diff, marker="o", label=region)
        ax.axhline(0.0, color="black", linewidth=0.8, alpha=0.7)
        ax.axvline(3, color="grey", linestyle="--", linewidth=0.8, alpha=0.7)
        ax.set_title(title)
        ax.set_xticks(times)
        ax.set_xticklabels(xlabels, rotation=45, fontsize=8)
        ax.grid(alpha=0.2)

    axes[0].legend(loc="best", fontsize=7)
    fig.suptitle(
        "Regional Effects: HCI Policy - Baseline\n"
        "(cf. Paper Tables 1, 4, 6, 10 and Figure 8)"
    )
    fig.savefig(outpath, dpi=160)
    plt.close(fig)


def plot_rural_spillovers(
    *,
    times: np.ndarray,
    base: dict[str, np.ndarray],
    policy: dict[str, np.ndarray],
    regions: list[str],
    outpath: Path,
) -> None:
    """Plot rural spillover channels: ag productivity, migration, services.

    Directly motivated by the paper's empirical findings:
    - Table 4: agricultural productivity and labour intensity
    - Table 6: population migration by IP distance
    - Table 10: service sector growth
    """
    rural_idx = regions.index("Rural")
    daegu_idx = regions.index("Daegu")

    fig, axes = plt.subplots(2, 2, figsize=(12, 9), constrained_layout=True)
    xlabels = _time_labels(times)

    # Panel 1: Rural ag output share (proxy for ag productivity)
    ax = axes[0, 0]
    ax.plot(times, base["target_output_share"][:, rural_idx],
            marker="o", label="No HCI")
    ax.plot(times, policy["target_output_share"][:, rural_idx],
            marker="s", label="HCI Policy")
    ax.set_title(f"Rural: Agri output share\n(cf. Table 4: ag productivity +0.70 log pts)")
    ax.set_xticks(times)
    ax.set_xticklabels(xlabels, rotation=45, fontsize=8)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.2)

    # Panel 2: Population share changes (near IP vs remote)
    ax = axes[0, 1]
    for r_idx, region in enumerate(regions):
        diff = policy["pop_share"][:, r_idx] - base["pop_share"][:, r_idx]
        ax.plot(times, diff, marker="o", label=region)
    ax.axhline(0, color="black", linewidth=0.8, alpha=0.5)
    ax.axvline(3, color="grey", linestyle="--", linewidth=0.8, alpha=0.7)
    ax.set_title("Population share effect by region\n(cf. Table 6, Figure 7)")
    ax.set_xticks(times)
    ax.set_xticklabels(xlabels, rotation=45, fontsize=8)
    ax.legend(fontsize=7)
    ax.grid(alpha=0.2)

    # Panel 3: Services output share (Rural vs Daegu)
    ax = axes[1, 0]
    for r_idx, label in [(rural_idx, "Rural"), (daegu_idx, "Daegu")]:
        base_val = base["services_output_share"][:, r_idx]
        pol_val = policy["services_output_share"][:, r_idx]
        ax.plot(times, pol_val - base_val, marker="o", label=f"{label} (policy effect)")
    ax.axhline(0, color="black", linewidth=0.8, alpha=0.5)
    ax.set_title("Services output share effect\n(cf. Table 10: +8.8 firms per delta-logMA)")
    ax.set_xticks(times)
    ax.set_xticklabels(xlabels, rotation=45, fontsize=8)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.2)

    # Panel 4: Per-capita income convergence
    ax = axes[1, 1]
    for r_idx, region in enumerate(regions):
        base_val = base["income_pc"][:, r_idx]
        pol_val = policy["income_pc"][:, r_idx]
        ax.plot(times, pol_val - base_val, marker="o", label=region)
    ax.axhline(0, color="black", linewidth=0.8, alpha=0.5)
    ax.axvline(3, color="grey", linestyle="--", linewidth=0.8, alpha=0.7)
    ax.set_title("Per-capita income effect by region")
    ax.set_xticks(times)
    ax.set_xticklabels(xlabels, rotation=45, fontsize=8)
    ax.legend(fontsize=7)
    ax.grid(alpha=0.2)

    fig.suptitle("Rural Spillover Channels (calibrated to paper estimates)")
    fig.savefig(outpath, dpi=160)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def print_policy_description() -> None:
    print("=" * 70)
    print("HCI INDUSTRIAL POLICY SIMULATION")
    print("Calibrated to 'The Miracle on the Han' empirical estimates")
    print("=" * 70)
    print()
    print("Policy channels:")
    print("  1) Industrial parks in Changwon & Busan (t>=3, ~1973)")
    print("     - HeavyMnf productivity and entry improve most in Changwon")
    print("     - Busan receives a smaller corridor/port manufacturing boost")
    print("     Calibration: Table 1 SDID ATTs (1972-73 cohorts)")
    print()
    print("  2) Road infrastructure build-out (t>=2, phased)")
    print("     - tau declines most on the Seoul-Busan-Changwon corridor")
    print("     - Migration costs delta fall more for moves into the IP core")
    print("     Calibration: Section 2.2, Figures 4-5")
    print()
    print("  3) Agricultural modernisation spillover (t>=3)")
    print("     - Fbreve falls mostly in Daegu/Rural as road access improves")
    print("     - Ag productivity and labour-saving shifts scale with exposure")
    print("     Calibration: Table 2 (beta=272), Table 4 (+0.70, -0.61)")
    print()
    print("  4) Rural service growth (t>=3)")
    print("     - Lower service entry costs and modest service productivity gains")
    print("     Calibration: Table 10 (+8.8 establishments)")
    print()
    print(f"Empirical targets:")
    print(f"  Ag productivity elasticity to MA:  {BETA_AG_PRODUCTIVITY:+.2f} log pts")
    print(f"  Labour intensity elasticity to MA: {BETA_LABOUR_INTENSITY:+.2f} log pts")
    print(f"  Machinery adoption (HH tillers):   {BETA_MACHINERY_ADOPTION:.0f} per unit")
    print(f"  Non-farm population elasticity:    {BETA_NONFARM_POP:+.3f}")
    print(f"  Service establishments per MA:     {BETA_SERVICES:+.3f}")
    print(f"  Peak production ATT (1973):        {PEAK_PRODUCTION_ATT:,} MMS units")
    print()


def print_calibration_summary(
    *,
    base: dict[str, np.ndarray],
    policy: dict[str, np.ndarray],
) -> None:
    moments = calibration_moments(base=base, policy=policy)
    print("=== Directional calibration check (1985 policy - baseline) ===")
    print(f"  Aggregate agriculture share: {moments['agg_agri_share_change']:+.4f}")
    print(f"  Aggregate manufacturing share: {moments['agg_mnf_share_change']:+.4f}")
    print(f"  Aggregate services share: {moments['agg_services_share_change']:+.4f}")
    print(f"  Changwon wage: {moments['changwon_wage_change']:+.4f}")
    print(f"  Changwon manufacturing share: {moments['changwon_mnf_share_change']:+.4f}")
    print(f"  Seoul population share: {moments['seoul_pop_change']:+.4f}")
    print(f"  Rural population share: {moments['rural_pop_change']:+.4f}")
    print(f"  Rural income per capita: {moments['rural_income_change']:+.4f}")
    print(f"  Rural services share: {moments['rural_services_change']:+.4f}")
    print(f"  Daegu services share: {moments['daegu_services_change']:+.4f}")
    print()


def print_summary(
    *,
    times: np.ndarray,
    regions: list[str],
    base: dict[str, np.ndarray],
    policy: dict[str, np.ndarray],
) -> None:
    t_last_idx = len(times) - 1
    t_label = YEAR_LABELS.get(int(times[t_last_idx]), str(times[t_last_idx]))

    print(f"=== End-of-horizon effects at t={times[t_last_idx]} ({t_label}) ===")
    print(f"{'Region':<12} {'Wage':>8} {'Pop share':>10} {'Income pc':>10} "
          f"{'Exports':>9} {'Mnf share':>10} {'Svc share':>10}")
    print("-" * 72)

    for r_idx, region in enumerate(regions):
        dw = policy["wage"][t_last_idx, r_idx] - base["wage"][t_last_idx, r_idx]
        dp = policy["pop_share"][t_last_idx, r_idx] - base["pop_share"][t_last_idx, r_idx]
        dy = policy["income_pc"][t_last_idx, r_idx] - base["income_pc"][t_last_idx, r_idx]
        de = policy["exports_total"][t_last_idx, r_idx] - base["exports_total"][t_last_idx, r_idx]
        dm = policy["mnf_output_share"][t_last_idx, r_idx] - base["mnf_output_share"][t_last_idx, r_idx]
        ds = policy["services_output_share"][t_last_idx, r_idx] - base["services_output_share"][t_last_idx, r_idx]
        print(f"{region:<12} {dw:+8.4f} {dp:+10.4f} {dy:+10.4f} "
              f"{de:+9.4f} {dm:+10.4f} {ds:+10.4f}")

    print()
    te_b = base["exports_total"][t_last_idx, :].sum()
    te_p = policy["exports_total"][t_last_idx, :].sum()
    print(f"Aggregate exports: {te_p - te_b:+.4f}")
    print(f"Tax rate (taubar): {policy['taubar'][t_last_idx] - base['taubar'][t_last_idx]:+.4f}")
    print(f"Profit share (pibar): {policy['pibar'][t_last_idx] - base['pibar'][t_last_idx]:+.4f}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    outdir = Path("outputs")
    outdir.mkdir(exist_ok=True)

    print("Building baseline economy (5 regions, 3 sectors, 6 periods)...")
    baseline_inputs = build_baseline_inputs()

    print("Applying HCI policy package...")
    policy_inputs = with_hci_policy(baseline_inputs)

    options = SolverOptions(max_iter=3000, tol=1e-8, damping=0.25, verbose=False)

    print("Solving baseline equilibrium...")
    baseline_path = solve_dynamic_equilibrium(inputs=baseline_inputs, options=options)

    print("Solving policy equilibrium...")
    policy_path = solve_dynamic_equilibrium(inputs=policy_inputs, options=options)

    dims = baseline_inputs.dims
    times = np.asarray(dims.times)
    regions = list(dims.regions)
    agri_idx = dims.sectors.index("Agri")

    base_metrics = collect_region_metrics(
        inputs=baseline_inputs, path=baseline_path, target_sector_idx=agri_idx
    )
    policy_metrics = collect_region_metrics(
        inputs=policy_inputs, path=policy_path, target_sector_idx=agri_idx
    )

    # --- Generate plots ---
    structural_plot = outdir / "structural_transformation.png"
    target_plot = outdir / "changwon_ip_mechanisms.png"
    regional_plot = outdir / "regional_policy_effects.png"
    rural_plot = outdir / "rural_spillovers.png"

    changwon_idx = regions.index("Changwon")

    plot_structural_transformation(
        times=times,
        base=base_metrics,
        policy=policy_metrics,
        outpath=structural_plot,
    )
    plot_target_mechanisms(
        times=times,
        base=base_metrics,
        policy=policy_metrics,
        target_region_idx=changwon_idx,
        target_region="Changwon",
        outpath=target_plot,
    )
    plot_regional_effects(
        times=times,
        regions=regions,
        base=base_metrics,
        policy=policy_metrics,
        outpath=regional_plot,
    )
    plot_rural_spillovers(
        times=times,
        base=base_metrics,
        policy=policy_metrics,
        regions=regions,
        outpath=rural_plot,
    )

    # --- Print results ---
    print()
    print_policy_description()
    print("=== Files written ===")
    for p in [structural_plot, target_plot, regional_plot, rural_plot]:
        print(f"  {p}")
    print()
    print_calibration_summary(base=base_metrics, policy=policy_metrics)
    print_summary(
        times=times, regions=regions, base=base_metrics, policy=policy_metrics
    )


if __name__ == "__main__":
    main()
