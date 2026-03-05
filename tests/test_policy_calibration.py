from __future__ import annotations

import numpy as np
import pytest

from korea_growth.production import unit_cost_bundle
from korea_growth.solver import solve_dynamic_equilibrium
from korea_growth.types import SolverOptions
from scripts.simulate_policy_shock import (
    aggregate_output_shares,
    build_baseline_inputs,
    collect_region_metrics,
    with_hci_policy,
)


@pytest.fixture(scope="module")
def policy_metrics():
    opts = SolverOptions(max_iter=3000, tol=1e-8, damping=0.25, verbose=False)

    baseline_inputs = build_baseline_inputs()
    policy_inputs = with_hci_policy(baseline_inputs)

    baseline_path = solve_dynamic_equilibrium(inputs=baseline_inputs, options=opts)
    policy_path = solve_dynamic_equilibrium(inputs=policy_inputs, options=opts)

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
