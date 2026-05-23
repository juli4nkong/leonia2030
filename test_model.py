"""
test_model.py
-------------
Minimal sanity tests for the Leonia 2030 fiscal model.
Run with:   python3 -m unittest test_model.py
"""

import unittest

from fiscal_model import (
    Development,
    calculate_assessed_value,
    calculate_annual_tax_revenue,
    calculate_new_pupils,
    calculate_pm_peak_trips,
    fiscal_impact,
    monte_carlo,
)
import leonia_constants as L


class TestModel(unittest.TestCase):

    def test_empty_development_zero_revenue(self):
        dev = Development()
        self.assertEqual(calculate_annual_tax_revenue(dev), 0)
        self.assertEqual(calculate_new_pupils(dev), 0)

    def test_assessed_value_proportional_to_market(self):
        small  = Development(one_bedroom=10)
        big    = Development(one_bedroom=20)
        # Doubling units should ~double assessed value
        self.assertAlmostEqual(
            calculate_assessed_value(big) / calculate_assessed_value(small),
            2.0, places=2)

    def test_three_bedroom_generates_more_pupils_than_studio(self):
        studios = Development(studios=100)
        three   = Development(three_bedroom=100)
        self.assertGreater(
            calculate_new_pupils(three),
            calculate_new_pupils(studios))

    def test_traffic_increases_corridor_load(self):
        baseline = L.GRAND_AVE_PM_BASELINE_TRIPS
        dev = Development(one_bedroom=50, retail_sf=5000)
        t = calculate_pm_peak_trips(dev)
        self.assertGreater(t["projected_corridor"], baseline)

    def test_fiscal_impact_keys(self):
        dev = Development(one_bedroom=30, retail_sf=2000)
        result = fiscal_impact(dev)
        for k in ("assessed_value", "annual_tax_revenue", "new_pupils",
                  "new_residents", "annual_school_cost",
                  "annual_municipal_cost", "annual_total_cost",
                  "net_fiscal_impact", "revenue_to_cost_ratio",
                  "break_even", "traffic"):
            self.assertIn(k, result)

    def test_monte_carlo_runs_and_is_reproducible(self):
        dev = Development(one_bedroom=40, retail_sf=3000)
        r1 = monte_carlo(dev, n_iterations=200, seed=7)
        r2 = monte_carlo(dev, n_iterations=200, seed=7)
        self.assertEqual(len(r1["net_impact"]), 200)
        # Same seed → same results
        self.assertEqual(r1["net_impact"][0], r2["net_impact"][0])

    def test_equalization_ratio_makes_sense(self):
        # Should be between 0 and 1; Leonia ≈ 0.63
        self.assertGreater(L.EQUALIZATION_RATIO, 0.4)
        self.assertLess(L.EQUALIZATION_RATIO, 0.95)

    def test_pilot_reduces_revenue_vs_standard_tax(self):
        """A PILOT should always produce LESS revenue than standard tax for
        a typical Bergen Co. mid-rise — that's the entire point politically."""
        standard = Development(one_bedroom=50, two_bedroom=30, retail_sf=5000)
        pilot    = Development(one_bedroom=50, two_bedroom=30, retail_sf=5000,
                               pilot_active=True)
        self.assertLess(
            calculate_annual_tax_revenue(pilot),
            calculate_annual_tax_revenue(standard))

    def test_los_thresholds_ordered(self):
        # LOS C ceiling must be below LOS E (gridlock)
        self.assertLess(L.GRAND_AVE_LOS_C_CAPACITY, L.GRAND_AVE_LOS_E_CAPACITY)
        self.assertGreater(L.GRAND_AVE_LOS_C_CAPACITY,
                           L.GRAND_AVE_PM_BASELINE_TRIPS)

    def test_monte_carlo_summary_stats_sensible(self):
        from fiscal_model import summarize_monte_carlo
        dev = Development(one_bedroom=40, two_bedroom=20, retail_sf=4000)
        results = monte_carlo(dev, n_iterations=500, seed=1)
        summary = summarize_monte_carlo(results)
        # P5 should be lower than mean, P95 should be higher
        self.assertLess(summary["p5_worst_case"], summary["mean_net_impact"])
        self.assertGreater(summary["p95_best_case"], summary["mean_net_impact"])
        # prob_positive is a probability
        self.assertGreaterEqual(summary["prob_positive"], 0.0)
        self.assertLessEqual(summary["prob_positive"], 1.0)


if __name__ == "__main__":
    unittest.main()
