"""Macro scorecard: does the model economy look like Korea, 1965-1985?

Solves the baseline and HCI-policy economies of ``scripts/simulate_policy_shock.py`` and
reports the aggregate moments the macro story is about, next to approximate data values.
The data column holds order-of-magnitude reference values only (sources listed in
docs/fresh_look.md, section 1); replace them with the digitised series before using them
for anything beyond orientation.

Also checks that the static equilibrium does not depend on the solver's initial guess.

Run:
    python scripts/macro_scorecard.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from korea_growth.accounting import real_gdp_index, sector_accounts
from korea_growth.checks import aggregate_accounting, cutoff_ordering_violation
from korea_growth.preferences import composite_price, equivalent_income
from korea_growth.solver import initial_guess, solve_dynamic_equilibrium, solve_static_equilibrium
from korea_growth.types import DynamicEquilibriumPath, ModelInputs, SolverOptions
from scripts.simulate_policy_shock import build_baseline_inputs, with_hci_policy

# 1965 -> 1985 reference values; approximate, to be replaced with the digitised series.
# Only the direction is asserted for the last two (sign of the rural gap; near-zero
# mechanisation in 1965).
DATA_TARGETS = {
    "real_gdp_pc_index": "1.00 -> ~4",  # Maddison / PWT real GDP per capita
    "consumption_pc_index": "    n/a",  # purchasing-power check, reported next to real GDP
    "ag_employment_share": "0.59 -> 0.25",  # EAPS: agriculture, forestry & fishing
    "ag_va_share": "0.38 -> 0.13",  # BoK national accounts, current prices (verify)
    "urban_pop_share": "0.32 -> 0.65",  # WDI urban population share
    "exports_gdp": "0.09 -> 0.33",  # national accounts, goods & services
    "imports_gdp": "0.16 -> 0.32",
    "rural_urban_real_income": " <1 -> <1",  # farm vs urban household income per capita
    "traditional_ag_output_share": " ~1 -> <1",  # power tillers per farm household ~0 in 1965
}

LABELS = {
    "real_gdp_pc_index": "Real GDP pc, double-deflated (1965=1)",
    "consumption_pc_index": "Real consumption pc (1965 = 1)",
    "ag_employment_share": "Agriculture employment share (workers)",
    "ag_va_share": "Agriculture value-added share",
    "urban_pop_share": "Urban pop. share (non-'Rural' proxy)",
    "exports_gdp": "Exports / GDP",
    "imports_gdp": "Imports / GDP",
    "rural_urban_real_income": "Rural / urban equivalent income",
    "traditional_ag_output_share": "Traditional-tech share of ag output",
}


class _Slice:
    def __init__(self, path: DynamicEquilibriumPath, t: int):
        self.w, self.r, self.P, self.E = path.w[t], path.r[t], path.P[t], path.E[t]
        self.taubar, self.pibar = float(path.taubar[t]), float(path.pibar[t])


def macro_moments(inputs: ModelInputs, path: DynamicEquilibriumPath) -> dict[str, np.ndarray]:
    dims, params = inputs.dims, inputs.params
    rural = dims.regions.index("Rural")
    urban = [i for i in range(dims.N) if i != rural]
    agri = dims.agri_idx
    out: dict[str, list[float]] = {k: [] for k in LABELS if k != "real_gdp_pc_index"}
    out["cutoff_violation"] = []
    accounts = []

    for t in range(dims.T):
        L_prev = inputs.exog.L0 if t == 0 else path.L[t - 1]
        eq = _Slice(path, t)
        agg = aggregate_accounting(inputs, t, L_prev, eq)
        acc = sector_accounts(inputs, t, L_prev, eq)
        accounts.append(acc)
        L = path.L[t]

        # Consumption purchasing power: disposable income over the local consumption
        # composite price, population-weighted (a purchasing-power measure, not GDP).
        P_comp = np.array([composite_price(path.P[t, d], params.alpha_j) for d in range(dims.N)])
        Y_eq = np.array(
            [
                equivalent_income(path.y_pc[t, d], path.P[t, d], params.alpha_j, params.v_j, params.eta)
                for d in range(dims.N)
            ]
        )
        emp = acc.employment.sum(axis=0)
        va = acc.value_added.sum(axis=0)

        out["consumption_pc_index"].append(float(np.sum(L * path.y_pc[t] / P_comp) / L.sum()))
        out["ag_employment_share"].append(emp[agri] / emp.sum())
        out["ag_va_share"].append(va[agri] / va.sum())
        out["urban_pop_share"].append(1.0 - L[rural] / L.sum())
        out["exports_gdp"].append(agg["EX"] / agg["GDP"])
        out["imports_gdp"].append(agg["IM"] / agg["GDP"])
        out["rural_urban_real_income"].append(Y_eq[rural] / np.average(Y_eq[urban], weights=L[urban]))
        out["traditional_ag_output_share"].append(acc.traditional_ag_output_share)
        out["cutoff_violation"].append(cutoff_ordering_violation(inputs, t, L_prev, eq))

    moments = {k: np.asarray(v) for k, v in out.items()}
    # Total population is normalised to 1 in every period, so levels are per capita.
    moments["real_gdp_pc_index"] = real_gdp_index(accounts)
    moments["consumption_pc_index"] = moments["consumption_pc_index"] / moments["consumption_pc_index"][0]
    return moments


def guess_sensitivity(inputs: ModelInputs, opts: SolverOptions) -> float:
    """Max relative wage difference across solutions started from scaled initial guesses."""
    L0 = inputs.exog.L0
    g0 = initial_guess(inputs=inputs, t=0, L_prev=L0)
    wages = []
    for scale in (0.5, 1.0, 2.0):
        guess = dict(g0, w=g0["w"] * scale, r=g0["r"] * scale, E=g0["E"] * scale)
        wages.append(solve_static_equilibrium(inputs=inputs, t=0, L_prev=L0, guess=guess, options=opts).w)
    return float(max(np.max(np.abs(w / wages[1] - 1.0)) for w in wages))


def main() -> None:
    opts = SolverOptions(max_iter=20000, tol=1e-10, damping=0.25, verbose=False)
    base_inputs = build_baseline_inputs()
    policy_inputs = with_hci_policy(base_inputs)
    base_path = solve_dynamic_equilibrium(inputs=base_inputs, options=opts)
    base = macro_moments(base_inputs, base_path)
    policy = macro_moments(policy_inputs, solve_dynamic_equilibrium(inputs=policy_inputs, options=opts))

    print("Macro scorecard, 1965 -> 1985 (data column: approximate reference values)")
    print(f"{'moment':<38} {'data':>13} {'baseline':>15} {'HCI policy':>15}")
    print("-" * 84)
    for key, label in LABELS.items():
        print(
            f"{label:<38} {DATA_TARGETS[key]:>13}  {base[key][0]:6.3f}->{base[key][-1]:6.3f}"
            f"  {policy[key][0]:6.3f}->{policy[key][-1]:6.3f}"
        )
    print("-" * 84)
    rural = base_inputs.dims.regions.index("Rural")
    print(f"Rural pop. share: L0 = {base_inputs.exog.L0[rural]:.3f}; first solved period = "
          f"{base_path.L[0, rural]:.3f}")
    print(f"Max ag cutoff-ordering violation (baseline): {base['cutoff_violation'].max():.3f}")
    print(f"Initial-guess sensitivity of equilibrium wages: {guess_sensitivity(base_inputs, opts):.2e}")


if __name__ == "__main__":
    main()
