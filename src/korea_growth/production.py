"""Production-side primitives.

This module contains:

- Agglomeration term f_j(L_{t-1})
- Unit cost of the sector-j input bundle c_{o,j}

The scalar formulas match those used in `baseline.py`, but are implemented
in a vectorized, reusable way.
"""

from __future__ import annotations

import numpy as np


def agglomeration(L_prev: np.ndarray, rho_j: float) -> np.ndarray:
    """Agglomeration term f_j(L_{o,t-1}) = L_{o,t-1}^{rho_j}."""
    return np.power(L_prev, rho_j)


def unit_cost_bundle(
    *,
    r: np.ndarray,
    w: np.ndarray,
    P: np.ndarray,
    beta: np.ndarray,
    gamma: np.ndarray,
    gamma_io: np.ndarray,
) -> np.ndarray:
    """Compute unit cost c_{o,j} for all regions o, for one sector j.

    Parameters
    ----------
    r, w:
        Factor prices (N,).
    P:
        Local sectoral price indices (N, J).
    beta, gamma:
        Scalars per region (N,) for this sector.
    gamma_io:
        Input shares per region (N, J) for this sector.

    Returns
    -------
    c : ndarray (N,)
        Unit costs.

    Notes
    -----
    This implements the `baseline.py` formula:

        c_{o,j} = ((1/gamma_{o,j})*(r_o/beta_{o,j})^{beta_{o,j}}
                   *(w_o/(1-beta_{o,j}))^{1-beta_{o,j}})^{gamma_{o,j}}
                 * \prod_k (P_{o,k}/gamma_{o,jk})^{gamma_{o,jk}}

    where gamma_{o,jk} denotes the material input share on input k.
    """

    r = np.asarray(r, dtype=float)
    w = np.asarray(w, dtype=float)
    P = np.asarray(P, dtype=float)
    beta = np.asarray(beta, dtype=float)
    gamma = np.asarray(gamma, dtype=float)
    gamma_io = np.asarray(gamma_io, dtype=float)

    # Material-input cost term: prod_k (P_{o,k} / gamma_{o,jk})^{gamma_{o,jk}}
    # We compute in logs for stability.
    with np.errstate(divide="raise", invalid="raise"):
        log_material = np.sum(gamma_io * (np.log(P) - np.log(gamma_io)), axis=1)

    # Value-added (r,w) term
    va_inner = (1.0 / gamma) * np.power(r / beta, beta) * np.power(w / (1.0 - beta), 1.0 - beta)
    log_va = gamma * np.log(va_inner)

    log_c = log_va + log_material
    return np.exp(log_c)
