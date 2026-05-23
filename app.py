"""
app.py
------
Leonia 2030 — Streamlit dashboard.

Tabs:
1. Single Scenario — sliders + KPIs + Monte Carlo
2. Compare Two — side-by-side A/B comparison
3. Preset Scenarios — one-click benchmark configurations
4. Methodology — formulas, sources, limitations

Run with: streamlit run app.py
"""
import io
from datetime import date

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

import leonia_constants as L
from fiscal_model import (
    Development,
    fiscal_impact,
    monte_carlo,
    summarize_monte_carlo,
)

# -----------------------------------------------------------------------------
# Page setup
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Leonia 2030 — Fiscal Impact Simulator",
    page_icon="🏛️",
    layout="wide",
)

st.title("🏛️ Leonia 2030: Mixed-Use Fiscal Impact Simulator")
st.caption(
    "A data-driven model estimating net tax revenue, school costs, "
    "municipal service costs, and PM-peak traffic for proposed developments "
    "along the Grand Ave corridor."
)

# -----------------------------------------------------------------------------
# Preset scenarios
# -----------------------------------------------------------------------------
PRESETS = {
    "— Custom —": None,
    "Modest mixed-use (96 units)": dict(
        studios=12, one_bedroom=48, two_bedroom=30, three_bedroom=6,
        retail_sf=8500, office_sf=0),
    "Family-heavy (3-BR loaded)": dict(
        studios=0, one_bedroom=10, two_bedroom=40, three_bedroom=50,
        retail_sf=4000, office_sf=0),
    "Large TOD-style (200 units)": dict(
        studios=30, one_bedroom=130, two_bedroom=35, three_bedroom=5,
        retail_sf=20000, office_sf=0),
    "Small infill (24 units, ground retail)": dict(
        studios=4, one_bedroom=14, two_bedroom=6, three_bedroom=0,
        retail_sf=3500, office_sf=0),
}


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def slider_block(prefix: str, defaults: dict) -> Development:
    """Render a column of sliders prefixed with a unique key, return Development."""
    st.markdown(f"**Residential Mix**")
    studios = st.slider("Studios", 0, 100, defaults["studios"], key=f"{prefix}_studio")
    one_bedroom = st.slider("1-Bedroom", 0, 200, defaults["one_bedroom"], key=f"{prefix}_1br")
    two_bedroom = st.slider("2-Bedroom", 0, 200, defaults["two_bedroom"], key=f"{prefix}_2br")
    three_bedroom = st.slider("3-Bedroom", 0, 100, defaults["three_bedroom"], key=f"{prefix}_3br")

    st.markdown(f"**Commercial Space**")
    retail_sf = st.slider("Retail SF", 0, 50_000, defaults["retail_sf"], step=500, key=f"{prefix}_retail")
    office_sf = st.slider("Office SF", 0, 50_000, defaults["office_sf"], step=500, key=f"{prefix}_office")

    st.markdown(f"**Market & PILOT**")
    res_val = st.slider("Residential $/SF", 200, 700,
                        L.MARKET_VALUE_PER_SF["residential_mean"], step=5,
                        key=f"{prefix}_resval")
    retail_val = st.slider("Retail $/SF", 150, 500,
                           L.MARKET_VALUE_PER_SF["retail_mean"], step=5,
                           key=f"{prefix}_retailval")
    pilot = st.checkbox("Apply 10/15% PILOT (tax abatement)",
                        value=False, key=f"{prefix}_pilot",
                        help="If checked, developer pays a Payment-in-Lieu-of-Taxes "
                             "(typical NJ Long-Term Tax Exemption): 10% of gross "
                             "residential rent + 15% of commercial. Usually MUCH "
                             "less revenue for the borough than standard property tax.")

    return Development(
        studios=studios, one_bedroom=one_bedroom,
        two_bedroom=two_bedroom, three_bedroom=three_bedroom,
        retail_sf=retail_sf, office_sf=office_sf,
        res_value_per_sf=res_val, retail_value_per_sf=retail_val,
        pilot_active=pilot,
    )


def render_kpis(result: dict, suffix: str = ""):
    """Four-column KPI strip."""
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"Annual Tax Revenue{suffix}",
              f"${result['annual_tax_revenue']:,.0f}")
    c2.metric(f"Total Annual Cost{suffix}",
              f"${result['annual_total_cost']:,.0f}")
    c3.metric(f"Net Fiscal Impact{suffix}",
              f"${result['net_fiscal_impact']:,.0f}",
              delta="break-even ✅" if result["break_even"] else "deficit ❌")
    c4.metric(f"Revenue : Cost{suffix}",
              f"{result['revenue_to_cost_ratio']:.2f}×")


def render_breakdown_chart(result: dict, title: str = "Fiscal Components"):
    breakdown = pd.DataFrame({
        "Category": ["Tax Revenue", "School Cost", "Municipal Service Cost"],
        "Amount": [result["annual_tax_revenue"],
                   -result["annual_school_cost"],
                   -result["annual_municipal_cost"]],
    })
    fig, ax = plt.subplots(figsize=(6, 3.6))
    colors = ["#2ca02c" if x > 0 else "#d62728" for x in breakdown["Amount"]]
    ax.barh(breakdown["Category"], breakdown["Amount"], color=colors)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Annual $")
    ax.set_title(title)
    ax.ticklabel_format(axis="x", style="plain")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    return fig


def build_memo(dev: Development, result: dict, mc_sum: dict) -> str:
    """Generate a 1-page text memo for download."""
    pilot_str = "Yes" if dev.pilot_active else "No"
    los_status = ("OK (below LOS C)" if not result["traffic"]["exceeds_los_c"]
                  else "Approaching LOS E" if not result["traffic"]["exceeds_los_e"]
                  else "Gridlock risk")
    return f"""LEONIA 2030 — FISCAL IMPACT MEMO
Generated: {date.today().isoformat()}

DEVELOPMENT PROGRAM
-------------------
Studios:                {dev.studios}
1-Bedroom:              {dev.one_bedroom}
2-Bedroom:              {dev.two_bedroom}
3-Bedroom:              {dev.three_bedroom}
Total Units:            {dev.total_units}
Retail SF:              {dev.retail_sf:,}
Office SF:              {dev.office_sf:,}
PILOT applied:          {pilot_str}

FISCAL IMPACT (Annual)
----------------------
Assessed Value:         ${result['assessed_value']:>14,.0f}
Tax / PILOT Revenue:    ${result['annual_tax_revenue']:>14,.0f}
School Cost:            ${result['annual_school_cost']:>14,.0f}   ({result['new_pupils']:.1f} new pupils)
Municipal Service Cost: ${result['annual_municipal_cost']:>14,.0f}   ({result['new_residents']:.0f} new residents)
Total Annual Cost:      ${result['annual_total_cost']:>14,.0f}

NET FISCAL IMPACT:      ${result['net_fiscal_impact']:>14,.0f}
Revenue : Cost Ratio:   {result['revenue_to_cost_ratio']:>14.2f}x
Break-even:             {"YES" if result['break_even'] else "NO"}

TRAFFIC IMPACT (PM Peak)
------------------------
New Trips:              {result['traffic']['total_new_trips']:.0f}
Projected Corridor Vol: {result['traffic']['projected_corridor']:.0f}
LOS Status:             {los_status}

MONTE CARLO ({mc_sum['n_iterations']:,} iterations)
-----------
Mean Net Impact:        ${mc_sum['mean_net_impact']:>14,.0f}
Worst Case (5th %ile):  ${mc_sum['p5_worst_case']:>14,.0f}
Best Case (95th %ile):  ${mc_sum['p95_best_case']:>14,.0f}
Probability Net Positive: {mc_sum['prob_positive']*100:.1f}%

METHODOLOGY
-----------
Tax Revenue = Gross SF x $/SF x Equalization Ratio ({L.EQUALIZATION_RATIO:.3f}) x General Tax Rate ({L.GENERAL_TAX_RATE*100:.3f}%)
School Cost = Sum(units x Rutgers PSAC multiplier) x ${L.COST_PER_PUPIL:,}/pupil
Service Cost = Sum(units x household size) x ${L.MUNICIPAL_SERVICE_COST_PER_RESIDENT:,}/resident
Traffic = ITE 11th Edition trip rates (LUC 221 mid-rise, LUC 820 retail)

Sources: NJ Treasury (general tax rates 2024); NJDOE User-Friendly Budget
2025-26 (Leonia Boro 2620); Rutgers CUPR "Who Lives in NJ Housing?" (2006);
ITE Trip Generation Manual 11th Edition (2021); U.S. Census QuickFacts.

LIMITATIONS: Planning-grade model. Not a substitute for a stamped fiscal
impact study or traffic study. See README for full caveats.
"""


# -----------------------------------------------------------------------------
# Tabs
# -----------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Single Scenario",
    "🆚 Compare Two",
    "📁 Preset Scenarios",
    "📚 Methodology",
])

# =============================================================================
# TAB 1 — Single Scenario
# =============================================================================
with tab1:
    st.sidebar.header("📐 Development Program")
    preset_name = st.sidebar.selectbox("Quick Preset", list(PRESETS.keys()), index=1)

    # --- FIX: when the preset dropdown changes, write its values into
    # session_state BEFORE the sliders render. Otherwise Streamlit keeps
    # the old slider values because the slider key already exists.
    if "last_preset" not in st.session_state:
        st.session_state.last_preset = preset_name

    if preset_name != st.session_state.last_preset:
        st.session_state.last_preset = preset_name
        if PRESETS[preset_name] is not None:
            cfg = PRESETS[preset_name]
            st.session_state["main_studio"] = cfg["studios"]
            st.session_state["main_1br"] = cfg["one_bedroom"]
            st.session_state["main_2br"] = cfg["two_bedroom"]
            st.session_state["main_3br"] = cfg["three_bedroom"]
            st.session_state["main_retail"] = cfg["retail_sf"]
            st.session_state["main_office"] = cfg["office_sf"]
            st.rerun()

    if PRESETS[preset_name] is not None:
        defaults = PRESETS[preset_name]
    else:
        defaults = PRESETS["Modest mixed-use (96 units)"]

    with st.sidebar:
        dev = slider_block("main", defaults)

        st.markdown("---")
        st.subheader("🎲 Monte Carlo Controls")
        n_iter = st.select_slider("Iterations", [250, 500, 1000, 2500, 5000], 1000)
        rate_mean = st.slider("Interest Rate (mean %)", 2.0, 12.0, 6.5, step=0.1, key="ratemean") / 100
        rate_std = st.slider("Interest Rate (σ, pp)", 0.1, 3.0, 1.5, step=0.1, key="ratestd") / 100

    result = fiscal_impact(dev)
    mc = monte_carlo(dev, n_iterations=n_iter,
                     interest_rate_mean=rate_mean,
                     interest_rate_std=rate_std)
    mc_sum = summarize_monte_carlo(mc)

    st.subheader("📊 Fiscal Snapshot")
    render_kpis(result)

    st.divider()
    left, right = st.columns([1, 1])
    with left:
        st.subheader("Revenue vs. Cost")
        st.pyplot(render_breakdown_chart(result), clear_figure=True)
    with right:
        st.subheader("Demographic & School Impact")
        st.write(f"**New residents:** {result['new_residents']:.1f}")
        st.write(f"**New public-school pupils:** {result['new_pupils']:.2f}")
        st.write(f"**Assessed value (taxable):** ${result['assessed_value']:,.0f}")
        pupil_pct = result["new_pupils"] / 1960 * 100
        st.progress(min(pupil_pct / 10, 1.0),
                    text=f"Adds {pupil_pct:.2f}% to enrollment (~1,960 pupils)")
        if dev.pilot_active:
            st.warning("⚠️ PILOT is active — revenue is gross-rent-based, "
                       "not assessed-value-based. Typically reduces borough "
                       "revenue 40-60% vs. standard property tax.")

    st.divider()
    st.subheader("🚦 PM-Peak Traffic Impact (Grand Ave)")
    t = result["traffic"]
    t1, t2, t3 = st.columns(3)
    t1.metric("New PM Peak Trips", f"{t['total_new_trips']:.0f}")
    t2.metric("Projected Corridor", f"{t['projected_corridor']:.0f}",
              delta=f"+{t['total_new_trips']:.0f}")
    los_status = ("🟢 OK" if not t["exceeds_los_c"]
                  else "🟡 Approaching LOS E" if not t["exceeds_los_e"]
                  else "🔴 Gridlock risk")
    t3.metric("LOS Status", los_status)

    fig2, ax2 = plt.subplots(figsize=(8, 1.6))
    ax2.barh([""], [t["projected_corridor"]], color="#1f77b4", height=0.4)
    ax2.axvline(L.GRAND_AVE_PM_BASELINE_TRIPS, color="gray", ls="--", label="Baseline")
    ax2.axvline(L.GRAND_AVE_LOS_C_CAPACITY, color="orange", ls="--", label="LOS C")
    ax2.axvline(L.GRAND_AVE_LOS_E_CAPACITY, color="red", ls="--", label="LOS E")
    ax2.set_xlim(0, max(L.GRAND_AVE_LOS_E_CAPACITY + 200, t["projected_corridor"] + 200))
    ax2.set_xlabel("PM Peak Hour Vehicle Trips")
    ax2.legend(loc="upper right", fontsize=8, framealpha=0.9)
    for spine in ("top", "right", "left"):
        ax2.spines[spine].set_visible(False)
    ax2.set_yticks([])
    st.pyplot(fig2, clear_figure=True)

    st.divider()
    st.subheader("🎲 Monte Carlo Sensitivity")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Mean Net", f"${mc_sum['mean_net_impact']:,.0f}")
    m2.metric("Worst (P5)", f"${mc_sum['p5_worst_case']:,.0f}")
    m3.metric("Best (P95)", f"${mc_sum['p95_best_case']:,.0f}")
    m4.metric("P(net positive)", f"{mc_sum['prob_positive']*100:.1f}%")

    fig3, ax3 = plt.subplots(figsize=(9, 3.6))
    ax3.hist(mc["net_impact"], bins=40, color="#4c72b0", edgecolor="white", alpha=0.85)
    ax3.axvline(0, color="black", linewidth=1, label="Break-even")
    ax3.axvline(mc_sum["mean_net_impact"], color="#2ca02c", ls="--", label="Mean")
    ax3.axvline(mc_sum["p5_worst_case"], color="#d62728", ls="--", label="P5")
    ax3.axvline(mc_sum["p95_best_case"], color="#ff7f0e", ls="--", label="P95")
    ax3.set_xlabel("Net Fiscal Impact ($/yr)")
    ax3.set_title("Monte Carlo Distribution")
    ax3.legend()
    for spine in ("top", "right"):
        ax3.spines[spine].set_visible(False)
    ax3.ticklabel_format(axis="x", style="plain")
    st.pyplot(fig3, clear_figure=True)

    # Memo download
    memo_text = build_memo(dev, result, mc_sum)
    st.download_button("📄 Download 1-page Memo (TXT)",
                       data=memo_text,
                       file_name=f"leonia_memo_{date.today().isoformat()}.txt",
                       mime="text/plain")


# =============================================================================
# TAB 2 — Compare Two
# =============================================================================
with tab2:
    st.subheader("🆚 Side-by-Side Scenario Comparison")
    st.caption("Configure two development programs and compare their fiscal "
               "and traffic impacts head-to-head.")

    colA, colB = st.columns(2)
    with colA:
        st.markdown("### Scenario A")
        st.caption("Defaults: 'Modest mixed-use (96 units)'")
        devA = slider_block("A", PRESETS["Modest mixed-use (96 units)"])
    with colB:
        st.markdown("### Scenario B")
        st.caption("Defaults: 'Family-heavy (3-BR loaded)'")
        devB = slider_block("B", PRESETS["Family-heavy (3-BR loaded)"])

    rA = fiscal_impact(devA)
    rB = fiscal_impact(devB)

    st.divider()
    st.markdown("### Comparison Table")
    comp = pd.DataFrame({
        "Metric": ["Total Units", "Retail SF", "Assessed Value",
                   "Annual Tax Revenue", "New Pupils", "School Cost",
                   "Municipal Cost", "Total Cost", "NET FISCAL IMPACT",
                   "Revenue:Cost Ratio", "PM Peak New Trips",
                   "Corridor Total", "Break-even"],
        "Scenario A": [
            devA.total_units, f"{devA.retail_sf:,}",
            f"${rA['assessed_value']:,.0f}",
            f"${rA['annual_tax_revenue']:,.0f}",
            f"{rA['new_pupils']:.2f}",
            f"${rA['annual_school_cost']:,.0f}",
            f"${rA['annual_municipal_cost']:,.0f}",
            f"${rA['annual_total_cost']:,.0f}",
            f"${rA['net_fiscal_impact']:,.0f}",
            f"{rA['revenue_to_cost_ratio']:.2f}×",
            f"{rA['traffic']['total_new_trips']:.0f}",
            f"{rA['traffic']['projected_corridor']:.0f}",
            "✅" if rA["break_even"] else "❌",
        ],
        "Scenario B": [
            devB.total_units, f"{devB.retail_sf:,}",
            f"${rB['assessed_value']:,.0f}",
            f"${rB['annual_tax_revenue']:,.0f}",
            f"{rB['new_pupils']:.2f}",
            f"${rB['annual_school_cost']:,.0f}",
            f"${rB['annual_municipal_cost']:,.0f}",
            f"${rB['annual_total_cost']:,.0f}",
            f"${rB['net_fiscal_impact']:,.0f}",
            f"{rB['revenue_to_cost_ratio']:.2f}×",
            f"{rB['traffic']['total_new_trips']:.0f}",
            f"{rB['traffic']['projected_corridor']:.0f}",
            "✅" if rB["break_even"] else "❌",
        ],
        "Δ (B − A)": [
            devB.total_units - devA.total_units,
            f"{devB.retail_sf - devA.retail_sf:+,}",
            f"${rB['assessed_value'] - rA['assessed_value']:+,.0f}",
            f"${rB['annual_tax_revenue'] - rA['annual_tax_revenue']:+,.0f}",
            f"{rB['new_pupils'] - rA['new_pupils']:+.2f}",
            f"${rB['annual_school_cost'] - rA['annual_school_cost']:+,.0f}",
            f"${rB['annual_municipal_cost'] - rA['annual_municipal_cost']:+,.0f}",
            f"${rB['annual_total_cost'] - rA['annual_total_cost']:+,.0f}",
            f"${rB['net_fiscal_impact'] - rA['net_fiscal_impact']:+,.0f}",
            "—",
            f"{rB['traffic']['total_new_trips'] - rA['traffic']['total_new_trips']:+.0f}",
            f"{rB['traffic']['projected_corridor'] - rA['traffic']['projected_corridor']:+.0f}",
            "—",
        ],
    })
    st.dataframe(comp, use_container_width=True, hide_index=True)

    st.divider()
    cc1, cc2 = st.columns(2)
    with cc1:
        st.markdown("**Scenario A — Components**")
        st.pyplot(render_breakdown_chart(rA, "Scenario A"), clear_figure=True)
    with cc2:
        st.markdown("**Scenario B — Components**")
        st.pyplot(render_breakdown_chart(rB, "Scenario B"), clear_figure=True)


# =============================================================================
# TAB 3 — Preset Scenarios
# =============================================================================
with tab3:
    st.subheader("📁 Pre-Configured Benchmark Scenarios")
    st.caption("These represent typical mixed-use proposals seen along Bergen "
               "County's MX corridors. Click any row to see its details.")

    preset_rows = []
    for name, cfg in PRESETS.items():
        if cfg is None:
            continue
        dev = Development(**cfg)
        r = fiscal_impact(dev)
        preset_rows.append({
            "Scenario": name,
            "Units": dev.total_units,
            "Retail SF": f"{dev.retail_sf:,}",
            "Pupils": f"{r['new_pupils']:.1f}",
            "Revenue": f"${r['annual_tax_revenue']:,.0f}",
            "Total Cost": f"${r['annual_total_cost']:,.0f}",
            "Net Impact": f"${r['net_fiscal_impact']:,.0f}",
            "PM Trips": f"{r['traffic']['total_new_trips']:.0f}",
            "Break-even": "✅" if r["break_even"] else "❌",
        })
    st.dataframe(pd.DataFrame(preset_rows),
                 use_container_width=True, hide_index=True)

    st.info("💡 **Key insight:** *Unit count* drives revenue and traffic, "
            "but *unit mix* drives school cost. A 100-unit project loaded with "
            "3-BR units can generate 3× the pupils of a 200-unit project "
            "loaded with 1-BR units.")


# =============================================================================
# TAB 4 — Methodology
# =============================================================================
with tab4:
    st.subheader("📚 Methodology & Sources")
    st.markdown(f"""
#### Tax Revenue Formula
```
Market Value   = Σ (SF × $/SF) for residential + retail + office
Assessed Value = Market Value × Equalization Ratio ({L.EQUALIZATION_RATIO:.4f})
Tax Revenue    = Assessed Value × General Tax Rate ({L.GENERAL_TAX_RATE*100:.3f}%)
```

#### PILOT Alternative (if checked)
```
PILOT Revenue = (units × avg rent × 10%) + (commercial SF × $/SF × 15%)
```

#### Cost Formulas
```
New Pupils    = Σ (units × Rutgers PSAC multiplier)
School Cost   = Pupils × ${L.COST_PER_PUPIL:,} / pupil / year
Service Cost  = Residents × ${L.MUNICIPAL_SERVICE_COST_PER_RESIDENT:,} / resident / year
```

#### Traffic Formula (ITE 11th Edition, PM Peak)
```
Residential trips = Units × {L.ITE_TRIP_RATES_PM_PEAK['multifamily_mid_rise']}  (LUC 221)
Retail trips      = (SF / 1000) × {L.ITE_TRIP_RATES_PM_PEAK['shopping_center']} × (1 − 0.34 pass-by)
Office trips      = (SF / 1000) × {L.ITE_TRIP_RATES_PM_PEAK['general_office']}
```
""")
    st.markdown("### Sourced Constants")
    src = pd.DataFrame([
        ["General Tax Rate", "3.409%", "NJ Treasury — General Tax Rates, 2024"],
        ["Effective Tax Rate", "2.157%", "NJ Treasury — General Tax Rates, 2024"],
        ["Equalization Ratio", f"{L.EQUALIZATION_RATIO:.3f}", "Derived"],
        ["Cost per Pupil", f"${L.COST_PER_PUPIL:,}", "NJDOE / Leonia Schools"],
        ["District Enrollment", "1,960", "NJDOE UFB 2025-26 (district 2620)"],
        ["Leonia Population", f"{L.LEONIA_POPULATION:,}", "U.S. Census 2023"],
        ["PSAC, 1-BR", "0.01", "Rutgers CUPR (2006)"],
        ["PSAC, 2-BR", "0.14", "Rutgers CUPR (2006)"],
        ["PSAC, 3-BR", "0.40", "Rutgers CUPR (2006)"],
        ["PM trip rate, mid-rise", "0.39 / DU", "ITE 11th Ed., LUC 221"],
        ["PM trip rate, retail", "3.81 / 1k SF", "ITE 11th Ed., LUC 820"],
    ], columns=["Parameter", "Value", "Source"])
    st.dataframe(src, use_container_width=True, hide_index=True)

    st.markdown("### ⚠️ Limitations")
    st.markdown("""
- **Planning-grade**, not a stamped fiscal-impact study.
- PSAC multipliers reflect statewide multifamily averages; TOD products generate fewer.
- Traffic ignores mode shift (walk/bike/bus). A real study would apply NCHRP 758.
- Interest-rate sensitivity is linear; real comp values move non-linearly.
- PILOT modeling uses typical NJ Long-Term Tax Exemption rates; actual deals vary.
- Municipal service cost is a single per-capita figure; Burchell per-capita-multiplier
  method would split out police, DPW, admin, parks separately.
""")
