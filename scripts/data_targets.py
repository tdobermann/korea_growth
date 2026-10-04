"""Macro targets for Korea, 1965-1985, with provenance.

Every value states where it comes from. Two statuses:

- ``sourced``: stated in a document in this repository, cited by location.
- ``unverified``: an approximate value carried over from docs/fresh_look.md section 1.1
  ("order-of-magnitude values for orientation; each needs to be replaced from source").
  These have NOT been checked against the named source. Replace them with the digitised
  series before reading the calibration as quantitative.

Nothing here is interpolated or filled in. A moment with no value in the repository is
listed in MISSING rather than given a guess.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Target:
    key: str
    year: int
    value: float
    source: str
    status: str  # "sourced" or "unverified"


TARGETS = [
    # Structural transformation (calibration targets)
    Target("ag_employment_share", 1965, 0.59, "EAPS (Statistics Korea); fresh_look.md 1.1", "unverified"),
    Target("ag_employment_share", 1985, 0.25, "EAPS (Statistics Korea); fresh_look.md 1.1", "unverified"),
    Target("mnf_va_share", 1965, 0.15, "paper draft sec. 1 ('around 15%'), from World Bank WDI", "sourced"),
    Target("mnf_va_share", 1985, 0.30, "paper draft sec. 1 ('nearly 30%'), from World Bank WDI", "sourced"),
    Target("real_gdp_pc_ratio", 1985, 4.0, "Maddison / PWT, 1985 relative to 1965; fresh_look.md 1.1", "unverified"),
    Target("exports_gdp", 1965, 0.09, "BoK national accounts; fresh_look.md 1.1", "unverified"),
    Target("exports_gdp", 1985, 0.33, "BoK national accounts; fresh_look.md 1.1", "unverified"),
    # Population: the 1965 value sets the initial distribution (amenity inversion).
    Target("urban_pop_share", 1965, 0.32, "WDI; fresh_look.md 1.1 (paper draft gives 28% for 1960)", "unverified"),
    Target("urban_pop_share", 1980, 0.57, "paper draft sec. 1 ('57% by 1980')", "sourced"),
    # Validation only (not targeted)
    Target("urban_pop_share", 1985, 0.65, "WDI; fresh_look.md 1.1", "unverified"),
    Target("ag_va_share", 1965, 0.38, "BoK national accounts; scorecard (added 2026-10-03)", "unverified"),
    Target("ag_va_share", 1985, 0.13, "BoK national accounts; scorecard (added 2026-10-03)", "unverified"),
]

CALIBRATION_KEYS = [
    ("ag_employment_share", 1965),
    ("ag_employment_share", 1985),
    ("mnf_va_share", 1965),
    ("mnf_va_share", 1985),
    ("real_gdp_pc_ratio", 1985),
    ("exports_gdp", 1965),
    ("exports_gdp", 1985),
    ("urban_pop_share", 1980),
]

# Moments the calibration would use if data were available, with none in the repository.
MISSING = [
    "food expenditure share by income (household surveys): pins the PIGL Engel curve directly",
    "grain / other-farm import share (self-sufficiency ratios): disciplines the OtherAg import margin",
    "rice's share of food expenditure: the Rice / OtherAg split of the food demand parameters",
    "power tillers per farm household, 1965-85: pins the rice mechanisation fixed cost",
    "sectoral TFP or labour-productivity growth (e.g. GGDC 10-sector): separates g_farm from g_svc",
    "regional population and farm employment: replaces the stylised five-region split",
    "input-output coefficients (BoK IO tables): the stylised IO matrix over-produces manufacturing in 1965",
    "farm vs non-farm earnings: the agricultural productivity gap needs sectoral wage data",
]


def target(key: str, year: int) -> Target:
    for tg in TARGETS:
        if tg.key == key and tg.year == year:
            return tg
    raise KeyError((key, year))
