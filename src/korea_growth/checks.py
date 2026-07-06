"""Input validation and parameter restrictions.

The original prototype (`baseline.py`) relied on a global `check_param_restrictions()`
function. Here we expose it as a reusable validator.
"""

from __future__ import annotations

import numpy as np

from .types import ModelInputs


class ModelInputError(ValueError):
    """Raised when model inputs fail shape or parameter restriction checks."""


def validate_shapes(inputs: ModelInputs) -> None:
    """Validate that array shapes match the declared dimensions."""

    dims = inputs.dims
    ex = inputs.exog

    def assert_shape(name: str, arr: np.ndarray, shape: tuple[int, ...]) -> None:
        if tuple(arr.shape) != tuple(shape):
            raise ModelInputError(f"{name}.shape expected {shape} but got {arr.shape}")

    T, N, J = dims.T, dims.N, dims.J

    assert_shape("L0", ex.L0, (N,))
    assert_shape("M", ex.M, (T, J))
    assert_shape("Vbar", ex.Vbar, (T, N))

    assert_shape("A", ex.A, (T, N, J))
    assert_shape("beta", ex.beta, (T, N, J))
    assert_shape("gamma", ex.gamma, (T, N, J))
    assert_shape("gamma_io", ex.gamma_io, (T, N, J, J))

    assert_shape("betabreve", ex.betabreve, (T, N, J))
    assert_shape("gammabreve", ex.gammabreve, (T, N, J))
    assert_shape("gammabreve_io", ex.gammabreve_io, (T, N, J, J))

    assert_shape("F", ex.F, (T, N, J))
    assert_shape("Fbreve", ex.Fbreve, (T, N, J))
    assert_shape("Ftilde", ex.Ftilde, (T, N, J))

    assert_shape("s", ex.s, (T, N, J))

    assert_shape("tau", ex.tau, (T, J, N, N))
    assert_shape("tautilde", ex.tautilde, (T, J, N))
    assert_shape("Dtilde", ex.Dtilde, (T, J))
    assert_shape("ptilde", ex.ptilde, (T, J))

    assert_shape("delta", ex.delta, (T, N, N))
    assert_shape("H", ex.H, (T, N))
    assert_shape("tax_spending_on_building_H_and_roads", ex.tax_spending_on_building_H_and_roads, (T,))


def validate_param_restrictions(inputs: ModelInputs, tol: float = 1e-10) -> None:
    """Validate the key parameter restrictions assumed by the theory.

    This is a cleaned-up version of the checks in `baseline.py`.

    Raises
    ------
    ModelInputError
        If any restriction is violated.
    """

    dims = inputs.dims
    p = inputs.params
    ex = inputs.exog

    T, N, J = dims.T, dims.N, dims.J

    errors: list[str] = []

    # Population normalization (optional, but the prototype assumes it)
    if not np.isclose(ex.L0.sum(), 1.0, atol=tol):
        errors.append("L0 must sum to 1 (population normalization)")

    if not (p.sigma > 1):
        errors.append("sigma must be > 1")
    if not (p.kappa > 1):
        errors.append("kappa must be > 1")
    if not (p.xi > 1):
        errors.append("xi must be > 1")

    if not (np.min(p.rho_j) > 0 and np.max(p.rho_j) < 1):
        errors.append("rho_j must be in (0,1)")

    if not (-1 < p.iota < 0):
        errors.append("iota must be in (-1,0)")

    if not np.isclose(p.alpha_j.sum(), 1.0, atol=tol):
        errors.append("alpha_j must sum to 1")

    if not np.isclose(p.v_j.sum(), 0.0, atol=tol):
        errors.append("v_j must sum to 0")

    # PIGL regularity / sign conventions (model_review.md 7.3, model.tex): eta > 0 and a
    # positive agriculture taste shifter deliver Engel's law and keep the expenditure shares
    # well-behaved. (The share bounds themselves are income-dependent and are checked at the
    # solved equilibrium, not here.)
    if not (p.eta > 0):
        errors.append("eta must be > 0 (PIGL regularity)")
    agri_idx = dims.agri_idx
    if agri_idx is not None and not (p.v_j[agri_idx] > 0):
        errors.append("v_j for agriculture must be > 0 (Engel's law)")

    if not (np.min(ex.beta) > 0 and np.max(ex.beta) < 1):
        errors.append("beta must be in (0,1)")

    # Production shares sum-to-one
    if not np.allclose(ex.gamma + ex.gamma_io.sum(axis=-1), 1.0, atol=tol):
        errors.append("gamma + sum_k gamma_io must equal 1 for every (t,o,j)")

    if not (np.min(ex.gamma) > 0 and np.max(ex.gamma) < 1):
        errors.append("gamma must be in (0,1)")

    if not (np.min(ex.gamma_io) >= 0 and np.max(ex.gamma_io) < 1):
        errors.append("gamma_io must be in [0,1)")

    # New-tech shares sum-to-one
    if not np.allclose(ex.gammabreve + ex.gammabreve_io.sum(axis=-1), 1.0, atol=tol):
        errors.append("gammabreve + sum_k gammabreve_io must equal 1 for every (t,o,j)")

    # Relationship gammabreve*betabreve == gamma*beta (keeps land share in value added consistent)
    if not np.allclose(ex.gammabreve * ex.betabreve, ex.gamma * ex.beta, atol=tol):
        errors.append("gammabreve*betabreve must equal gamma*beta (for every t,o,j)")

    # The original code assumes the adoption changes only the heavy-manufacturing input share.
    heavy_idx = dims.heavy_idx
    if heavy_idx is not None:
        mask_k = np.ones(J, dtype=bool)
        mask_k[heavy_idx] = False
        if not np.allclose(ex.gammabreve_io[..., mask_k], ex.gamma_io[..., mask_k], atol=tol):
            errors.append("For k != HeavyMnf, gammabreve_io must equal gamma_io")

    if not (np.min(ex.s) >= 0 and np.max(ex.s) < 1):
        errors.append("s must be in [0,1)")

    if errors:
        raise ModelInputError("; ".join(errors))


def validate_inputs(inputs: ModelInputs) -> None:
    """Run all validation checks."""
    validate_shapes(inputs)
    validate_param_restrictions(inputs)


def aggregate_accounting(inputs: ModelInputs, t: int, L_prev: np.ndarray, eq) -> dict:
    """Return the aggregate accounting diagnostics at a solved equilibrium.

    Re-evaluates the equilibrium map at ``eq`` (which is a fixed point, so the implied
    values equal ``eq``) and returns the ``aggregates`` dictionary, which contains the
    resource-constraint residual, income-vs-expenditure residual, government-budget
    residual, exports, imports, and the net foreign transfer (model_review.md 1).
    """
    from .equilibrium import compute_implied_static

    implied = compute_implied_static(
        inputs=inputs,
        t=t,
        L_prev=L_prev,
        w=eq.w,
        r=eq.r,
        P=eq.P,
        E=eq.E,
        taubar=eq.taubar,
        pibar=eq.pibar,
    )
    return implied.aggregates


def cutoff_ordering_violation(inputs: ModelInputs, t: int, L_prev: np.ndarray, eq) -> float:
    """Max violation of the agricultural cutoff ordering phibar <= phibreve <= phitilde.

    Returns 0.0 when the ordering holds (or when there is no agriculture sector). Only
    finite cutoffs are compared (phibreve is +inf where mechanized adoption is never
    profitable). See model_review.md 2.2 and model.tex.
    """
    from .trade import compute_sector_state

    agri_idx = inputs.dims.agri_idx
    if agri_idx is None:
        return 0.0

    st = compute_sector_state(
        t=t,
        j=agri_idx,
        dims=inputs.dims,
        params=inputs.params,
        exog=inputs.exog,
        L_prev=L_prev,
        w=eq.w,
        r=eq.r,
        P=eq.P,
        E=eq.E,
    )

    phi_bar = np.asarray(st.phi_bar, dtype=float)
    phi_breve = np.asarray(st.phi_breve, dtype=float)
    phi_tilde = np.asarray(st.phi_tilde, dtype=float)

    finite = np.isfinite(phi_breve)
    v1 = phi_bar[finite] - phi_breve[finite]  # want <= 0
    v2 = phi_breve[finite] - phi_tilde[finite]  # want <= 0
    worst = 0.0
    for arr in (v1, v2):
        if arr.size:
            worst = max(worst, float(np.max(arr)))
    return max(0.0, worst)
