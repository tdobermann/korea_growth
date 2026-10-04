"""Korea 1965-1985 baseline economy: 5 stylised regions, 4 sectors, 6 periods.

Sectors
  Rice           staple grain; internationally non-traded (protected: import controls and,
                 from 1969, government procurement); carries the mechanisation margin
  OtherAg        other grains (wheat, barley, feed grains) and other farm output; competes
                 with imports at world prices, so grain import dependence is an equilibrium
                 outcome (not exported)
  Manufacturing  traded; the export sector
  Services       internationally non-traded

The structural-transformation block (sectoral TFP growth, PIGL Engel parameters, the 1965
amenities that make the observed 1965 population an equilibrium) is calibrated by
``scripts/calibrate_history.py`` to the targets in ``scripts/data_targets.py``. Values set
here by assumption, without data behind them, are marked ASSUMPTION.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from korea_growth.checks import validate_inputs
from korea_growth.types import ModelDimensions, ModelExogenousPaths, ModelInputs, ModelParameters

YEARS = np.array([1965, 1968, 1973, 1975, 1980, 1985])
REGIONS = ["Seoul", "Busan", "Changwon", "Daegu", "Rural"]
SECTORS = ["Rice", "OtherAg", "Manufacturing", "Services"]
FARM_SECTORS = ("Rice", "OtherAg")
URBAN = [0, 1, 2, 3]
RURAL = 4

# ASSUMPTION: split of the 1965 urban population across the four stylised cities, carried
# over from the earlier calibration (Seoul : Busan : Changwon : Daegu = 20 : 12 : 3 : 10).
CITY_SPLIT = np.array([0.20, 0.12, 0.03, 0.10]) / 0.45
# ASSUMPTION: rice's share of the food asymptote alpha and Engel shifter v.
RICE_SHARE_OF_FOOD = 0.5


@dataclass(frozen=True)
class HistoryCalibration:
    """Parameters set by scripts/calibrate_history.py (defaults: current calibrated values)."""

    # Annual TFP growth by sector (log points), common across regions.
    g_farm: float = 0.031693
    g_mnf: float = 0.041483
    g_svc: float = 0.031693  # calibration ties g_svc = g_farm (no sectoral TFP data yet)
    # Foreign demand for manufactures: 1965 level and annual growth (log points).
    d_mnf_1965: float = 0.004419
    g_export: float = 0.239667
    # PIGL: eta, food Engel shifter v_food (> 0), food asymptote alpha_food, and the
    # manufacturing share of the non-food asymptote.
    eta: float = 0.391253
    v_food: float = 0.509502
    alpha_food: float = 0.05
    mnf_share_nonfood: float = 0.020000
    # Farm TFP in the cities relative to Rural (farming is mostly rural). ASSUMPTION.
    urban_farm_tfp: float = 0.40
    # Non-farm TFP in the cities relative to Rural (urban productivity premium), calibrated to
    # the 1980 urban population share.
    urban_nonfarm_tfp: float = 1.173910
    # 1965 urban population share; the 1965 amenities make it an equilibrium.
    urban_share_1965: float = 0.32
    # Amenities (N,) that make the 1965 population an equilibrium (inverted; Seoul = 1).
    vbar_1965: tuple = (1.000000, 0.471456, 0.198998, 0.448559, 0.710297)
    # Mechanisation fixed cost for rice (labour units). Not identified without tiller data.
    rice_adoption_fixed_cost: float = 0.80


CURRENT = HistoryCalibration()


def build_baseline_inputs(cal: HistoryCalibration = CURRENT) -> ModelInputs:
    """Construct the 1965-1985 baseline economy for calibration ``cal``."""

    times = list(range(1, len(YEARS) + 1))
    dims = ModelDimensions(
        times=times,
        regions=REGIONS,
        sectors=SECTORS,
        agri_sector="Rice",
        heavy_mnf_sector="Manufacturing",
        services_sector="Services",
        farm_sectors=FARM_SECTORS,
        # Occupations: farming (rice and other crops share the farm wage), manufacturing,
        # services. Active only with params.eps_occ (sector-specific wages).
        occupation_of_sector=(0, 0, 1, 2),
    )
    T, N, J = dims.T, dims.N, dims.J
    R, O, MF, SV = range(4)
    dt = (YEARS - YEARS[0]).astype(float)

    # --- Preferences: PIGL. Food = Rice + OtherAg. v sums to zero (food vs services). ---
    a_f, v_f = cal.alpha_food, cal.v_food
    alpha = np.array(
        [
            RICE_SHARE_OF_FOOD * a_f,
            (1 - RICE_SHARE_OF_FOOD) * a_f,
            (1 - a_f) * cal.mnf_share_nonfood,
            (1 - a_f) * (1 - cal.mnf_share_nonfood),
        ]
    )
    v = np.array([RICE_SHARE_OF_FOOD * v_f, (1 - RICE_SHARE_OF_FOOD) * v_f, 0.0, -v_f])

    params = ModelParameters(
        sigma=4.0,
        theta=5.0,
        kappa=8.0,
        xi=1.2,  # mechanisation mainly labour-saving (docs/fresh_look.md 2.4)
        rho_j=np.array([0.03, 0.03, 0.12, 0.06]),
        iota=-0.02,
        eta=cal.eta,
        nu=5.0,
        alpha_j=alpha,
        v_j=v,
        fixed_costs_in_labor=True,
    )

    # --- Population: observed 1965 urban share, stylised split across cities. ---
    L0 = np.empty(N)
    L0[URBAN] = cal.urban_share_1965 * CITY_SPLIT
    L0[RURAL] = 1.0 - cal.urban_share_1965

    # --- Firm mass ---
    M = np.ones((T, J))
    M[:, MF] = 2.0

    # --- Productivity: 1965 levels (carried over) times sectoral TFP growth. ---
    A0 = np.ones((N, J))
    A0[[0, 1, 2, 3], MF] = [1.25, 1.45, 1.55, 1.15]
    A0[0, SV] = 0.98
    A0[URBAN, R] *= cal.urban_farm_tfp
    A0[URBAN, O] *= cal.urban_farm_tfp
    A0[URBAN, MF] *= cal.urban_nonfarm_tfp
    A0[URBAN, SV] *= cal.urban_nonfarm_tfp
    growth = np.stack(
        [np.exp(cal.g_farm * dt), np.exp(cal.g_farm * dt), np.exp(cal.g_mnf * dt), np.exp(cal.g_svc * dt)],
        axis=-1,
    )  # (T, J)
    A = A0[None, :, :] * growth[:, None, :]

    # --- Technology shares (carried over from the 3-sector calibration; farm rows shared) ---
    beta = np.zeros((T, N, J))
    beta[..., [R, O]] = 0.40
    beta[..., MF] = 0.15
    beta[..., SV] = 0.25
    gamma = np.zeros((T, N, J))
    gamma[..., [R, O]] = 0.55
    gamma[..., MF] = 0.40
    gamma[..., SV] = 0.70
    io = np.zeros((J, J))  # io[j, k]: share of input k in sector j
    io[R] = [0.05, 0.05, 0.20, 0.15]
    io[O] = [0.05, 0.05, 0.20, 0.15]
    io[MF] = [0.025, 0.025, 0.35, 0.20]
    io[SV] = [0.025, 0.025, 0.10, 0.15]
    gamma_io = np.broadcast_to(io, (T, N, J, J)).copy()

    # Mechanised rice: more machinery input, same land share of gross output.
    gammabreve_io = gamma_io.copy()
    gammabreve_io[..., R, MF] = 0.35
    gammabreve = gamma.copy()
    gammabreve[..., R] = 1.0 - gammabreve_io[..., R, :].sum(axis=-1)
    betabreve = beta.copy()
    betabreve[..., R] = gamma[..., R] * beta[..., R] / gammabreve[..., R]

    # --- Fixed costs: labour requirements (old numeraire values at the old 1965 wage). ---
    ref_wage = 0.2547
    F = np.full((T, N, J), 0.20) / ref_wage
    F[..., MF] *= 0.52
    Fbreve = np.zeros((T, N, J))
    Fbreve[..., R] = cal.rice_adoption_fixed_cost
    Ftilde = np.full((T, N, J), 0.05) / ref_wage

    s = np.zeros((T, N, J))
    s[..., [R, O]] = 0.05

    # --- Foreign demand and prices: only manufactures are exported. OtherAg competes with
    # imports but is not exported (simplification: farm exports were small). ---
    Dtilde = np.zeros((T, J))
    Dtilde[:, MF] = cal.d_mnf_1965 * np.exp(cal.g_export * dt)
    ptilde = np.ones((T, J))

    Vbar = np.broadcast_to(np.asarray(cal.vbar_1965, dtype=float), (T, N)).copy()

    base_tau = np.array(
        [
            [1.00, 1.30, 1.35, 1.25, 1.50],
            [1.30, 1.00, 1.10, 1.20, 1.40],
            [1.35, 1.10, 1.00, 1.15, 1.35],
            [1.25, 1.20, 1.15, 1.00, 1.30],
            [1.50, 1.40, 1.35, 1.30, 1.00],
        ]
    )
    tau = np.broadcast_to(base_tau, (T, J, N, N)).copy()
    tautilde = np.full((T, J, N), 1.5)
    tautilde[:, :, 1] = 1.3
    tautilde[:, :, 2] = 1.35

    base_delta = np.array(
        [
            [1.00, 1.08, 1.10, 1.08, 1.15],
            [1.08, 1.00, 1.05, 1.08, 1.12],
            [1.10, 1.05, 1.00, 1.06, 1.10],
            [1.08, 1.08, 1.06, 1.00, 1.10],
            [1.15, 1.12, 1.10, 1.10, 1.00],
        ]
    )
    delta = np.broadcast_to(base_delta, (T, N, N)).copy()

    H = np.full((T, N), 1.0)
    H[:, 0] = 0.7
    H[:, RURAL] = 2.0

    tax_spending = np.array([0.005, 0.01, 0.02, 0.025, 0.02, 0.015])

    exog = ModelExogenousPaths(
        L0=L0, M=M, Vbar=Vbar, A=A, beta=beta, gamma=gamma, gamma_io=gamma_io,
        betabreve=betabreve, gammabreve=gammabreve, gammabreve_io=gammabreve_io,
        F=F, Fbreve=Fbreve, Ftilde=Ftilde, s=s, tau=tau, tautilde=tautilde,
        Dtilde=Dtilde, ptilde=ptilde, delta=delta, H=H,
        tax_spending_on_building_H_and_roads=tax_spending,
        nontraded=np.array([True, False, False, True]),
    )
    inputs = ModelInputs(dims=dims, params=params, exog=exog)
    validate_inputs(inputs)
    return inputs
