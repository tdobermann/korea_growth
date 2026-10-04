"""Calibrate the 1965-1985 baseline to Korea's structural transformation.

Solves for eight parameters of ``scripts/korea_baseline.HistoryCalibration`` so that the
baseline reproduces the eight calibration targets in ``scripts/data_targets.py``:

    parameter                         main target it moves
    g_mnf      mnf TFP growth         real GDP per capita, 1985 / 1965
    g_farm     farm (= services) TFP  manufacturing VA share, 1985
    eta        PIGL income elasticity agriculture employment share, 1985
    v_food     PIGL food shifter      agriculture employment share, 1965
    mnf_share_nonfood                 manufacturing VA share, 1965
    d_mnf_1965 foreign demand level   exports / GDP, 1965
    g_export   foreign demand growth  exports / GDP, 1985
    urban_nonfarm_tfp  urban premium  urban population share, 1980 (sourced)

Each evaluation first inverts the 1965 amenities so that the observed 1965 population is an
equilibrium (``korea_growth.inversion``); urbanisation after 1965 is then a model outcome.
The PIGL share bounds are imposed as a penalty, so the share guard never binds at the
solution. Assumptions held fixed are listed in ``scripts/korea_baseline.py``.

Run (about 15-30 minutes):
    python scripts/calibrate_history.py
Prints the calibrated values for ``HistoryCalibration`` and the targeted and untargeted fit.
"""

from __future__ import annotations

import sys
from dataclasses import fields, replace
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from korea_growth.accounting import real_gdp_index, sector_accounts
from korea_growth.checks import aggregate_accounting, pigl_share_violation
from korea_growth.inversion import invert_amenities
from korea_growth.solver import solve_dynamic_equilibrium
from korea_growth.types import DynamicEquilibriumPath, ModelInputs, SolverOptions
from scripts.data_targets import CALIBRATION_KEYS, TARGETS, target
from scripts.korea_baseline import CURRENT, RURAL, YEARS, HistoryCalibration, build_baseline_inputs

OPTS = SolverOptions(max_iter=20000, tol=1e-10, damping=0.25, verbose=False)
FREE = ["g_mnf", "g_farm", "eta", "v_food", "mnf_share_nonfood", "d_mnf_1965", "g_export", "urban_nonfarm_tfp"]
BOUNDS = {
    "g_mnf": (0.0, 0.2),
    "g_farm": (-0.05, 0.15),
    "eta": (0.05, 0.99),
    "v_food": (0.01, 2.0),
    "mnf_share_nonfood": (0.02, 0.9),
    "d_mnf_1965": (1e-4, 2.0),
    "g_export": (-0.1, 0.4),
    "urban_nonfarm_tfp": (0.5, 5.0),
}


class _Slice:
    def __init__(self, path: DynamicEquilibriumPath, t: int):
        self.w, self.r, self.P, self.E = path.w[t], path.r[t], path.P[t], path.E[t]
        self.taubar, self.pibar = float(path.taubar[t]), float(path.pibar[t])


def history_moments(inputs: ModelInputs, path: DynamicEquilibriumPath) -> dict[str, np.ndarray]:
    """National structural-transformation moments by period (arrays of length T)."""
    dims = inputs.dims
    farm, mnf = dims.farm_idx, dims.heavy_idx
    other_ag = [j for j in farm if j != dims.agri_idx]
    sigma = inputs.params.sigma
    out: dict[str, list[float]] = {
        k: [] for k in (
            "ag_employment_share", "ag_va_share", "mnf_va_share", "urban_pop_share",
            "exports_gdp", "imports_gdp", "otherag_import_share", "traditional_rice_share",
        )
    }
    accounts = []
    for t in range(dims.T):
        L_prev = inputs.exog.L0 if t == 0 else path.L[t - 1]
        eq = _Slice(path, t)
        acc = sector_accounts(inputs, t, L_prev, eq)
        agg = aggregate_accounting(inputs, t, L_prev, eq)
        accounts.append(acc)
        emp, va = acc.employment.sum(axis=0), acc.value_added.sum(axis=0)
        out["ag_employment_share"].append(emp[farm].sum() / emp.sum())
        out["ag_va_share"].append(va[farm].sum() / va.sum())
        out["mnf_va_share"].append(va[mnf] / va.sum())
        out["urban_pop_share"].append(1.0 - path.L[t, RURAL] / path.L[t].sum())
        out["exports_gdp"].append(agg["EX"] / agg["GDP"])
        out["imports_gdp"].append(agg["IM"] / agg["GDP"])
        if other_ag:
            j = other_ag[0]
            imp = np.power(inputs.exog.tautilde[t, j] * inputs.exog.ptilde[t, j], 1.0 - sigma)
            share = imp / np.power(path.P[t][:, j], 1.0 - sigma)
            out["otherag_import_share"].append(float(np.sum(share * path.E[t][:, j]) / np.sum(path.E[t][:, j])))
        else:
            out["otherag_import_share"].append(np.nan)
        out["traditional_rice_share"].append(acc.traditional_ag_output_share)
    moments = {k: np.asarray(v) for k, v in out.items()}
    moments["real_gdp_pc_index"] = real_gdp_index(accounts)
    return moments


def model_value(moments: dict[str, np.ndarray], key: str, year: int) -> float:
    t = int(np.flatnonzero(YEARS == year)[0])
    if key == "real_gdp_pc_ratio":
        return float(moments["real_gdp_pc_index"][t])
    return float(moments[key][t])


def solve_history(cal: HistoryCalibration) -> tuple[HistoryCalibration, ModelInputs, DynamicEquilibriumPath]:
    """Invert 1965 amenities for ``cal`` and solve the baseline path."""
    inputs = build_baseline_inputs(cal)
    vbar, _ = invert_amenities(
        inputs=inputs, t=0, L_prev=inputs.exog.L0, L_target=inputs.exog.L0, options=OPTS
    )
    cal = replace(cal, vbar_1965=tuple(float(x) for x in vbar))
    inputs = build_baseline_inputs(cal)
    return cal, inputs, solve_dynamic_equilibrium(inputs=inputs, options=OPTS)


def residuals(x: np.ndarray, base: HistoryCalibration) -> np.ndarray:
    cal = replace(base, **dict(zip(FREE, map(float, x))), g_svc=float(x[FREE.index("g_farm")]))
    try:
        _, inputs, path = solve_history(cal)
    except (RuntimeError, ValueError, FloatingPointError):
        return np.full(len(CALIBRATION_KEYS) + 1, 10.0)
    m = history_moments(inputs, path)
    res = []
    for key, year in CALIBRATION_KEYS:
        tgt = target(key, year).value
        val = model_value(m, key, year)
        # Log deviations for the GDP ratio, level deviations for shares.
        res.append(np.log(val / tgt) if key == "real_gdp_pc_ratio" else val - tgt)
    res.append(10.0 * pigl_share_violation(inputs, path))
    return np.asarray(res)


def calibrate(start: HistoryCalibration = CURRENT) -> HistoryCalibration:
    x0 = np.array([getattr(start, k) for k in FREE])
    lo = np.array([BOUNDS[k][0] for k in FREE])
    hi = np.array([BOUNDS[k][1] for k in FREE])
    sol = least_squares(
        residuals, np.clip(x0, lo, hi), bounds=(lo, hi), args=(start,), x_scale="jac",
        diff_step=1e-4, xtol=1e-10, ftol=1e-12, gtol=1e-12, max_nfev=400, verbose=1,
    )
    cal = replace(start, **dict(zip(FREE, map(float, sol.x))), g_svc=float(sol.x[FREE.index("g_farm")]))
    cal, _, _ = solve_history(cal)
    return cal


def report(cal: HistoryCalibration) -> None:
    _, inputs, path = solve_history(cal)
    m = history_moments(inputs, path)
    print("Targeted moments (model vs target; status of the target value)")
    for key, year in CALIBRATION_KEYS:
        tg = target(key, year)
        print(f"  {key:<22} {year}  model {model_value(m, key, year):7.3f}  target {tg.value:6.3f}  [{tg.status}]")
    print("Untargeted moments")
    for tg in TARGETS:
        if (tg.key, tg.year) in CALIBRATION_KEYS or (tg.key, tg.year) == ("urban_pop_share", 1965):
            continue
        print(f"  {tg.key:<22} {tg.year}  model {model_value(m, tg.key, tg.year):7.3f}  data   {tg.value:6.3f}  [{tg.status}]")
    for key in ("otherag_import_share", "traditional_rice_share", "imports_gdp"):
        print(f"  {key:<22} 1965->1985  model {m[key][0]:.3f} -> {m[key][-1]:.3f}  (no data in repository)")
    print(f"PIGL share-bound violation along the path: {pigl_share_violation(inputs, path):.2e}")


def main() -> None:
    cal = calibrate()
    print("\nHistoryCalibration(")
    for f in fields(HistoryCalibration):
        val = getattr(cal, f.name)
        if isinstance(val, tuple):
            val = "(" + ", ".join(f"{v:.6f}" for v in val) + ")"
        elif isinstance(val, float):
            val = f"{val:.6f}"
        print(f"    {f.name}={val},")
    print(")\n")
    report(cal)


if __name__ == "__main__":
    main()
