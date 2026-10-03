from __future__ import annotations

import numpy as np
import pytest

from korea_growth.accounting import sector_accounts
from korea_growth.production import unit_cost_bundle
from korea_growth.solver import solve_dynamic_equilibrium
from korea_growth.types import SolverOptions
from scripts.calibrate_agriculture import moments_1965
from scripts.simulate_policy_shock import (
    AG_ADOPTION_FIXED_COST,
    AG_FOREIGN_DEMAND,
    AG_TARGET_EXPORT_SHARE_1965,
    AG_TARGET_TRADITIONAL_SHARE_1965,
    aggregate_output_shares,
    build_baseline_inputs,
    collect_region_metrics,
    with_hci_policy,
)


class _Slice:
    def __init__(self, path, t):
        self.w, self.r, self.P, self.E = path.w[t], path.r[t], path.P[t], path.E[t]


@pytest.fixture(scope="module")
def policy_paths():
    opts = SolverOptions(max_iter=3000, tol=1e-8, damping=0.25, verbose=False)

    baseline_inputs = build_baseline_inputs()
    policy_inputs = with_hci_policy(baseline_inputs)

    baseline_path = solve_dynamic_equilibrium(inputs=baseline_inputs, options=opts)
    policy_path = solve_dynamic_equilibrium(inputs=policy_inputs, options=opts)
    return baseline_inputs, policy_inputs, baseline_path, policy_path


@pytest.fixture(scope="module")
def policy_metrics(policy_paths):
    baseline_inputs, policy_inputs, baseline_path, policy_path = policy_paths

    agri_idx = baseline_inputs.dims.sectors.index("Agri")
    base = collect_region_metrics(
        inputs=baseline_inputs,
        path=baseline_path,
        target_sector_idx=agri_idx,
    )
    policy = collect_region_metrics(
        inputs=policy_inputs,
        path=policy_path,
        target_sector_idx=agri_idx,
    )
    return base, policy


def test_policy_matches_directional_targets(policy_metrics):
    base, policy = policy_metrics
    base_agg = aggregate_output_shares(base)
    policy_agg = aggregate_output_shares(policy)

    assert policy_agg[-1, 0] < base_agg[-1, 0]
    assert policy_agg[-1, 1] > base_agg[-1, 1]
    assert policy["wage"][-1, 2] > base["wage"][-1, 2]
    assert policy["mnf_output_share"][-1, 2] > base["mnf_output_share"][-1, 2]
    assert policy["pop_share"][-1, 0] < base["pop_share"][-1, 0]
    assert policy["pop_share"][-1, 2] >= base["pop_share"][-1, 2]
    assert policy["income_pc"][-1, 4] > base["income_pc"][-1, 4]
    assert policy["services_output_share"][-1, 3] > base["services_output_share"][-1, 3]
    assert policy["services_output_share"][-1, 4] > base["services_output_share"][-1, 4]


def test_agricultural_calibration_hits_1965_targets():
    trad, export_share = moments_1965(AG_FOREIGN_DEMAND, AG_ADOPTION_FIXED_COST)
    assert trad == pytest.approx(AG_TARGET_TRADITIONAL_SHARE_1965, abs=1e-4)
    assert export_share == pytest.approx(AG_TARGET_EXPORT_SHARE_1965, abs=1e-4)


def test_mechanisation_diffuses_faster_under_hci(policy_paths):
    # Interior adoption margin: traditional farming dominates in 1965 and declines, faster
    # with HCI (higher wages, cheaper machinery, lower adoption costs).
    baseline_inputs, policy_inputs, baseline_path, policy_path = policy_paths

    def trad_share(inputs, path, t):
        L_prev = inputs.exog.L0 if t == 0 else path.L[t - 1]
        return sector_accounts(inputs, t, L_prev, _Slice(path, t)).traditional_ag_output_share

    base_0, base_T = trad_share(baseline_inputs, baseline_path, 0), trad_share(baseline_inputs, baseline_path, -1)
    pol_T = trad_share(policy_inputs, policy_path, -1)
    assert 0.9 < base_0 < 1.0
    assert base_T < base_0
    assert pol_T < base_T


def test_unit_cost_bundle_handles_zero_input_shares():
    r = np.array([1.2, 0.9])
    w = np.array([0.8, 1.1])
    P = np.array([[1.0, 1.1, 0.9], [1.2, 0.95, 1.05]])
    beta = np.array([0.4, 0.3])
    gamma = np.array([0.55, 0.60])
    gamma_io = np.array([[0.10, 0.20, 0.00], [0.00, 0.15, 0.25]])

    observed = unit_cost_bundle(r=r, w=w, P=P, beta=beta, gamma=gamma, gamma_io=gamma_io)

    expected = []
    for idx in range(2):
        va = (
            (1.0 / gamma[idx])
            * (r[idx] / beta[idx]) ** beta[idx]
            * (w[idx] / (1.0 - beta[idx])) ** (1.0 - beta[idx])
        ) ** gamma[idx]
        material = 1.0
        for share, price in zip(gamma_io[idx], P[idx]):
            if share > 0.0:
                material *= (price / share) ** share
        expected.append(va * material)

    np.testing.assert_allclose(observed, np.asarray(expected))
