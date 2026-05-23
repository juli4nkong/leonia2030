"""
demo_run.py
-----------
Headless demo + sensitivity sweep. Useful for:
  - Validating the model without spinning up Streamlit
  - Generating chart images for slide decks / reports
  - Stress-testing under unfavorable inputs
"""

import numpy as np
import matplotlib.pyplot as plt

from fiscal_model import (
    Development,
    fiscal_impact,
    monte_carlo,
    summarize_monte_carlo,
)


def print_result(label: str, dev: Development) -> dict:
    r = fiscal_impact(dev)
    print(f"\n--- {label} ---")
    print(f"  Units: {dev.total_units}   Retail: {dev.retail_sf:,} SF")
    print(f"  Tax revenue:     ${r['annual_tax_revenue']:>11,.0f}")
    print(f"  School cost:     ${r['annual_school_cost']:>11,.0f}  "
          f"({r['new_pupils']:.2f} pupils)")
    print(f"  Service cost:    ${r['annual_municipal_cost']:>11,.0f}  "
          f"({r['new_residents']:.1f} residents)")
    print(f"  NET:             ${r['net_fiscal_impact']:>11,.0f}   "
          f"{'✅' if r['break_even'] else '❌'}")
    print(f"  PM new trips:    {r['traffic']['total_new_trips']:.0f}    "
          f"Corridor: {r['traffic']['projected_corridor']:.0f}/{r['traffic']['los_e_capacity']}")
    return r


# -----------------------------------------------------------------------------
# Three benchmark scenarios
# -----------------------------------------------------------------------------

scenarios = {
    "Modest mixed-use (96 units)": Development(
        studios=12, one_bedroom=48, two_bedroom=30, three_bedroom=6,
        retail_sf=8500),

    "Family-heavy proposal (3-BR loaded)": Development(
        studios=0, one_bedroom=10, two_bedroom=40, three_bedroom=50,
        retail_sf=4000),

    "Large TOD-style (200 units, mostly 1-BR)": Development(
        studios=30, one_bedroom=130, two_bedroom=35, three_bedroom=5,
        retail_sf=20_000),
}

print("=" * 72)
print("LEONIA 2030 — BENCHMARK SCENARIOS")
print("=" * 72)

for name, dev in scenarios.items():
    print_result(name, dev)


# -----------------------------------------------------------------------------
# Unit-count sensitivity sweep — find break-even threshold
# -----------------------------------------------------------------------------

print("\n" + "=" * 72)
print("SENSITIVITY: scaling unit count, fixed mix (12% studio / 50% 1BR / "
      "31% 2BR / 7% 3BR), 80 SF retail per unit")
print("=" * 72)

total_units_grid = list(range(20, 301, 20))
nets, pupils, trips = [], [], []

for n in total_units_grid:
    dev = Development(
        studios       = int(0.12 * n),
        one_bedroom   = int(0.50 * n),
        two_bedroom   = int(0.31 * n),
        three_bedroom = int(0.07 * n),
        retail_sf     = n * 80,
    )
    r = fiscal_impact(dev)
    nets.append(r["net_fiscal_impact"])
    pupils.append(r["new_pupils"])
    trips.append(r["traffic"]["total_new_trips"])

# -----------------------------------------------------------------------------
# Plot the sensitivity sweep
# -----------------------------------------------------------------------------

fig, axes = plt.subplots(1, 3, figsize=(14, 4))

axes[0].plot(total_units_grid, nets, marker="o", color="#2ca02c")
axes[0].axhline(0, color="black", linewidth=0.8)
axes[0].set_xlabel("Total Units")
axes[0].set_ylabel("Net Fiscal Impact ($/yr)")
axes[0].set_title("Net Fiscal Impact vs. Project Size")
axes[0].ticklabel_format(axis="y", style="plain")

axes[1].plot(total_units_grid, pupils, marker="o", color="#1f77b4")
axes[1].set_xlabel("Total Units")
axes[1].set_ylabel("New Pupils")
axes[1].set_title("Pupil Generation")

axes[2].plot(total_units_grid, trips, marker="o", color="#d62728")
axes[2].set_xlabel("Total Units")
axes[2].set_ylabel("New PM-Peak Trips")
axes[2].set_title("Traffic Generation")

for ax in axes:
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

plt.tight_layout()
plt.savefig("sensitivity_sweep.png", dpi=130, bbox_inches="tight")
print("\n📊 Saved sensitivity_sweep.png")

# -----------------------------------------------------------------------------
# Monte Carlo histogram for the baseline scenario
# -----------------------------------------------------------------------------

baseline = scenarios["Modest mixed-use (96 units)"]
mc = monte_carlo(baseline, n_iterations=2500)
sm = summarize_monte_carlo(mc)

print("\n" + "=" * 72)
print("MONTE CARLO — Modest mixed-use scenario (2,500 iterations)")
print("=" * 72)
for k, v in sm.items():
    if isinstance(v, float) and abs(v) > 1000:
        print(f"  {k:<22} ${v:>14,.0f}")
    else:
        print(f"  {k:<22} {v}")

fig2, ax = plt.subplots(figsize=(9, 4))
ax.hist(mc["net_impact"], bins=50, color="#4c72b0",
        edgecolor="white", alpha=0.85)
ax.axvline(0, color="black", linewidth=1, label="Break-even")
ax.axvline(sm["mean_net_impact"], color="#2ca02c", ls="--", label="Mean")
ax.axvline(sm["p5_worst_case"],   color="#d62728", ls="--", label="P5 (worst)")
ax.axvline(sm["p95_best_case"],   color="#ff7f0e", ls="--", label="P95 (best)")
ax.set_xlabel("Net Fiscal Impact ($/yr)")
ax.set_ylabel("Frequency")
ax.set_title("Monte Carlo Distribution — Baseline 96-unit mixed-use")
ax.legend()
for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)
ax.ticklabel_format(axis="x", style="plain")
plt.tight_layout()
plt.savefig("monte_carlo_histogram.png", dpi=130, bbox_inches="tight")
print("📊 Saved monte_carlo_histogram.png")
