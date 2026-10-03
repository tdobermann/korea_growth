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

from korea_growth.checks import aggregate_accounting, cutoff_ordering_violation
from korea_growth.preferences import composite_price, real_income_index
from korea_growth.solver import initial_guess, solve_dynamic_equilibrium, solve_static_equilibrium
from korea_growth.trade import compute_sector_state
from korea_growth.types import DynamicEquilibriumPath, ModelInputs, SolverOptions
from scripts.simulate_policy_shock import build_baseline_inputs, with_hci_policy

# 1965 -> 1985 reference values; approximate, to be replaced with the digitised series.
# Only the direction is asserted for the last two (sign of the rural gap; near-zero
# mechanisation in 1965).
DATA_TARGETS = {
    "real_gdp_pc_index": "1.00 -> ~4",  # Maddison / PWT real GDP per capita
    "ag_employment_share": "0.59 -> 0.25",  # EAPS: agriculture, forestry & fishing
    "urban_pop_share": "0.32 -> 0.65",  # WDI urban population share
    "exports_gdp": "0.09 -> 0.33",  # national accounts, goods & services
    "imports_gdp": "0.16 -> 0.32",
    "rural_urban_real_income": " <1 -> <1",  # farm vs urban household income per capita
    "traditional_ag_output_share": " ~1 -> <1",  # power tillers per farm household ~0 in 1965
}

LABELS = {
    "real_gdp_pc_index": "Real GDP per capita (1965 = 1)",
    "ag_employment_share": "Agriculture employment share",
    "urban_pop_share": "Urban pop. share (non-'Rural' proxy)",
    "exports_gdp": "Exports / GDP",
    "imports_gdp": "Imports / GDP",
    "rural_urban_real_income": "Rural / urban real income",
    "traditional_ag_output_share": "Traditional-tech share of ag output",
}


def _sector_labor(inputs: ModelInputs, path: DynamicEquilibriumPath, t: int) -> tuple[np.ndarray, float]:
    """Economy-wide variable labor payments by sector and the traditional share of ag output."""
    exog, sigma = inputs.exog, inputs.params.sigma
    agri = inputs.dims.agri_idx
    L_prev = exog.L0 if t == 0 else path.L[t - 1]
    labor = np.zeros(inputs.dims.J)
    trad_share = np.nan
    for j in range(inputs.dims.J):
        st = compute_sector_state(
            t=t, j=j, dims=inputs.dims, params=inputs.params, exog=exog, L_prev=L_prev,
            w=path.w[t], r=path.r[t], P=path.P[t], E=path.E[t],
        )
        tfc = (sigma - 1.0) / sigma / (1.0 - exog.s[t, :, j])
        lab_share = (1.0 - exog.beta[t, :, j]) * exog.gamma[t, :, j]
        if j == agri:
            lab_share_new = (1.0 - exog.betabreve[t, :, j]) * exog.gammabreve[t, :, j]
            labor[j] = np.sum(tfc * (lab_share * st.R_trad + lab_share_new * (st.R_breve + st.R_tilde)))
            trad_share = float(st.R_trad.sum() / st.gross_output.sum())
        else:
            labor[j] = np.sum(tfc * lab_share * st.gross_output)
    return labor, trad_share


class _Slice:
    def __init__(self, path: DynamicEquilibriumPath, t: int):
        self.w, self.r, self.P, self.E = path.w[t], path.r[t], path.P[t], path.E[t]
        self.taubar, self.pibar = float(path.taubar[t]), float(path.pibar[t])


def macro_moments(inputs: ModelInputs, path: DynamicEquilibriumPath) -> dict[str, np.ndarray]:
    dims, params = inputs.dims, inputs.params
    rural = dims.regions.index("Rural")
    urban = [i for i in range(dims.N) if i != rural]
    out: dict[str, list[float]] = {k: [] for k in LABELS}
    out["cutoff_violation"] = []

    for t in range(dims.T):
        L_prev = inputs.exog.L0 if t == 0 else path.L[t - 1]
        agg = aggregate_accounting(inputs, t, L_prev, _Slice(path, t))
        L = path.L[t]

        P_comp = np.array([composite_price(path.P[t, d], params.alpha_j) for d in range(dims.N)])
        P_nat = float(np.exp(np.dot(L, np.log(P_comp))))
        Y_real = np.array(
            [real_income_index(path.y_pc[t, d], path.P[t, d], params.alpha_j, params.v_j) for d in range(dims.N)]
        )
        labor, trad_share = _sector_labor(inputs, path, t)

        out["real_gdp_pc_index"].append(agg["GDP"] / P_nat / L.sum())
        out["ag_employment_share"].append(labor[dims.agri_idx] / labor.sum())
        out["urban_pop_share"].append(1.0 - L[rural] / L.sum())
        out["exports_gdp"].append(agg["EX"] / agg["GDP"])
        out["imports_gdp"].append(agg["IM"] / agg["GDP"])
        out["rural_urban_real_income"].append(Y_real[rural] / np.average(Y_real[urban], weights=L[urban]))
        out["traditional_ag_output_share"].append(trad_share)
        out["cutoff_violation"].append(cutoff_ordering_violation(inputs, t, L_prev, _Slice(path, t)))

    moments = {k: np.asarray(v) for k, v in out.items()}
    moments["real_gdp_pc_index"] = moments["real_gdp_pc_index"] / moments["real_gdp_pc_index"][0]
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
