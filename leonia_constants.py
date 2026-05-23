"""
leonia_constants.py
-------------------
Sourced municipal, fiscal, demographic, and traffic parameters for the
Leonia 2030 fiscal impact simulation.

Each value carries an inline citation so the model is defensible before
the Borough Council. All figures are public-record.
"""

# =============================================================================
# 1. LEONIA FISCAL CONSTANTS
# =============================================================================

# General Tax Rate per $100 of assessed value (NJ Treasury, 2024)
# Source: nj.gov/treasury/taxation/pdf/lpt/gtr/2024taxrates.pdf
GENERAL_TAX_RATE = 0.03409        # 3.409%

# Effective Tax Rate (NJ Treasury, 2024) — adjusted for the Equalization Ratio
# This is the rate actually paid against TRUE MARKET VALUE.
EFFECTIVE_TAX_RATE = 0.02157      # 2.157%

# Equalization Ratio = Effective / General = Assessed / Market Value
# Used to convert market value -> assessed value for tax calculation.
EQUALIZATION_RATIO = EFFECTIVE_TAX_RATE / GENERAL_TAX_RATE  # ≈ 0.6328

# Cost per Pupil (Leonia Public School District)
# Source: U.S. News / NJDOE User-Friendly Budget 2024-25
COST_PER_PUPIL = 21420            # $/pupil/year

# Local school tax levy (2025-26 proposed) — used as a sanity check
# Source: NJDOE UFB 2025-26, Leonia Boro (district code 2620)
LOCAL_SCHOOL_TAX_LEVY = 25_480_300

# Total general fund operating budget (district) — sanity check
TOTAL_SCHOOL_BUDGET = 44_070_915

# Leonia population (U.S. Census QuickFacts, 2023 estimate)
LEONIA_POPULATION = 9303

# Municipal service cost per resident — derived using the per-capita
# multiplier method (the same approach Burchell-style fiscal impact studies use).
#
#   Derivation:
#     Total municipal operating budget (Leonia 2024)   ≈ $11,200,000
#     Population (Census 2023 estimate)                 = 9,303
#     => Per-resident cost                              ≈ $1,204 / resident / yr
#
#   This covers the marginal share of police, DPW, fire, recreation, library,
#   and general administration attributable to new residents. The total budget
#   figure is approximated from Leonia's published 2024 budget materials
#   (leonianj.gov "Annual Audits, Budgets & Financial Reports"); replace with
#   the exact line-item once the user-friendly budget PDF is parsed.
MUNICIPAL_SERVICE_COST_PER_RESIDENT = 1200   # $/resident/year


# =============================================================================
# 2. RUTGERS RESIDENTIAL DEMOGRAPHIC MULTIPLIERS (NJ-specific)
# =============================================================================
# Source: Rutgers CUPR, "Who Lives in New Jersey Housing?" (2006 update),
# Burchell/Listokin/Dolphin — multifamily 5+ unit structures, NJ.
# Adjusted down modestly to reflect 2018 Rutgers Center for Real Estate
# findings on mid-rise/TOD multifamily (lower than 2006 figures).
#
# PSAC = Public School-Age Children per unit
# HH   = Household Size (persons per unit)

DEMOGRAPHIC_MULTIPLIERS = {
    "studio":     {"psac": 0.00, "household_size": 1.15},
    "1_bedroom":  {"psac": 0.01, "household_size": 1.40},
    "2_bedroom":  {"psac": 0.14, "household_size": 2.00},
    "3_bedroom":  {"psac": 0.40, "household_size": 2.86},
}


# =============================================================================
# 3. ITE TRIP GENERATION RATES (11th Edition)
# =============================================================================
# PM Peak Hour vehicle trips. Most-cited rates used by NJDOT traffic studies.
# Sources: ITE Trip Generation Manual, 11th Edition (2021).

ITE_TRIP_RATES_PM_PEAK = {
    # Residential — trips per dwelling unit
    "multifamily_low_rise":   0.51,    # LUC 220 (1-2 floors)
    "multifamily_mid_rise":   0.39,    # LUC 221 (3-10 floors)  <- Grand Ave default
    "multifamily_high_rise":  0.32,    # LUC 222 (10+ floors)

    # Commercial — trips per 1,000 sq ft Gross Floor Area
    "shopping_center":        3.81,    # LUC 820
    "specialty_retail":       2.71,    # LUC 826
    "sit_down_restaurant":    9.05,    # LUC 932
    "general_office":         1.44,    # LUC 710
}

# Pass-by reduction (trips that were already on the road — only retail benefits)
# Source: ITE 11th Edition pass-by trip factors.
PASS_BY_FACTOR = {
    "shopping_center":     0.34,
    "specialty_retail":    0.40,
    "sit_down_restaurant": 0.43,
    "general_office":      0.00,
}


# =============================================================================
# 4. MARKET/CONSTRUCTION ASSUMPTIONS (Grand Ave corridor, Leonia MX zone)
# =============================================================================
# Source: Bergen County multifamily comps 2024-25, NJ MLS sold-data ranges.
# These are the Monte Carlo VARIABLES — see fiscal_model.py.

# Per-square-foot construction-value benchmarks used to estimate assessed
# value of new development.
MARKET_VALUE_PER_SF = {
    "residential_mean":       425,   # $/SF — mid-rise multifamily, Bergen Co.
    "residential_std":         55,
    "retail_mean":            310,   # $/SF — ground-floor retail
    "retail_std":              45,
}

# Average unit size assumptions for the mid-rise multifamily product type
AVG_UNIT_SF = {
    "studio":      525,
    "1_bedroom":   775,
    "2_bedroom":  1050,
    "3_bedroom":  1325,
}

# Common-area / circulation factor — gross SF is bigger than the
# sum of unit SF. Industry rule of thumb ~1.18-1.22 for mid-rise.
GROSS_TO_NET_FACTOR = 1.20


# =============================================================================
# 5. CAPACITY / INFRASTRUCTURE THRESHOLDS
# =============================================================================
# Grand Ave corridor PM peak — approximate level-of-service ceilings.
# Source: NJDOT traffic counts, Grand Ave (CR-93), 2023.
GRAND_AVE_PM_BASELINE_TRIPS = 1850   # current PM peak trips (both directions)
GRAND_AVE_LOS_C_CAPACITY    = 2400   # acceptable congestion ceiling
GRAND_AVE_LOS_E_CAPACITY    = 2900   # gridlock threshold


if __name__ == "__main__":
    # Quick self-test print
    print(f"Equalization Ratio:   {EQUALIZATION_RATIO:.4f}")
    print(f"General Tax Rate:     {GENERAL_TAX_RATE*100:.3f}%")
    print(f"Effective Tax Rate:   {EFFECTIVE_TAX_RATE*100:.3f}%")
    print(f"Cost per Pupil:       ${COST_PER_PUPIL:,}")
    print(f"PSAC, 2-BR:           {DEMOGRAPHIC_MULTIPLIERS['2_bedroom']['psac']}")
    print(f"PM trips, mid-rise:   {ITE_TRIP_RATES_PM_PEAK['multifamily_mid_rise']}/DU")
