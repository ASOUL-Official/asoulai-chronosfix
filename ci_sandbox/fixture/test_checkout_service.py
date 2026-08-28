from __future__ import annotations

import unittest

from checkout_service import DEFAULT_POOL_SIZE, simulate_checkout


class CheckoutPeakTests(unittest.TestCase):
    def test_peak_traffic_stays_below_risk_gate_threshold(self):
        result = simulate_checkout(traffic_rps=300)
        self.assertGreaterEqual(DEFAULT_POOL_SIZE, 48)
        self.assertLessEqual(result.failure_rate, 0.10)

    def test_normal_traffic_remains_healthy(self):
        self.assertEqual(simulate_checkout(80).failure_rate, 0.0)


if __name__ == "__main__":
    unittest.main()
