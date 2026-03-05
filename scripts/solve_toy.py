"""Toy example run.

This script builds a *small synthetic* instance of the model (N=3 regions, J=2 sectors, T=2)
and runs the dynamic equilibrium solver.

It is meant as a smoke test and a template for wiring in real data.

Run:
    PYTHONPATH=src python scripts/solve_toy.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from korea_growth.checks import validate_inputs
from korea_growth.solver import solve_dynamic_equilibrium
from korea_growth.types import (
    ModelDimensions,
    ModelExogenousPaths,
    ModelInputs,
    ModelParameters,
    SolverOptions,
)


def build_toy_inputs() -> ModelInputs:
    times = [0, 1]
    regions = ["Seoul", "Busan", "Daegu"]
    sectors = ["Agri", "HeavyMnf"]

    dims = ModelDimensions(times=times, regions=regions, sectors=sectors)

    params = ModelParameters(
        sigma=4.0,
        theta=5.0,
        kappa=8.0,
        xi=1.5,
        rho_j=np.array([0.05, 0.10]),
        iota=-0.02,
        eta=0.2,
        nu=5.0,
        alpha_j=np.array([0.5, 0.5]),
        v_j=np.array([0.02, -0.02]),
    )

    T, N, J = dims.T, dims.N, dims.J

    # Initial population distribution (must sum to 1)
    L0 = np.array([0.40, 0.35, 0.25])

    # Mass of potential firms (per region, by sector)
    M = np.full((T, J), 1.0)

    # Productivity shifters
    A = np.ones((T, N, J))

    # Land share in VA
    beta = np.full((T, N, J), 0.30)

    # Value added share
    gamma = np.full((T, N, J), 0.60)

    # Intermediate input shares gamma_{j,k} (output sector j, input sector k)
    gamma_io = np.zeros((T, N, J, J))
    # For Agri: material inputs sum to 0.40
    gamma_io[..., 0, 0] = 0.10  # Agri input
    gamma_io[..., 0, 1] = 0.30  # HeavyMnf input
    # For HeavyMnf: material inputs sum to 0.40
    gamma_io[..., 1, 0] = 0.25  # Agri input
    gamma_io[..., 1, 1] = 0.15  # HeavyMnf input

    # New-tech parameters (only meaningfully different for Agri)
    gammabreve_io = gamma_io.copy()
    gammabreve = gamma.copy()
    betabreve = beta.copy()

    # Make Agri new-tech more HeavyMnf-intensive by increasing ONLY the HeavyMnf input share.
    # Per the restriction used in the paper/prototype, non-HeavyMnf input shares remain unchanged,
    # and the value-added share adjusts to keep shares summing to one.
    gammabreve_io[..., 0, 1] = 0.35  # (was 0.30)
    gammabreve[..., 0] = 1.0 - gammabreve_io[..., 0, :].sum(axis=-1)
    gammabreve[..., 0] = np.clip(gammabreve[..., 0], 1e-6, 0.999)

    # Enforce the restriction: gammabreve * betabreve = gamma * beta (for Agri)
    betabreve[..., 0] = (gamma[..., 0] * beta[..., 0]) / gammabreve[..., 0]

    # Fixed costs (in units of the input bundle)
    F = np.full((T, N, J), 0.20)
    Fbreve = np.zeros((T, N, J))
    Fbreve[..., 0] = 0.05  # only Agri has adoption fixed costs
    Ftilde = np.full((T, N, J), 0.05)

    # Subsidies (rate on variable costs)
    s = np.zeros((T, N, J))
    s[..., 0] = 0.05  # small Agri subsidy

    # Foreign demand shifter and world prices
    Dtilde = np.full((T, J), 0.50)
    ptilde = np.ones((T, J))

    # Amenities
    Vbar = np.ones((T, N))

    # Trade costs within country (iceberg)
    tau = np.ones((T, J, N, N))
    for t in range(T):
        for j in range(J):
            for o in range(N):
                for d in range(N):
                    tau[t, j, o, d] = 1.0 if o == d else 1.2

    # Import iceberg costs (foreign -> region d)
    tautilde = np.full((T, J, N), 1.5)

    # Migration frictions delta_{o,d}
    delta = np.ones((T, N, N))
    for t in range(T):
        for o in range(N):
            for d in range(N):
                delta[t, o, d] = 1.0 if o == d else 1.1

    # Land/structures endowment
    H = np.full((T, N), 1.0)

    # Exogenous infrastructure spending
    tax_spending_on_building_H_and_roads = np.full((T,), 0.01)

    exog = ModelExogenousPaths(
        L0=L0,
        M=M,
        A=A,
        beta=beta,
        gamma=gamma,
        gamma_io=gamma_io,
        betabreve=betabreve,
        gammabreve=gammabreve,
        gammabreve_io=gammabreve_io,
        F=F,
        Fbreve=Fbreve,
        Ftilde=Ftilde,
        s=s,
        Dtilde=Dtilde,
        ptilde=ptilde,
        Vbar=Vbar,
        tau=tau,
        tautilde=tautilde,
        delta=delta,
        H=H,
        tax_spending_on_building_H_and_roads=tax_spending_on_building_H_and_roads,
    )

    inputs = ModelInputs(dims=dims, params=params, exog=exog)
    validate_inputs(inputs)
    return inputs


def main() -> None:
    inputs = build_toy_inputs()

    options = SolverOptions(
        max_iter=2000,
        tol=1e-7,
        damping=0.25,
        verbose=True,
    )

    path = solve_dynamic_equilibrium(inputs=inputs, options=options)

    print("\n=== Solution summary ===")
    print("w (t=0):", path.w[0])
    print("L (t=0):", path.L[0], "sum:", path.L[0].sum())
    print("taubar (t=0):", path.taubar[0], "pibar (t=0):", path.pibar[0])
    print("Max residual (t=0):", path.max_residual[0])
    print("")
    print("w (t=1):", path.w[1])
    print("L (t=1):", path.L[1], "sum:", path.L[1].sum())
    print("taubar (t=1):", path.taubar[1], "pibar (t=1):", path.pibar[1])
    print("Max residual (t=1):", path.max_residual[1])


if __name__ == "__main__":
    main()
