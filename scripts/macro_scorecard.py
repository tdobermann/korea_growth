"""Macro scorecard: does the model economy look like Korea, 1965-1985?

Solves the baseline and HCI-policy economies of ``scripts/simulate_policy_shock.py`` and
reports the aggregate moments the macro story is about, next to the data values in
``scripts/data_targets.py``. Each data value carries its provenance: values marked * are
unverified approximations awaiting the digitised series, and ? means the repository has no
data for that moment.

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

from korea_growth.checks import cutoff_ordering_violation, pigl_share_violation
from korea_growth.preferences import equivalent_income
from korea_growth.solver import initial_guess, solve_dynamic_equilibrium, solve_static_equilibrium
from korea_growth.types import DynamicEquilibriumPath, ModelInputs, SolverOptions
from scripts.calibrate_history import history_moments
from scripts.data_targets import CALIBRATION_KEYS, MISSING, TARGETS
from scripts.korea_baseline import RURAL, URBAN, YEARS, build_baseline_inputs
from scripts.simulate_policy_shock import with_hci_policy

LABELS = {
    "real_gdp_pc_index": "Real GDP pc, double-deflated (1965=1)",
    "ag_employment_share": "Agriculture employment share (workers)",
    "ag_va_share": "Agriculture value-added share",
    "mnf_va_share": "Manufacturing value-added share",
    "urban_pop_share": "Urban pop. share (non-'Rural')",
    "exports_gdp": "Exports / GDP",
    "imports_gdp": "Imports / GDP",
    "otherag_import_share": "Import share of other-farm demand",
    "traditional_rice_share": "Traditional-tech share of rice output",
    "rural_urban_real_income": "Rural / urban equivalent income",
}


def _data_column(key: str) -> str:
    """Data values for 1965 and 1985 from the registry, '*' = unverified, '?' = none."""
    if key == "real_gdp_pc_index":
        key = "real_gdp_pc_ratio"
    vals = {tg.year: tg for tg in TARGETS if tg.key == key}
    cells = []
    for year in (1965, 1985):
        if key == "real_gdp_pc_ratio" and year == 1965:
            cells.append("1.00")
        elif year in vals:
            cells.append(f"{vals[year].value:.2f}{'*' if vals[year].status == 'unverified' else ''}")
        else:
            cells.append("?")
    return " -> ".join(cells)


def macro_moments(inputs: ModelInputs, path: DynamicEquilibriumPath) -> dict[str, np.ndarray]:
    moments = history_moments(inputs, path)
    params = inputs.params
    ratio = []
    cutoff = []
    for t in range(inputs.dims.T):
        L = path.L[t]
        y_eq = np.array(
            [
                equivalent_income(path.y_pc[t, d], path.P[t, d], params.alpha_j, params.v_j, params.eta)
                for d in range(inputs.dims.N)
            ]
        )
        ratio.append(y_eq[RURAL] / np.average(y_eq[URBAN], weights=L[URBAN]))
        L_prev = inputs.exog.L0 if t == 0 else path.L[t - 1]
        cutoff.append(cutoff_ordering_violation(inputs, t, L_prev, path.at(t)))
    moments["rural_urban_real_income"] = np.asarray(ratio)
    moments["cutoff_violation"] = np.asarray(cutoff)
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
    policy_path = solve_dynamic_equilibrium(inputs=policy_inputs, options=opts)
    policy = macro_moments(policy_inputs, policy_path)

    targeted = {key for key, _ in CALIBRATION_KEYS} | {"real_gdp_pc_index"}
    print("Macro scorecard, 1965 -> 1985. Data: * = unverified approximate value, ? = no data in")
    print("the repository (see scripts/data_targets.py). T = calibration target.")
    print(f"{'moment':<40} {'data':>14} {'baseline':>15} {'HCI policy':>15}")
    print("-" * 88)
    for key, label in LABELS.items():
        flag = "T" if key in targeted else " "
        print(
            f"{label:<38}{flag:>2} {_data_column(key):>14}  {base[key][0]:6.3f}->{base[key][-1]:6.3f}"
            f"  {policy[key][0]:6.3f}->{policy[key][-1]:6.3f}"
        )
    print("-" * 88)
    t1980 = int(np.flatnonzero(YEARS == 1980)[0])
    print(f"Urban share 1980: baseline {base['urban_pop_share'][t1980]:.3f} (paper draft: 0.57, targeted)")
    print(f"Max ag cutoff-ordering violation (baseline): {base['cutoff_violation'].max():.3f}")
    print(
        f"PIGL share-bound violation (baseline / HCI): {pigl_share_violation(base_inputs, base_path):.1e}"
        f" / {pigl_share_violation(policy_inputs, policy_path):.1e}"
    )
    print(f"Initial-guess sensitivity of equilibrium wages: {guess_sensitivity(base_inputs, opts):.2e}")
    print("Moments with no data in the repository yet:")
    for item in MISSING:
        print(f"  - {item}")


if __name__ == "__main__":
    main()
