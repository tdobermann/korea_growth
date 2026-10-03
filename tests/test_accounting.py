"""Tests for the accounting corrections implemented from ``docs/model_review.md``.

These cover the theory-consistent fixes in section 1 (Walras / adding-up) and section 2
(theory-code contradictions):

- aggregate income equals aggregate expenditure and the resource constraint holds
  (land rents rebated, fixed costs paid in labor, consistent subsidy accounting,
  infrastructure buying goods, net foreign transfer);
- the migration index is the exact PIGL equivalent income, strictly positive even when
  indirect utility is not, and migration and welfare rank destinations like V does;
- entry, adoption and export are a nested choice (exporters and adopters are active firms);
- sector accounts (employment in workers, value added) add up to population and GDP;
- ``xi`` appears in the domestic mechanized productivity aggregate;
- the PIGL regularity restrictions are enforced.
"""

from __future__ import annotations

import numpy as np
import pytest

from korea_growth.checks import (
    ModelInputError,
    aggregate_accounting,
    validate_inputs,
)
from korea_growth.distributions import integral_phi_sigma_minus_1
from korea_growth.accounting import sector_accounts
from korea_growth.equilibrium import _transfer_scale
from korea_growth.preferences import (
    composite_price,
    equivalent_income,
    expected_utility,
    indirect_utility,
    migration_shares,
)
from korea_growth.solver import initial_guess, solve_dynamic_equilibrium, solve_static_equilibrium
from korea_growth.trade import compute_sector_state, nested_cutoffs
from korea_growth.types import SolverOptions
from dataclasses import replace

from scripts.simulate_policy_shock import build_baseline_inputs
from scripts.solve_toy import build_toy_inputs


class _Eq:
    """Lightweight view of a static equilibrium slice for the accounting helpers."""

    def __init__(self, path, t):
        self.w = path.w[t]
        self.r = path.r[t]
        self.P = path.P[t]
        self.E = path.E[t]
        self.taubar = float(path.taubar[t])
        self.pibar = float(path.pibar[t])


@pytest.fixture(scope="module")
def toy_solution():
    inputs = build_toy_inputs()
    path = solve_dynamic_equilibrium(
        inputs=inputs, options=SolverOptions(max_iter=5000, tol=1e-10, verbose=False)
    )
    return inputs, path


def test_walras_and_resource_constraint_hold(toy_solution):
    inputs, path = toy_solution
    for t in range(inputs.dims.T):
        L_prev = inputs.exog.L0 if t == 0 else path.L[t - 1]
        agg = aggregate_accounting(inputs, t, L_prev, _Eq(path, t))

        # Aggregate income equals aggregate final expenditure (guards land-rent and
        # transfer inclusion; model_review.md 1.1, 1.5).
        assert abs(agg["income_minus_expenditure"]) < 1e-8

        # Resource constraint sum(Y) == sum(E) + EX - IM (CES bookkeeping; 1.5).
        assert abs(agg["resource_residual"]) < 1e-8

        # Government budget balances: tau * W == subsidies + infrastructure (1.3, 1.4).
        assert abs(agg["gov_budget_residual"]) < 1e-8


def test_equilibrium_is_invariant_to_initial_guess():
    # The trade closure must pin domestic prices relative to the foreign numeraire. Under the
    # former closure (transfer = IM - EX at the current guess) scaled guesses converged to
    # different wage levels and trade deficits (docs/fresh_look.md, section 2.1).
    inputs = build_toy_inputs()
    L0 = inputs.exog.L0
    opts = SolverOptions(max_iter=20000, tol=1e-11, verbose=False)
    g0 = initial_guess(inputs=inputs, t=0, L_prev=L0)

    sols = []
    for scale in (0.5, 1.0, 2.0):
        guess = dict(g0, w=g0["w"] * scale, r=g0["r"] * scale, E=g0["E"] * scale)
        sols.append(
            solve_static_equilibrium(inputs=inputs, t=0, L_prev=L0, guess=guess, options=opts)
        )

    for eq in sols[1:]:
        np.testing.assert_allclose(eq.w, sols[0].w, rtol=1e-7)
        np.testing.assert_allclose(eq.P, sols[0].P, rtol=1e-7)
        np.testing.assert_allclose(eq.L, sols[0].L, rtol=1e-7)


def test_net_exports_are_pinned_by_nx_gdp():
    inputs = build_toy_inputs()
    nx = np.full(inputs.dims.T, -0.05)
    inputs = replace(inputs, exog=replace(inputs.exog, nx_gdp=nx))
    path = solve_dynamic_equilibrium(
        inputs=inputs, options=SolverOptions(max_iter=20000, tol=1e-11, verbose=False)
    )
    for t in range(inputs.dims.T):
        L_prev = inputs.exog.L0 if t == 0 else path.L[t - 1]
        agg = aggregate_accounting(inputs, t, L_prev, _Eq(path, t))

        assert agg["NX"] / agg["GDP"] == pytest.approx(-0.05, abs=1e-8)
        assert abs(agg["nx_residual"]) < 1e-8
        assert abs(agg["income_minus_expenditure"]) < 1e-8
        assert abs(agg["resource_residual"]) < 1e-8


def test_population_is_conserved(toy_solution):
    inputs, path = toy_solution
    for t in range(inputs.dims.T):
        assert path.L[t].sum() == pytest.approx(1.0, abs=1e-10)


def test_equivalent_income_positive_when_utility_negative():
    # Log case: indirect utility is negative but the equivalent income is strictly positive.
    alpha = np.array([0.5, 0.5])
    v = np.array([0.02, -0.02])
    P = np.array([2.0, 2.0])
    y_pc = 1.0  # y_pc < composite price => log(y/P) < 0

    util = indirect_utility(y_pc, P, alpha, v, eta=0.0)
    yeq = equivalent_income(y_pc, P, alpha, v, eta=0.0)

    assert util < 0.0
    assert yeq > 0.0


@pytest.mark.parametrize("eta", [0.0, 0.2, 0.6])
def test_equivalent_income_is_money_metric(eta):
    alpha = np.array([0.35, 0.25, 0.40])
    v = np.array([0.03, -0.01, -0.02])
    P = np.array([1.6, 0.9, 1.3])
    P_ref = np.array([1.1, 1.2, 0.8])
    y = 0.7

    yeq = equivalent_income(y, P, alpha, v, eta, P_ref=P_ref)
    # Income yeq at reference prices attains the same utility as y at P ...
    assert indirect_utility(yeq, P_ref, alpha, v, eta) == pytest.approx(
        indirect_utility(y, P, alpha, v, eta), rel=1e-12, abs=1e-12
    )
    # ... and at reference prices equivalent income is income itself.
    assert equivalent_income(y, P_ref, alpha, v, eta, P_ref=P_ref) == pytest.approx(y, rel=1e-12)


def test_migration_and_welfare_agree_with_indirect_utility():
    # Two destinations whose ranking by the old index (y/P) exp(-sum v log P) is the reverse
    # of their ranking by indirect utility V (possible for eta != 0; review_fresh_look 2.3).
    inputs = build_toy_inputs()
    J = inputs.dims.J
    alpha = np.full(J, 1.0 / J)
    v = np.zeros(J)
    v[0], v[1] = 0.3, -0.3
    params = replace(inputs.params, alpha_j=alpha, v_j=v, eta=1.0, nu=3.0, iota=-0.0001)

    P = np.ones((2, J))
    P[1, 0], P[1, 1] = 0.2, 5.0  # destination 1: z = 0.3 log 0.2 - 0.3 log 5 < 0
    y = np.array([3.0, 2.0])

    def old_index(d):
        return y[d] / composite_price(P[d], alpha) * np.exp(-np.sum(v * np.log(P[d])))

    V = [indirect_utility(y[d], P[d], alpha, v, params.eta) for d in range(2)]
    assert V[0] > V[1]
    assert old_index(0) < old_index(1)  # the old index inverts the ranking

    yeq = [equivalent_income(y[d], P[d], alpha, v, params.eta) for d in range(2)]
    assert yeq[0] > yeq[1]

    # Symmetric two-region economy: equal amenities, lagged population, migration costs.
    dims = replace(inputs.dims, regions=["A", "B"])
    exog = replace(
        inputs.exog,
        Vbar=np.ones((inputs.dims.T, 2)),
        delta=np.ones((inputs.dims.T, 2, 2)),
    )
    L_prev = np.array([0.5, 0.5])
    L, _, _ = migration_shares(t=0, dims=dims, params=params, exog=exog, L_prev=L_prev, y_pc=y, P=P)
    assert L[0] > L[1]

    # Welfare is the inclusive value over the same values: its gradient in W_od is mu_od.
    # Raising destination-0 income raises welfare by mu_{o,0} * d log Y^eq_0.
    EU = expected_utility(t=0, dims=dims, params=params, exog=exog, L_prev=L_prev, y_pc=y, P=P)
    h = 1e-6
    y_up = y * np.array([np.exp(h), 1.0])
    EU_up = expected_utility(t=0, dims=dims, params=params, exog=exog, L_prev=L_prev, y_pc=y_up, P=P)
    dlogY = np.log(equivalent_income(y_up[0], P[0], alpha, v, params.eta) / yeq[0])
    mu0 = L[0]  # identical origins => mu_{o,0} = L_0 / sum(L_prev)
    np.testing.assert_allclose((EU_up - EU) / dlogY, mu0, rtol=1e-5)


def test_nested_cutoffs_match_brute_force():
    rng = np.random.default_rng(0)
    sigma = 4.0
    for _ in range(200):
        slopes = np.concatenate([[0.0], np.sort(rng.uniform(0.01, 2.0, 3))])
        rng_slopes = slopes.copy()
        if rng.random() < 0.3:  # option 2 dominated by option 1 (adoption never pays)
            rng_slopes[2] = rng_slopes[1] * rng.uniform(0.5, 1.0)
        costs = np.concatenate([[0.0], np.cumsum(rng.uniform(0.0, 1.0, 3))])
        phis = nested_cutoffs(rng_slopes[:, None], costs[:, None], sigma=sigma)[:, 0]

        grid = np.linspace(1.0, 20.0, 4001)
        x = grid ** (sigma - 1.0)
        choice = np.argmax(rng_slopes[:, None] * x[None, :] - costs[:, None], axis=0)
        assert np.all(np.diff(choice) >= 0)  # envelope index is monotone
        for k in range(1, 4):
            chosen = grid[choice >= k]
            expected = chosen.min() if chosen.size else np.inf
            if np.isfinite(expected):
                assert phis[k] == pytest.approx(expected, abs=grid[1] - grid[0])
            else:
                assert phis[k] > grid[-1] - (grid[1] - grid[0])


def test_exporters_and_adopters_are_active_firms(toy_solution):
    inputs, path = toy_solution
    for inp, pth in ((inputs, path), (build_baseline_inputs(), None)):
        if pth is None:
            pth = solve_dynamic_equilibrium(
                inputs=inp, options=SolverOptions(max_iter=20000, tol=1e-10, damping=0.25, verbose=False)
            )
        for t in range(inp.dims.T):
            L_prev = inp.exog.L0 if t == 0 else pth.L[t - 1]
            for j in range(inp.dims.J):
                st = compute_sector_state(
                    t=t, j=j, dims=inp.dims, params=inp.params, exog=inp.exog, L_prev=L_prev,
                    w=pth.w[t], r=pth.r[t], P=pth.P[t], E=pth.E[t],
                )
                assert np.all(st.num_exporters <= st.num_firms + 1e-12)
                assert np.all(st.num_adopters <= st.num_firms + 1e-12)
                if j == inp.dims.agri_idx:
                    # Agricultural exporters use the mechanised technology, so they adopt.
                    assert np.all(st.num_exporters <= st.num_adopters + 1e-12)
                    assert np.all(st.phi_bar <= st.phi_breve)
                    assert np.all(st.phi_breve <= st.phi_tilde)


def test_sector_accounts_add_up(toy_solution):
    inputs, path = toy_solution
    for t in range(inputs.dims.T):
        L_prev = inputs.exog.L0 if t == 0 else path.L[t - 1]
        eq = _Eq(path, t)
        acc = sector_accounts(inputs, t, L_prev, eq)
        agg = aggregate_accounting(inputs, t, L_prev, eq)
        # Workers (variable + fixed-cost labour) sum to each region's population.
        np.testing.assert_allclose(acc.employment.sum(axis=1), path.L[t], rtol=1e-8)
        # Value added sums to GDP.
        assert acc.value_added.sum() == pytest.approx(agg["GDP"], rel=1e-10)


def test_accounts_add_up_with_labor_unit_fixed_costs():
    # The policy baseline states fixed costs as labour requirements (cost = F * w).
    inputs = build_baseline_inputs()
    assert inputs.params.fixed_costs_in_labor
    L0 = inputs.exog.L0
    eq = solve_static_equilibrium(
        inputs=inputs, t=0, L_prev=L0,
        options=SolverOptions(max_iter=20000, tol=1e-11, damping=0.25, verbose=False),
    )
    agg = aggregate_accounting(inputs, 0, L0, eq)
    acc = sector_accounts(inputs, 0, L0, eq)
    assert abs(agg["income_minus_expenditure"]) < 1e-8
    assert abs(agg["resource_residual"]) < 1e-8
    np.testing.assert_allclose(acc.employment.sum(axis=1), eq.L, rtol=1e-8)
    for j in range(inputs.dims.J):
        st = compute_sector_state(
            t=0, j=j, dims=inputs.dims, params=inputs.params, exog=inputs.exog,
            L_prev=L0, w=eq.w, r=eq.r, P=eq.P, E=eq.E,
        )
        np.testing.assert_allclose(st.F_cost, inputs.exog.F[0, :, j] * eq.w)


def test_infeasible_surplus_target_raises():
    assert _transfer_scale(-0.5, 1.0, 0, 1e-14) == pytest.approx(0.5)
    with pytest.raises(ValueError, match="Infeasible"):
        _transfer_scale(-1.5, 1.0, 0, 1e-14)


def test_export_demand_elasticity_is_separate():
    inputs = build_toy_inputs()
    opts = SolverOptions(max_iter=20000, tol=1e-11, verbose=False)
    base = solve_dynamic_equilibrium(inputs=inputs, options=opts)

    # sigma_x = sigma reproduces the default exactly.
    same = replace(inputs, params=replace(inputs.params, sigma_x=inputs.params.sigma))
    path_same = solve_dynamic_equilibrium(inputs=same, options=opts)
    np.testing.assert_allclose(path_same.w, base.w, rtol=1e-12)

    # A lower aggregate elasticity: D_x = Dtilde (P^X / ptilde)^(sigma - sigma_x) at the
    # solution, and external balance still holds.
    low = replace(inputs, params=replace(inputs.params, sigma_x=1.5))
    path = solve_dynamic_equilibrium(inputs=low, options=opts)
    sigma, sigma_x = low.params.sigma, 1.5
    for t in range(low.dims.T):
        L_prev = low.exog.L0 if t == 0 else path.L[t - 1]
        agg = aggregate_accounting(low, t, L_prev, _Eq(path, t))
        assert abs(agg["nx_residual"]) < 1e-8
        for j in range(low.dims.J):
            st = compute_sector_state(
                t=t, j=j, dims=low.dims, params=low.params, exog=low.exog, L_prev=L_prev,
                w=path.w[t], r=path.r[t], P=path.P[t], E=path.E[t],
            )
            PX = (st.R_tilde.sum() / st.D_export) ** (1.0 / (1.0 - sigma))
            expected = low.exog.Dtilde[t, j] * (PX / low.exog.ptilde[t, j]) ** (sigma - sigma_x)
            assert st.D_export == pytest.approx(expected, rel=1e-9)


def test_xi_enters_domestic_mechanized_aggregate():
    inputs = build_toy_inputs()
    agri_idx = inputs.dims.agri_idx
    assert agri_idx is not None

    L_prev = inputs.exog.L0
    w = np.ones(inputs.dims.N)
    r = np.ones(inputs.dims.N)
    P = np.full((inputs.dims.N, inputs.dims.J), 1.2)
    E = np.full((inputs.dims.N, inputs.dims.J), 0.5)

    st = compute_sector_state(
        t=0, j=agri_idx, dims=inputs.dims, params=inputs.params, exog=inputs.exog,
        L_prev=L_prev, w=w, r=r, P=P, E=E,
    )

    p = inputs.params
    f_o = np.power(L_prev, float(p.rho_j[agri_idx]))
    A_o = inputs.exog.A[0, :, agri_idx]
    I_breve = integral_phi_sigma_minus_1(
        st.phi_breve, p.kappa, sigma=p.sigma, theta=p.theta, kappa=p.kappa
    )
    expected = A_o * f_o * p.xi * np.power(I_breve, 1.0 / (p.sigma - 1.0))

    np.testing.assert_allclose(st.Zbreve, expected, rtol=1e-12)


def test_pigl_restrictions_are_enforced():
    inputs = build_toy_inputs()

    bad_eta = replace(inputs, params=replace(inputs.params, eta=-0.2))
    with pytest.raises(ModelInputError, match="eta"):
        validate_inputs(bad_eta)

    # Flip the agriculture taste shifter negative (keep sum-to-zero).
    v_bad = inputs.params.v_j.copy()
    v_bad[inputs.dims.agri_idx] = -abs(v_bad[inputs.dims.agri_idx])
    v_bad[-1] = -v_bad[:-1].sum()
    bad_v = replace(inputs, params=replace(inputs.params, v_j=v_bad))
    with pytest.raises(ModelInputError, match="agriculture"):
        validate_inputs(bad_v)
