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
    # Sectors counted as agriculture in reporting (employment, value added). Default: the
    # agri_sector alone.
    farm_sectors: Sequence[str] = ()
    # Occupation of each sector (J,) as integers 0..O-1: sectors in the same occupation share
    # one wage within a location (e.g. rice and other crops are both farming). Default: each
    # sector is its own occupation. Used only with params.eps_occ.
    occupation_of_sector: Sequence[int] = ()

    @property
    def occ_idx(self) -> np.ndarray:
        if self.occupation_of_sector:
            return np.asarray(self.occupation_of_sector, dtype=int)
        return np.arange(len(self.sectors))

    @property
    def O(self) -> int:
        return int(self.occ_idx.max()) + 1

    @property
    def farm_idx(self) -> list[int]:
        names = self.farm_sectors or ((self.agri_sector,) if self.agri_sector in self.sectors else ())
        return [self.sectors.index(name) for name in names]

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

    # Aggregate elasticity of foreign demand for Korean exports (between the Korean export
    # bundle and foreign goods). External balance pins the wage level through this
    # elasticity, so it should be calibrated externally rather than tied to the domestic
    # substitution elasticity sigma. None = sigma.
    sigma_x: Optional[float] = None

    # Units of the fixed costs F, Fbreve, Ftilde. False: numeraire units. True: local labour
    # requirements, so the cost is F * w_o. Fixed costs are paid in local labour, so labour
    # units keep entry, exporting and mechanisation from getting mechanically cheaper in real
    # terms as wages grow (docs/fresh_look.md 2.5).
    fixed_costs_in_labor: bool = False

    # Occupation choice (model.tex, "Occupation choice and sector-specific wages"). Within a
    # location, workers choose a sector with i.i.d. Gumbel taste shocks of scale 1/eps_occ,
    # nested inside the location choice (nested logit; requires eps_occ >= nu). Each
    # location-sector then has its own wage. None = integrated local labour market: one wage
    # per location (the eps_occ -> infinity limit with unit wedges).
    eps_occ: Optional[float] = None


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

    # Exogenous net exports (EX - IM) as a share of GDP. This pins the trade balance, and with
    # it the level of domestic prices relative to the foreign numeraire. None = balanced trade.
    nx_gdp: Optional[Array] = None  # (T,)

    # Sectors that are not traded with the rest of the world (J,) bool: no imports (the
    # foreign variety drops out of the price index) and no exports. Interregional trade is
    # unaffected. None = every sector traded.
    nontraded: Optional[Array] = None  # (J,)

    # Non-pecuniary occupation wedges b_{d,o,t} > 0 (T, N, O): the value of working in
    # occupation o in location d relative to its pay (attachment to farming, entry barriers,
    # disamenity). Used only when params.eps_occ is set. None = all ones.
    b_occ: Optional[Array] = None  # (T, N, O)

    def is_nontraded(self, j: int) -> bool:
        return self.nontraded is not None and bool(self.nontraded[j])


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
    w: Array  # (N,) employment-weighted average wage
    r: Array  # (N,)
    P: Array  # (N, J)
    E: Array  # (N, J)
    L: Array  # (N,)
    y_pc: Array  # (N,) average per-capita income
    taubar: float
    pibar: float

    # Diagnostics
    max_residual: float
    iters: int

    # Sector-specific labour market: wages, employment and per-worker income by (location,
    # sector). With an integrated labour market every column of w_sector equals w.
    w_sector: Optional[Array] = None  # (N, J)
    L_sector: Optional[Array] = None  # (N, J)
    y_sector: Optional[Array] = None  # (N, J)


@dataclass(frozen=True)
class DynamicEquilibriumPath:
    """Dynamic equilibrium path (sequence of static equilibria)."""

    w: Array  # (T, N) employment-weighted average wage
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

    # Sector-specific labour market (see StaticEquilibrium)
    w_sector: Optional[Array] = None  # (T, N, J)
    L_sector: Optional[Array] = None  # (T, N, J)
    y_sector: Optional[Array] = None  # (T, N, J)

    def at(self, t: int) -> StaticEquilibrium:
        """The static equilibrium of period t."""
        sec = (lambda a: None if a is None else a[t])
        return StaticEquilibrium(
            t=t, w=self.w[t], r=self.r[t], P=self.P[t], E=self.E[t], L=self.L[t],
            y_pc=self.y_pc[t], taubar=float(self.taubar[t]), pibar=float(self.pibar[t]),
            max_residual=float(self.max_residual[t]), iters=int(self.iters[t]),
            w_sector=sec(self.w_sector), L_sector=sec(self.L_sector), y_sector=sec(self.y_sector),
        )


def sector_wages(eq) -> Array:
    """Wages by (location, sector) of an equilibrium-like object: ``w_sector`` when present,
    else ``w`` (one wage per location, or already (N, J))."""
    w_sector = getattr(eq, "w_sector", None)
    return np.asarray(eq.w if w_sector is None else w_sector, dtype=float)


def sector_incomes(eq) -> Array:
    """Per-worker income by (location, sector) when present, else per-capita income (N,)."""
    y_sector = getattr(eq, "y_sector", None)
    return np.asarray(eq.y_pc if y_sector is None else y_sector, dtype=float)


