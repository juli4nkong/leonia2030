"""
make_screenshot.py
------------------
Generates a single composite PNG that LOOKS like the dashboard, suitable
for the README hero image. We can't actually screenshot Streamlit in this
sandbox, so we render a representative figure that captures the same charts.
"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

from fiscal_model import Development, fiscal_impact, monte_carlo, summarize_monte_carlo
import leonia_constants as L

# Use the modest mixed-use scenario
dev = Development(studios=12, one_bedroom=48, two_bedroom=30, three_bedroom=6,
                  retail_sf=8500)
r = fiscal_impact(dev)
mc = monte_carlo(dev, n_iterations=2500, seed=42)
sm = summarize_monte_carlo(mc)

fig = plt.figure(figsize=(14, 8), facecolor="#f7f7f9")
gs = fig.add_gridspec(3, 4, hspace=0.55, wspace=0.45,
                      top=0.92, bottom=0.06, left=0.05, right=0.97)

# ── Title bar ─────────────────────────────────────────────────────────────
fig.suptitle("Leonia 2030 — Mixed-Use Fiscal Impact Simulator",
             fontsize=18, fontweight="bold", y=0.97)

# ── KPI strip ──────────────────────────────────────────────────────────────
kpi_ax = fig.add_subplot(gs[0, :])
kpi_ax.axis("off")
kpis = [
    ("Annual Tax Revenue", f"${r['annual_tax_revenue']:,.0f}",   "#2ca02c"),
    ("Total Annual Cost",  f"${r['annual_total_cost']:,.0f}",    "#d62728"),
    ("Net Fiscal Impact",  f"${r['net_fiscal_impact']:,.0f}",    "#1f77b4"),
    ("Revenue : Cost",     f"{r['revenue_to_cost_ratio']:.2f}×", "#ff7f0e"),
]
for i, (label, value, color) in enumerate(kpis):
    box = patches.FancyBboxPatch(
        (i * 0.25 + 0.01, 0.1), 0.23, 0.8,
        boxstyle="round,pad=0.02",
        linewidth=1.2, edgecolor=color, facecolor="white",
        transform=kpi_ax.transAxes)
    kpi_ax.add_patch(box)
    kpi_ax.text(i * 0.25 + 0.125, 0.65, label,
                ha="center", va="center", fontsize=10, color="#555",
                transform=kpi_ax.transAxes)
    kpi_ax.text(i * 0.25 + 0.125, 0.30, value,
                ha="center", va="center", fontsize=15, fontweight="bold",
                color=color, transform=kpi_ax.transAxes)

# ── Breakdown bars ─────────────────────────────────────────────────────────
bd_ax = fig.add_subplot(gs[1, :2])
cats   = ["Tax Revenue", "School Cost", "Service Cost"]
vals   = [r["annual_tax_revenue"], -r["annual_school_cost"], -r["annual_municipal_cost"]]
colors = ["#2ca02c" if v > 0 else "#d62728" for v in vals]
bd_ax.barh(cats, vals, color=colors)
bd_ax.axvline(0, color="black", linewidth=0.8)
bd_ax.set_xlabel("Annual $")
bd_ax.set_title("Revenue vs. Cost Breakdown", fontweight="bold")
bd_ax.ticklabel_format(axis="x", style="plain")
for spine in ("top", "right"):
    bd_ax.spines[spine].set_visible(False)

# ── Traffic LOS bar ────────────────────────────────────────────────────────
tr_ax = fig.add_subplot(gs[1, 2:])
proj = r["traffic"]["projected_corridor"]
tr_ax.barh([""], [proj], color="#1f77b4", height=0.35)
tr_ax.axvline(L.GRAND_AVE_PM_BASELINE_TRIPS, color="gray",   ls="--", label="Baseline")
tr_ax.axvline(L.GRAND_AVE_LOS_C_CAPACITY,    color="orange", ls="--", label="LOS C")
tr_ax.axvline(L.GRAND_AVE_LOS_E_CAPACITY,    color="red",    ls="--", label="LOS E")
tr_ax.set_xlim(0, L.GRAND_AVE_LOS_E_CAPACITY + 200)
tr_ax.set_xlabel("PM Peak Hour Vehicle Trips")
tr_ax.set_title("Grand Ave Corridor — PM Peak Load", fontweight="bold")
tr_ax.legend(loc="lower right", fontsize=8)
for spine in ("top", "right", "left"):
    tr_ax.spines[spine].set_visible(False)
tr_ax.set_yticks([])

# ── Monte Carlo histogram ─────────────────────────────────────────────────
mc_ax = fig.add_subplot(gs[2, :])
mc_ax.hist(mc["net_impact"], bins=45, color="#4c72b0", edgecolor="white", alpha=0.85)
mc_ax.axvline(0, color="black", linewidth=1, label="Break-even")
mc_ax.axvline(sm["mean_net_impact"], color="#2ca02c", ls="--", label=f"Mean: ${sm['mean_net_impact']:,.0f}")
mc_ax.axvline(sm["p5_worst_case"],   color="#d62728", ls="--", label=f"P5 worst: ${sm['p5_worst_case']:,.0f}")
mc_ax.axvline(sm["p95_best_case"],   color="#ff7f0e", ls="--", label=f"P95 best: ${sm['p95_best_case']:,.0f}")
mc_ax.set_xlabel("Net Fiscal Impact ($/yr)")
mc_ax.set_ylabel("Frequency")
mc_ax.set_title(f"Monte Carlo Sensitivity — {sm['n_iterations']:,} iterations | "
                f"P(net positive) = {sm['prob_positive']*100:.1f}%",
                fontweight="bold")
mc_ax.legend(loc="upper right", fontsize=8)
for spine in ("top", "right"):
    mc_ax.spines[spine].set_visible(False)
mc_ax.ticklabel_format(axis="x", style="plain")

plt.savefig("dashboard_preview.png", dpi=140, bbox_inches="tight",
            facecolor=fig.get_facecolor())
print("✓ Saved dashboard_preview.png")
