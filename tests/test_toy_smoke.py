import numpy as np

from korea_growth.solver import solve_dynamic_equilibrium
from korea_growth.types import SolverOptions

from scripts.solve_toy import build_toy_inputs


def test_toy_converges():
    inputs = build_toy_inputs()
    opts = SolverOptions(max_iter=2000, tol=1e-8, damping=0.25, verbose=False)
    path = solve_dynamic_equilibrium(inputs=inputs, options=opts)

    assert np.all(np.isfinite(path.w))
    assert np.all(np.isfinite(path.P))
    assert np.all(path.max_residual < 1e-6)
