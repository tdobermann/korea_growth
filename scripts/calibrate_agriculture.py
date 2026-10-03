"""Calibrate the agricultural mechanisation and export margins to 1965 targets.

Solves for foreign demand for farm output (Dtilde[Agri]) and the mechanisation fixed cost
(Fbreve[Agri], labour units) so that the 1965 baseline static equilibrium has

- the traditional technology's share of farm output = AG_TARGET_TRADITIONAL_SHARE_1965, and
- farm exports / farm output = AG_TARGET_EXPORT_SHARE_1965,

taking xi = XI_MECHANISATION as given. Agricultural exporters use the mechanised technology,
so in 1965 the mechanised fringe is export-led; domestic diffusion afterwards comes from
rising wages and cheaper machinery (docs/fresh_look.md 2.4).

Prints the calibrated values; paste them into AG_FOREIGN_DEMAND and AG_ADOPTION_FIXED_COST
in scripts/simulate_policy_shock.py.

Run:
    python scripts/calibrate_agriculture.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.optimize import root

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from korea_growth.accounting import sector_accounts
from korea_growth.solver import solve_static_equilibrium
from korea_growth.trade import compute_sector_state
from korea_growth.types import SolverOptions
from scripts.simulate_policy_shock import (
    AG_ADOPTION_FIXED_COST,
    AG_FOREIGN_DEMAND,
    AG_TARGET_EXPORT_SHARE_1965,
    AG_TARGET_TRADITIONAL_SHARE_1965,
    build_baseline_inputs,
)

OPTS = SolverOptions(max_iter=20000, tol=1e-11, damping=0.25, verbose=False)


def moments_1965(ag_foreign_demand: float, ag_adoption_fixed_cost: float) -> tuple[float, float]:
    """(traditional share of farm output, farm exports / farm output) in 1965."""
    inputs = build_baseline_inputs(
        ag_foreign_demand=ag_foreign_demand, ag_adoption_fixed_cost=ag_adoption_fixed_cost
    )
    L0 = inputs.exog.L0
    eq = solve_static_equilibrium(inputs=inputs, t=0, L_prev=L0, options=OPTS)
    acc = sector_accounts(inputs, 0, L0, eq)
    agri = inputs.dims.agri_idx
    st = compute_sector_state(
        t=0, j=agri, dims=inputs.dims, params=inputs.params, exog=inputs.exog,
        L_prev=L0, w=eq.w, r=eq.r, P=eq.P, E=eq.E,
    )
    return acc.traditional_ag_output_share, float(st.R_tilde.sum() / st.gross_output.sum())


def calibrate() -> tuple[float, float]:
    targets = np.array([AG_TARGET_TRADITIONAL_SHARE_1965, AG_TARGET_EXPORT_SHARE_1965])

    def resid(z: np.ndarray) -> np.ndarray:
        trad, exp_share = moments_1965(float(np.exp(z[0])), float(np.exp(z[1])))
        # Log-odds of the traditional share and log export share: well scaled near the targets.
        return np.array(
            [
                np.log(trad / (1.0 - trad)) - np.log(targets[0] / (1.0 - targets[0])),
                np.log(exp_share) - np.log(targets[1]),
            ]
        )

    z0 = np.log([AG_FOREIGN_DEMAND, AG_ADOPTION_FIXED_COST])
    sol = root(resid, z0, method="hybr", options={"xtol": 1e-10})
    if not sol.success:
        raise RuntimeError(f"calibration failed: {sol.message}")
    return float(np.exp(sol.x[0])), float(np.exp(sol.x[1]))


def main() -> None:
    d_ag, fb_ag = calibrate()
    trad, exp_share = moments_1965(d_ag, fb_ag)
    print(f"AG_FOREIGN_DEMAND = {d_ag:.5f}")
    print(f"AG_ADOPTION_FIXED_COST = {fb_ag:.5f}")
    print(f"1965 traditional share of farm output: {trad:.4f} (target {AG_TARGET_TRADITIONAL_SHARE_1965})")
    print(f"1965 farm exports / farm output:       {exp_share:.4f} (target {AG_TARGET_EXPORT_SHARE_1965})")


if __name__ == "__main__":
    main()
