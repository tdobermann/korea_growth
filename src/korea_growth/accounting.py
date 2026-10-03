"""Sectoral national accounts at a solved equilibrium.

Reporting helpers that turn an equilibrium slice into the objects the macro story is
measured in (docs/review_fresh_look.md 1.3 item 4 and 2.1-2.2):

- gross output, intermediate purchases and value added by region and sector;
- employment (workers, not payments) by region and sector, including the labour that pays
  fixed costs, so that employment sums to population in every region;
- producer price indices, and a chained Fisher double-deflated real GDP index.

The formulas mirror ``equilibrium.compute_implied_static``; ``tests/test_accounting.py``
checks that the two agree (value added sums to GDP, employment sums to population).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .trade import compute_sector_state
from .types import ModelInputs


@dataclass(frozen=True)
class SectorAccounts:
    """Accounts for one period. Arrays are (N, J) unless noted; o = region, j = sector."""

    gross_output: np.ndarray
    intermediates: np.ndarray  # (N, J, K) purchases by sector j in region o of input k
    value_added: np.ndarray  # gross output - intermediate purchases
    labor_variable: np.ndarray  # variable labour payments
    labor_fixed: np.ndarray  # fixed-cost labour payments (F, Ftilde, Fbreve)
    employment: np.ndarray  # workers = (variable + fixed labour payments) / w_o
    producer_price: np.ndarray  # CES index of region-o sector-j varieties at the factory gate
    purchaser_price: np.ndarray  # P_{o,k}, the price of intermediates bought in o
    traditional_ag_output_share: float  # national share of farm output on the old technology


def sector_accounts(inputs: ModelInputs, t: int, L_prev: np.ndarray, eq) -> SectorAccounts:
    """Compute :class:`SectorAccounts` at an equilibrium slice ``eq`` (w, r, P, E)."""

    dims, params, exog = inputs.dims, inputs.params, inputs.exog
    N, J = dims.N, dims.J
    sigma = params.sigma
    agri = dims.agri_idx

    gross = np.zeros((N, J))
    inter = np.zeros((N, J, J))
    lab_var = np.zeros((N, J))
    lab_fix = np.zeros((N, J))
    ppi = np.zeros((N, J))
    trad_share = np.nan

    for j in range(J):
        st = compute_sector_state(
            t=t, j=j, dims=dims, params=params, exog=exog, L_prev=L_prev,
            w=eq.w, r=eq.r, P=eq.P, E=eq.E,
        )
        tfc_scale = (sigma - 1.0) / sigma / (1.0 - exog.s[t, :, j])
        gross[:, j] = st.gross_output
        if j == agri:
            tfc_trad = tfc_scale * st.R_trad
            tfc_new = tfc_scale * (st.R_breve + st.R_tilde)
            inter[:, j, :] = (
                tfc_trad[:, None] * exog.gamma_io[t, :, j, :]
                + tfc_new[:, None] * exog.gammabreve_io[t, :, j, :]
            )
            lab_var[:, j] = (
                (1.0 - exog.beta[t, :, j]) * exog.gamma[t, :, j] * tfc_trad
                + (1.0 - exog.betabreve[t, :, j]) * exog.gammabreve[t, :, j] * tfc_new
            )
            total = float(st.gross_output.sum())
            trad_share = float(st.R_trad.sum() / total) if total > 0 else np.nan
        else:
            tfc = tfc_scale * st.gross_output
            inter[:, j, :] = tfc[:, None] * exog.gamma_io[t, :, j, :]
            lab_var[:, j] = (1.0 - exog.beta[t, :, j]) * exog.gamma[t, :, j] * tfc
        lab_fix[:, j] = st.fixed_cost_bill
        with np.errstate(divide="ignore"):
            ppi[:, j] = np.power(st.B_domestic, 1.0 / (1.0 - sigma))

    value_added = gross - inter.sum(axis=2)
    employment = (lab_var + lab_fix) / np.maximum(eq.w, 1e-300)[:, None]
    return SectorAccounts(
        gross_output=gross,
        intermediates=inter,
        value_added=value_added,
        labor_variable=lab_var,
        labor_fixed=lab_fix,
        employment=employment,
        producer_price=ppi,
        purchaser_price=np.asarray(eq.P, dtype=float),
        traditional_ag_output_share=trad_share,
    )


def _double_deflated_va(prices_from: SectorAccounts, quantities_from: SectorAccounts) -> float:
    """Value added of ``quantities_from`` quantities at ``prices_from`` prices.

    Output quantities are gross output deflated by the producer price index; intermediate
    quantities are purchases deflated by the purchaser price of the input in that region.
    """

    def output_value(p: np.ndarray, a: SectorAccounts) -> np.ndarray:
        with np.errstate(invalid="ignore", divide="ignore"):
            q = np.where(a.gross_output > 0.0, a.gross_output / a.producer_price, 0.0)
        return np.where(q > 0.0, p * q, 0.0)

    y = output_value(prices_from.producer_price, quantities_from)
    x_qty = quantities_from.intermediates / quantities_from.purchaser_price[:, None, :]
    x = x_qty * prices_from.purchaser_price[:, None, :]
    return float(np.sum(y) - np.sum(x))


def real_gdp_index(accounts: list[SectorAccounts]) -> np.ndarray:
    """Chained Fisher index of real value added (double deflation), first period = 1.

    Each region-sector's output is a distinct good priced at its producer price index, and
    intermediates are priced at local purchaser prices. This is a production-side volume
    index, comparable to national-accounts real GDP; GDP divided by a consumption deflator
    is a purchasing-power measure instead (docs/review_fresh_look.md 2.2).
    """

    idx = [1.0]
    for prev, cur in zip(accounts[:-1], accounts[1:]):
        nominal_prev = _double_deflated_va(prev, prev)
        nominal_cur = _double_deflated_va(cur, cur)
        laspeyres = _double_deflated_va(prev, cur) / nominal_prev
        paasche = nominal_cur / _double_deflated_va(cur, prev)
        idx.append(idx[-1] * float(np.sqrt(laspeyres * paasche)))
    return np.asarray(idx)
