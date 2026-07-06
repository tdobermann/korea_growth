"""Tests for the accounting corrections implemented from ``docs/model_review.md``.

These cover the theory-consistent fixes in section 1 (Walras / adding-up) and section 2
(theory-code contradictions):

- aggregate income equals aggregate expenditure and the resource constraint holds
  (land rents rebated, fixed costs paid in labor, consistent subsidy accounting,
  infrastructure buying goods, net foreign transfer);
- the migration real-income index is strictly positive even when indirect utility is not;
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
from korea_growth.preferences import indirect_utility, real_income_index
from korea_growth.solver import solve_dynamic_equilibrium
from korea_growth.trade import compute_sector_state
from korea_growth.types import SolverOptions
from dataclasses import replace

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


def test_population_is_conserved(toy_solution):
    inputs, path = toy_solution
    for t in range(inputs.dims.T):
        assert path.L[t].sum() == pytest.approx(1.0, abs=1e-10)


def test_real_income_index_positive_when_utility_negative():
    # Choose prices/income so that the log-case indirect utility is negative but the
    # money-metric real-income index is still strictly positive.
    alpha = np.array([0.5, 0.5])
    v = np.array([0.02, -0.02])
    P = np.array([2.0, 2.0])
    y_pc = 1.0  # y_pc < composite price => log(y/P) < 0

    util = indirect_utility(y_pc, P, alpha, v, eta=0.0)
    yreal = real_income_index(y_pc, P, alpha, v)

    assert util < 0.0
    assert yreal > 0.0


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
