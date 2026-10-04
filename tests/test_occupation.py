"""Tests for occupation choice and sector-specific wages (model.tex, sec. occupation).

Each test checks a property the theory states:
- the integrated labour market is the eps_occ -> infinity limit;
- every (location, sector) labour market clears at its own wage, and the accounting
  identities still hold;
- occupation shares follow the nested-logit formula at the solved incomes;
- the within-location wage gap decomposes into a supply term and the non-pecuniary wedge;
- a higher farm wedge lowers the relative farm wage and raises farm employment;
- welfare responds to sector income with weight mu_{o,d} pi_{k|d};
- the solution does not depend on the initial guess;
- sectors mapped to one occupation share its wage (one occupation = integrated market).
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from korea_growth.accounting import sector_accounts
from korea_growth.checks import ModelInputError, aggregate_accounting, validate_inputs
from korea_growth.preferences import expected_utility, log_equivalent_income_matrix, occupation_choice
from korea_growth.solver import initial_guess, solve_dynamic_equilibrium, solve_static_equilibrium
from korea_growth.types import SolverOptions
from scripts.solve_toy import build_toy_inputs

OPTS = SolverOptions(max_iter=20000, tol=1e-11, verbose=False)


def segmented(eps_occ: float, b_agri: float = 1.0):
    inputs = build_toy_inputs()
    b = np.ones((inputs.dims.T, inputs.dims.N, inputs.dims.J))
    b[..., inputs.dims.agri_idx] = b_agri
    return replace(
        inputs,
        params=replace(inputs.params, eps_occ=eps_occ),
        exog=replace(inputs.exog, b_occ=b),
    )


@pytest.fixture(scope="module")
def solved():
    inputs = segmented(5.0, b_agri=1.3)
    return inputs, solve_dynamic_equilibrium(inputs=inputs, options=OPTS)


def test_integrated_market_is_the_large_eps_limit():
    integrated = build_toy_inputs()
    base = solve_dynamic_equilibrium(inputs=integrated, options=OPTS)
    limit = solve_dynamic_equilibrium(inputs=segmented(1e7), options=OPTS)
    np.testing.assert_allclose(limit.w, base.w, rtol=1e-6)
    np.testing.assert_allclose(limit.L, base.L, rtol=1e-6)
    # Wages equalise across sectors within each location.
    np.testing.assert_allclose(limit.w_sector, limit.w[..., None] * np.ones_like(limit.w_sector), rtol=1e-6)


def test_sector_labour_markets_clear_and_accounts_add_up(solved):
    inputs, path = solved
    for t in range(inputs.dims.T):
        L_prev = inputs.exog.L0 if t == 0 else path.L[t - 1]
        eq = path.at(t)
        agg = aggregate_accounting(inputs, t, L_prev, eq)
        acc = sector_accounts(inputs, t, L_prev, eq)
        assert abs(agg["income_minus_expenditure"]) < 1e-9
        assert abs(agg["resource_residual"]) < 1e-9
        assert abs(agg["gov_budget_residual"]) < 1e-9
        # Labour demanded (payments / own-sector wage) equals labour supplied (pi L).
        np.testing.assert_allclose(acc.employment, path.L_sector[t], rtol=1e-8)
        np.testing.assert_allclose(path.L_sector[t].sum(axis=1), path.L[t], rtol=1e-12)


def test_occupation_shares_follow_nested_logit(solved):
    inputs, path = solved
    p, ex = inputs.params, inputs.exog
    for t in range(inputs.dims.T):
        pi, log_phi, log_Y = occupation_choice(t=t, dims=inputs.dims, params=p, exog=ex, y=path.y_sector[t], P=path.P[t])
        np.testing.assert_allclose(path.L_sector[t] / path.L[t][:, None], pi, rtol=1e-8)
        u = np.log(ex.b_occ[t]) + log_Y
        np.testing.assert_allclose(pi, np.exp(p.eps_occ * u) / np.exp(p.eps_occ * u).sum(1, keepdims=True))
        np.testing.assert_allclose(log_phi, np.log(np.exp(p.eps_occ * u).sum(1)) / p.eps_occ)


def test_wage_gap_decomposition(solved):
    # log(pi_A / pi_N) = eps [log(b_A / b_N) + log(Y_A / Y_N)]: the equivalent-income gap is
    # a supply term (1/eps) log(L_A / L_N) minus the non-pecuniary wedge.
    inputs, path = solved
    a = inputs.dims.agri_idx
    n = 1 - a
    t = 0
    log_Y = log_equivalent_income_matrix(
        path.y_sector[t], path.P[t], inputs.params.alpha_j, inputs.params.v_j, inputs.params.eta
    )
    b = inputs.exog.b_occ[t]
    lhs = log_Y[:, a] - log_Y[:, n]
    rhs = np.log(path.L_sector[t][:, a] / path.L_sector[t][:, n]) / inputs.params.eps_occ - np.log(b[:, a] / b[:, n])
    np.testing.assert_allclose(lhs, rhs, atol=1e-9)


def test_farm_wedge_lowers_relative_farm_wage_and_raises_farm_employment():
    a = build_toy_inputs().dims.agri_idx
    low = solve_static_equilibrium(inputs=segmented(5.0, 1.0), t=0, L_prev=build_toy_inputs().exog.L0, options=OPTS)
    high = solve_static_equilibrium(inputs=segmented(5.0, 1.5), t=0, L_prev=build_toy_inputs().exog.L0, options=OPTS)

    def gap(eq):
        return eq.w_sector[:, a] / eq.w_sector[:, 1 - a]

    assert np.all(gap(high) < gap(low))
    assert high.L_sector[:, a].sum() > low.L_sector[:, a].sum()


def test_welfare_gradient_is_mu_times_pi(solved):
    inputs, path = solved
    t, d, k = 0, 1, inputs.dims.agri_idx
    L_prev = inputs.exog.L0
    y = path.y_sector[t].copy()
    kw = dict(t=t, dims=inputs.dims, params=inputs.params, exog=inputs.exog, L_prev=L_prev, P=path.P[t])
    EU = expected_utility(y_pc=y, **kw)
    h = 1e-6
    y_up = y.copy()
    y_up[d, k] *= np.exp(h)
    EU_up = expected_utility(y_pc=y_up, **kw)
    p = inputs.params
    dlogY = (
        log_equivalent_income_matrix(y_up, path.P[t], p.alpha_j, p.v_j, p.eta)
        - log_equivalent_income_matrix(y, path.P[t], p.alpha_j, p.v_j, p.eta)
    )[d, k]
    # mu_{o,d}: destination shares by origin, recovered from the migration values.
    from korea_growth.preferences import migration_values

    W, _ = migration_values(y_pc=y, **kw)
    mu = np.exp(p.nu * W) / np.exp(p.nu * W).sum(axis=1, keepdims=True)
    pi, _, _ = occupation_choice(t=t, dims=inputs.dims, params=p, exog=inputs.exog, y=y, P=path.P[t])
    np.testing.assert_allclose((EU_up - EU) / dlogY, mu[:, d] * pi[d, k], rtol=1e-5)


def test_segmented_equilibrium_is_invariant_to_initial_guess():
    inputs = segmented(5.0, 1.3)
    L0 = inputs.exog.L0
    g0 = initial_guess(inputs=inputs, t=0, L_prev=L0)
    sols = []
    for scale in (0.5, 1.0, 2.0):
        guess = dict(g0, w=g0["w"] * scale, r=g0["r"] * scale, E=g0["E"] * scale)
        sols.append(solve_static_equilibrium(inputs=inputs, t=0, L_prev=L0, guess=guess, options=OPTS))
    for eq in sols[1:]:
        np.testing.assert_allclose(eq.w_sector, sols[0].w_sector, rtol=1e-7)
        np.testing.assert_allclose(eq.L_sector, sols[0].L_sector, rtol=1e-7)


def test_nested_logit_restriction_is_enforced():
    inputs = build_toy_inputs()
    bad = replace(inputs, params=replace(inputs.params, eps_occ=0.5 * inputs.params.nu))
    with pytest.raises(ModelInputError, match="eps_occ"):
        validate_inputs(bad)


def test_single_occupation_is_the_integrated_market():
    integrated = build_toy_inputs()
    one_occ = replace(
        integrated,
        dims=replace(integrated.dims, occupation_of_sector=(0, 0)),
        params=replace(integrated.params, eps_occ=5.0),
    )
    a = solve_dynamic_equilibrium(inputs=integrated, options=OPTS)
    b = solve_dynamic_equilibrium(inputs=one_occ, options=OPTS)
    np.testing.assert_allclose(b.w_sector, a.w_sector, rtol=1e-9)
    np.testing.assert_allclose(b.L, a.L, rtol=1e-9)


def test_sectors_of_one_occupation_share_its_wage():
    from scripts.korea_baseline import build_baseline_inputs

    inputs = build_baseline_inputs()
    dims = replace(inputs.dims, occupation_of_sector=(0, 0, 1, 2))  # farming, mnf, services
    inputs = replace(inputs, dims=dims, params=replace(inputs.params, eps_occ=8.0))
    eq = solve_static_equilibrium(
        inputs=inputs, t=0, L_prev=inputs.exog.L0,
        options=SolverOptions(max_iter=20000, tol=1e-10, damping=0.25, verbose=False),
    )
    farm = list(dims.farm_idx)
    np.testing.assert_allclose(eq.w_sector[:, farm[0]], eq.w_sector[:, farm[1]], rtol=1e-12)
    pi, _, _ = occupation_choice(
        t=0, dims=dims, params=inputs.params, exog=inputs.exog, y=eq.y_sector, P=eq.P
    )
    np.testing.assert_allclose(eq.L_sector[:, farm].sum(axis=1), pi[:, 0] * eq.L, rtol=1e-7)
