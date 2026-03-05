r"""Productivity distribution primitives.

The model assumes a bounded Pareto distribution on the exogenous component
phi \in [1, kappa] with shape theta.

We expose vectorized CDF/PDF and the key CES-relevant integral:

    \int_a^b phi^{sigma-1} g(phi) dphi

where g(phi) is the Pareto PDF.
"""

from __future__ import annotations

import numpy as np


def pareto_cdf(phi: np.ndarray, theta: float, kappa: float) -> np.ndarray:
    """Bounded Pareto CDF G(phi). Vectorized."""
    phi = np.asarray(phi)
    out = np.zeros_like(phi, dtype=float)
    out = np.where(phi <= 1.0, 0.0, out)
    out = np.where(phi >= kappa, 1.0, out)
    mask = (phi > 1.0) & (phi < kappa)
    if np.any(mask):
        out = np.where(mask, (1.0 - phi ** (-theta)) / (1.0 - kappa ** (-theta)), out)
    return out


def pareto_survival(phi: np.ndarray, theta: float, kappa: float) -> np.ndarray:
    """Survival function 1 - G(phi). Vectorized."""
    return 1.0 - pareto_cdf(phi, theta, kappa)


def pareto_pdf(phi: np.ndarray, theta: float, kappa: float) -> np.ndarray:
    """Bounded Pareto PDF g(phi). Vectorized."""
    phi = np.asarray(phi)
    out = np.zeros_like(phi, dtype=float)
    mask = (phi >= 1.0) & (phi <= kappa)
    if np.any(mask):
        out = np.where(mask, theta * phi ** (-theta - 1.0) / (1.0 - kappa ** (-theta)), out)
    return out


def integral_phi_sigma_minus_1(
    a: np.ndarray,
    b: np.ndarray,
    sigma: float,
    theta: float,
    kappa: float,
) -> np.ndarray:
    r"""Compute \int_a^b phi^{sigma-1} g(phi) dphi for the bounded Pareto.

    Parameters
    ----------
    a, b:
        Lower and upper integration limits. Vectorized; must be broadcastable.
    sigma:
        Elasticity of substitution.
    theta, kappa:
        Pareto parameters.

    Returns
    -------
    ndarray
        The integral value(s).

    Notes
    -----
    For the bounded Pareto with PDF g(phi)=theta*phi^{-theta-1}/(1-kappa^{-theta}),

        phi^{sigma-1} g(phi) = theta/(1-kappa^{-theta}) * phi^{sigma-theta-2}.

    If sigma-theta-1 != 0, the primitive is proportional to phi^{sigma-theta-1}.
    If sigma-theta-1 == 0, the primitive is proportional to log(phi).
    """

    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)

    # Clamp to support; anything outside contributes 0 in this model.
    a_c = np.clip(a, 1.0, kappa)
    b_c = np.clip(b, 1.0, kappa)

    # If b<=a the integral is zero.
    valid = b_c > a_c

    out = np.zeros(np.broadcast(a_c, b_c).shape, dtype=float)

    expo = sigma - theta - 1.0
    pref = theta / (1.0 - kappa ** (-theta))

    if abs(expo) < 1e-14:
        # log case
        val = pref * np.log(b_c / a_c)
    else:
        val = pref * (b_c ** expo - a_c ** expo) / expo

    out = np.where(valid, val, 0.0)
    return out
