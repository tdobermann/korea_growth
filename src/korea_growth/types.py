"""Core dataclasses and typing helpers.

The original `baseline.py` used many global variables and long argument lists.
This module centralizes model inputs/outputs and provides shape validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np

Array = np.ndarray


@dataclass(frozen=True)
class ModelDimensions:
    """Discrete dimensions and labels.

    Parameters
    ----------
    times:
        Length-T sequence of time labels.
    regions:
        Length-N sequence of region labels.
    sectors:
        Length-J sequence of sector labels.
    agri_sector:
        Name of the agriculture sector used to activate machinery-adoption blocks.
    heavy_mnf_sector:
        Name of the heavy-manufacturing sector (used in parameter restrictions in the original code).
    """

    times: Sequence[int]
    regions: Sequence[str]
    sectors: Sequence[str]
    agri_sector: str = "Agri"
    heavy_mnf_sector: str = "HeavyMnf"
    services_sector: str = "Services"

    @property
    def T(self) -> int:
        return len(self.times)

    @property
    def N(self) -> int:
        return len(self.regions)

    @property
    def J(self) -> int:
        return len(self.sectors)

    @property
    def agri_idx(self) -> Optional[int]:
        return self.sectors.index(self.agri_sector) if self.agri_sector in self.sectors else None

    @property
    def heavy_idx(self) -> Optional[int]:
        return self.sectors.index(self.heavy_mnf_sector) if self.heavy_mnf_sector in self.sectors else None

    @property
    def services_idx(self) -> Optional[int]:
        return self.sectors.index(self.services_sector) if self.services_sector in self.sectors else None


@dataclass(frozen=True)
class ModelParameters:
    """Scalar and low-dimensional parameters."""

    sigma: float
    theta: float
    kappa: float
    xi: float

    rho_j: Array  # (J,)
    iota: float

    eta: float
    nu: float

    alpha_j: Array  # (J,)
    v_j: Array  # (J,)


@dataclass(frozen=True)
class ModelExogenousPaths:
    """Exogenous fundamentals and policy paths.

    All arrays must be NumPy ndarrays with the documented shapes.
    """

    # Initial population distribution (must sum to 1 if you want normalized population)
    L0: Array  # (N,)

    # Mass of potential firms by sector
    M: Array  # (T, J)

    # Household amenities
    Vbar: Array  # (T, N)

    # Production technology
    A: Array  # (T, N, J)
    beta: Array  # (T, N, J)
    gamma: Array  # (T, N, J)
    gamma_io: Array  # (T, N, J, J)  # gamma_io[t,o,j,k] = share of input k in sector j

    # Technology adoption (used for agriculture)
    betabreve: Array  # (T, N, J)
    gammabreve: Array  # (T, N, J)
    gammabreve_io: Array  # (T, N, J, J)

    # Fixed costs
    F: Array  # (T, N, J)
    Fbreve: Array  # (T, N, J)
    Ftilde: Array  # (T, N, J)

    # Industrial policy subsidy (input cost subsidy)
    s: Array  # (T, N, J)

    # Trade
    tau: Array  # (T, J, N, N)  # iceberg within-country
    tautilde: Array  # (T, J, N)  # iceberg to foreign
    Dtilde: Array  # (T, J)  # foreign demand shifter
    ptilde: Array  # (T, J)  # foreign price

    # Migration costs
    delta: Array  # (T, N, N)

    # Land/structures supply
    H: Array  # (T, N)

    # Exogenous government spending (in wage units / numeraire)
    tax_spending_on_building_H_and_roads: Array  # (T,)


@dataclass(frozen=True)
class ModelInputs:
    """Full set of inputs to solve the model."""

    dims: ModelDimensions
    params: ModelParameters
    exog: ModelExogenousPaths


@dataclass(frozen=True)
class SolverOptions:
    """Numerical options for the fixed-point solver."""

    max_iter: int = 5_000
    tol: float = 1e-10
    damping: float = 0.2
    min_damping: float = 1e-4
    verbose: bool = True

    # Safety floors to avoid log/zero issues
    eps: float = 1e-14


@dataclass(frozen=True)
class StaticEquilibrium:
    """Static equilibrium objects for a single time period."""

    t: int
    w: Array  # (N,)
    r: Array  # (N,)
    P: Array  # (N, J)
    E: Array  # (N, J)
    L: Array  # (N,)
    y_pc: Array  # (N,)
    taubar: float
    pibar: float

    # Diagnostics
    max_residual: float
    iters: int


@dataclass(frozen=True)
class DynamicEquilibriumPath:
    """Dynamic equilibrium path (sequence of static equilibria)."""

    w: Array  # (T, N)
    r: Array  # (T, N)
    P: Array  # (T, N, J)
    E: Array  # (T, N, J)
    L: Array  # (T, N)
    y_pc: Array  # (T, N)
    taubar: Array  # (T,)
    pibar: Array  # (T,)

    # Solver diagnostics
    iters: Array  # (T,)
    max_residual: Array  # (T,)


