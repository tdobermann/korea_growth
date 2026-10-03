from __future__ import annotations

import numpy as np
import pytest

from korea_growth.accounting import sector_accounts
from korea_growth.production import unit_cost_bundle
from korea_growth.solver import solve_dynamic_equilibrium
from korea_growth.types import SolverOptions
from korea_growth.checks import pigl_share_violation
from scripts.calibrate_history import history_moments, model_value
from scripts.data_targets import CALIBRATION_KEYS, target
from scripts.simulate_policy_shock import (
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

    base = collect_region_metrics(inputs=baseline_inputs, path=baseline_path)
    policy = collect_region_metrics(inputs=policy_inputs, path=policy_path)
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


def test_baseline_reproduces_structural_transformation(policy_paths):
    # The calibrated baseline hits the calibration targets of scripts/data_targets.py and
    # starts from the observed 1965 population (inverted amenities; no first-period jump).
    baseline_inputs, _, baseline_path, _ = policy_paths
    np.testing.assert_allclose(baseline_path.L[0], baseline_inputs.exog.L0, atol=1e-6)
    moments = history_moments(baseline_inputs, baseline_path)
    for key, year in CALIBRATION_KEYS:
        value, tgt = model_value(moments, key, year), target(key, year).value
        if key == "real_gdp_pc_ratio":
            assert value == pytest.approx(tgt, rel=0.02), key
        else:
            assert value == pytest.approx(tgt, abs=0.01), (key, year)
    assert pigl_share_violation(baseline_inputs, baseline_path) == 0.0


def test_mechanisation_diffuses_faster_under_hci(policy_paths):
    # Interior adoption margin: traditional farming dominates in 1965 and declines, faster
    # with HCI (higher wages, cheaper machinery, lower adoption costs).
    baseline_inputs, policy_inputs, baseline_path, policy_path = policy_paths

    def trad_share(inputs, path, t):
        L_prev = inputs.exog.L0 if t == 0 else path.L[t - 1]
        return sector_accounts(inputs, t, L_prev, _Slice(path, t)).traditional_ag_output_share

    base_0, base_T = trad_share(baseline_inputs, baseline_path, 0), trad_share(baseline_inputs, baseline_path, -1)
    pol_T = trad_share(policy_inputs, policy_path, -1)
    assert base_0 > 0.9
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
