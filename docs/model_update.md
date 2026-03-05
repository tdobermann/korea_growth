# Model Update: Marrying Theory with Empirical Results

This document describes the changes made to align the quantitative spatial
equilibrium model with the empirical findings in the paper draft
("The Miracle on the Han", 05 Mar 2026).

---

## 1. Summary of Changes

| Component | Before | After |
|-----------|--------|-------|
| **Sectors** | 2 (Agri, HeavyMnf) | 3 (Agri, HeavyMnf, **Services**) |
| **Regions** | 3 (Seoul, Busan, Daegu) | 5 (Seoul, Busan, **Changwon**, Daegu, **Rural**) |
| **Periods** | 5 (t=1..5, abstract) | 6 (t=1..6, mapped to 1965--1985) |
| **Policy** | Single-region, single-sector shock at t=4 | Multi-channel, phased HCI package |
| **Calibration** | Arbitrary parameters | Empirically informed (Tables 1--10) |

### Files modified

- `src/korea_growth/types.py` -- added `services_sector` field and `services_idx`
  property to `ModelDimensions`
- `scripts/simulate_policy_shock.py` -- complete rewrite (see below)

---

## 2. Motivation

The original simulation applied a single, stylised policy shock (Busan + Agri,
t=4) with no connection to the paper's empirical estimates. The paper identifies
**four interconnected channels** through which Korea's HCI drive affected the
spatial economy:

1. **Direct manufacturing effects** at industrial parks (SDID, Section 3.1)
2. **Road infrastructure** reducing trade and migration costs (Section 2.2)
3. **Agricultural modernisation** via market-access-driven machinery adoption
   (Section 3.2)
4. **Service sector growth** from rising rural incomes (Section 3.4)

The updated simulation implements all four channels with magnitudes calibrated
to the paper's point estimates.

---

## 3. Structural Extensions

### 3.1 Services Sector

The paper's Table 10 documents significant service sector growth in rural
townships exposed to market access improvements (+8.8 new establishments per
unit delta-log(MA), t=2.33). The original 2-sector model could not capture this
channel.

**Change:** Added `"Services"` as a third sector (j=2). In `ModelDimensions`,
a new `services_sector` field (default `"Services"`) and `services_idx`
property mirror the existing `agri_sector`/`heavy_mnf_sector` pattern.

Services characteristics in the baseline:
- High value-added share (gamma=0.70) -- mostly non-traded, few material inputs
- Moderate land share (beta=0.25) -- commercial real estate
- Low agglomeration elasticity (rho=0.06) -- local demand driven
- Largest expenditure share (alpha=0.40) -- consistent with 1960s Korean GDP
  composition (Figure 1)

### 3.2 Additional Regions

The paper's Figure 8 demonstrates a striking gradient in market access effects
by distance to industrial parks (non-farm population: -1.81 in D1 to +0.63 in
D10). Capturing this requires more than 3 regions.

**Change:** Expanded from 3 to 5 regions:

| Region | Role | Population share (1965) |
|--------|------|------------------------|
| Seoul | Capital, demand centre | 0.20 |
| Busan | Port city, secondary IP host | 0.12 |
| **Changwon** | Primary IP host (machinery complex, 1972-73) | 0.03 |
| Daegu | Intermediate city | 0.10 |
| **Rural** | Remote agricultural hinterland | 0.55 |

Initial population shares are calibrated to the paper's urbanisation data
(Figure 2: ~28% urban in 1960).

### 3.3 Historical Time Mapping

Periods are now mapped to the HCI timeline:

| t | Year | Event |
|---|------|-------|
| 1 | 1965 | Pre-HCI baseline |
| 2 | 1968 | Early industrialisation, first parks |
| 3 | 1973 | HCI declaration, Changwon/Onsan parks |
| 4 | 1975 | Peak HCI + Gyeongbu Expressway |
| 5 | 1980 | Road network doubled |
| 6 | 1985 | Mature effects, structural transformation |

---

## 4. Policy Calibration

### 4.1 Channel 1: Industrial Parks (t >= 3)

Calibrated to Table 1 SDID cohort-level ATT estimates. The 1972 and 1973
cohorts (Changwon machinery complex, Onsan-Ulsan complex) produced the
largest effects:

- Production ATT: 356,000--399,000 MMS units
- Employment ATT: 34,000--55,000 workers

**Model implementation:**
- Changwon: A_HeavyMnf * 1.50, F_HeavyMnf * 0.50, s_HeavyMnf = 0.25
- Busan: A_HeavyMnf * 1.25, F_HeavyMnf * 0.65, s_HeavyMnf = 0.15
- Outbound trade cost reduction from IP regions (tau * 0.85)

The productivity multiplier of 1.50 for Changwon reflects the enormous output
gains documented in the SDID event study (Figure 6), where log production
rises by approximately 2.5--3 log points over 10+ years post-treatment.

### 4.2 Channel 2: Road Infrastructure (t >= 2, phased)

The paper documents that paved road and highway coverage roughly doubled
between 1970 and 1980 (Section 2.2, Figure 5). The Gyeongbu Expressway
(Seoul--Busan, 428 km) opened in 1970, followed by five additional motorways
by 1981.

**Model implementation:** Trade costs (tau) decline by up to 50% of the
baseline gap over the period, phased as follows:

| Period | Year | Tau gap closed |
|--------|------|----------------|
| t=1 | 1965 | 0% |
| t=2 | 1968 | 10% |
| t=3 | 1973 | 25% |
| t=4 | 1975 | 40% |
| t=5 | 1980 | 50% |
| t=6 | 1985 | 50% |

Migration costs (delta) decline in parallel at 60% of the tau rate, reflecting
that roads reduce both goods and labour mobility frictions.

### 4.3 Channel 3: Agricultural Modernisation (t >= 3)

The paper's central rural spillover finding: improved road connectivity
(market access) drives agricultural machinery adoption, which in turn raises
productivity and reduces labour intensity.

**Key empirical estimates:**
- Table 2: +272 additional HH tillers per unit delta-log(MA)
  (s.e. 68, t=3.98)
- Table 4: +0.70 log points agricultural value-added per worker
  (s.e. 0.30, t=2.33)
- Table 4: -0.61 log points labour intensity (s.e. 0.29)

**Model implementation:**
- `Fbreve` (technology adoption cost) declines by up to 50% as roads
  improve, capturing the machinery-access channel
- `A_Agri` receives a per-period productivity boost (~10% per active period),
  accumulating to match the 0.70 log-point total effect
- `beta_Agri` shifts upward by 0.02 per period (more land/capital-intensive,
  less labour), capturing the -0.61 labour intensity decline

The decline in Fbreve is scaled by the road infrastructure phase factor,
creating the empirically documented link between market access and technology
adoption.

### 4.4 Channel 4: Export Demand Growth

Korea's export-led growth strategy amplified the park effects. Foreign demand
for heavy manufacturing (Dtilde) receives a 15% boost from t >= 3 onward,
reflecting the export infrastructure provided by industrial parks.

---

## 5. Baseline Parameter Choices

### 5.1 Expenditure Shares (alpha_j)

Calibrated to 1960s Korean GDP composition (Figure 1):
- Agriculture: 0.35 (~35% of GDP in 1965)
- Heavy Manufacturing: 0.25 (~15% in 1965, rising)
- Services: 0.40 (~45% in 1965)

Non-homothetic taste shifts (v_j = [+0.03, -0.01, -0.02]) ensure that as
incomes rise, expenditure shifts away from agriculture toward manufacturing
and services, matching the structural transformation in Figure 1.

### 5.2 Trade Costs

The asymmetric trade cost matrix reflects Korean geography:
- Seoul--Busan axis: tau = 1.30 (Gyeongbu corridor)
- Changwon--Busan: tau = 1.10 (nearby, southeastern corridor)
- Rural--Seoul: tau = 1.50 (highest, reflecting pre-road isolation)
- Self-trade: tau = 1.00 (by definition)

Port cities (Busan, Changwon) have lower import costs (tautilde = 1.30, 1.35
vs. 1.50 for inland regions).

### 5.3 Agglomeration

Sector-specific agglomeration elasticities (rho_j) reflect the paper's
spatial concentration findings:
- Agriculture: 0.03 (dispersed across rural areas)
- Heavy Manufacturing: 0.12 (strong concentration at parks, Figure 3)
- Services: 0.06 (moderate, driven by local demand)

---

## 6. Model Outputs and Empirical Validation

The simulation produces four output plots:

1. **structural_transformation.png** -- Economy-wide sectoral output shares
   over time. Should qualitatively match Figure 1: agriculture declining,
   manufacturing rising, services stable or rising.

2. **changwon_ip_mechanisms.png** -- Changwon-specific effects showing large
   wage, population, and manufacturing share gains at the IP host, consistent
   with the SDID event study (Figure 6).

3. **regional_policy_effects.png** -- Cross-regional comparison of policy
   effects. Should show the IP-distance gradient documented in Figure 8:
   largest manufacturing gains at Changwon, with spillovers attenuating
   by distance.

4. **rural_spillovers.png** -- Rural channels specifically: agricultural
   output share, population migration patterns, service sector growth, and
   income convergence. Calibrated to Tables 4, 6, and 10.

### End-of-horizon (1985) results summary

The model produces effects directionally consistent with the paper:
- **Changwon** receives the largest wage and manufacturing share gains
- **Rural** shows modest income gains (agricultural modernisation spillover)
  and slight population retention, consistent with the paper's finding that
  remote townships benefit from market access through productivity and
  service growth rather than industrial employment
- **Seoul** experiences wage gains but population share decline (consistent
  with the paper's finding that near-IP areas see outmigration to
  manufacturing centres)

---

## 7. Limitations and Future Work

1. **Number of regions:** Five regions is a reduced-form representation of the
   183-county panel used in the paper. A fully calibrated version would use
   county-level data.

2. **Continuous distance gradient:** The paper's Figure 8 shows continuous
   variation by IP-distance decile. The discrete 5-region model captures the
   qualitative gradient but not the full non-parametric shape.

3. **Service sector heterogeneity:** The model treats services as a single
   sector; the paper documents that service establishment growth is
   particularly strong in middle-to-remote deciles (D5--D10).

4. **Age-cohort migration:** Table 8 shows that prime working-age cohorts
   (25--49) are selectively retained. The model's homogeneous-agent migration
   framework cannot capture this heterogeneity.

5. **Oil shock attenuation:** The 1979 cohort shows near-zero effects
   (Table 1), suggesting that macro shocks interact with policy. The model
   does not include aggregate shocks.
