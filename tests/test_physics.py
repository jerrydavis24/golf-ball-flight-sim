"""Tests for the flight model. Run with:  python -m unittest discover tests"""

import unittest

from golfsim.clubs import CLUB_PRESETS, TOUR_CARRY_YD
from golfsim.physics import Conditions, Shot, air_density, simulate

DRIVER = CLUB_PRESETS["driver"]


class TestAtmosphere(unittest.TestCase):
    def test_sea_level_density(self):
        self.assertAlmostEqual(air_density(0, 15), 1.225, places=2)

    def test_density_drops_with_altitude(self):
        self.assertLess(air_density(1600), air_density(0))


class TestValidation(unittest.TestCase):
    def test_carry_matches_tour_averages_within_8_percent(self):
        for club, shot in CLUB_PRESETS.items():
            with self.subTest(club=club):
                carry = simulate(shot).carry_yd
                target = TOUR_CARRY_YD[club]
                self.assertLess(abs(carry - target) / target, 0.08,
                                f"{club}: {carry:.1f} vs {target}")

    def test_longer_clubs_carry_farther(self):
        order = ["driver", "3-wood", "5-iron", "7-iron", "9-iron", "pw"]
        carries = [simulate(CLUB_PRESETS[c]).carry_yd for c in order]
        self.assertEqual(carries, sorted(carries, reverse=True))


class TestPhysicsBehavior(unittest.TestCase):
    def test_straight_shot_stays_on_line(self):
        self.assertAlmostEqual(simulate(DRIVER).offline_yd, 0.0, places=6)

    def test_positive_side_spin_curves_right(self):
        fade = Shot(171, 10.4, 2545, side_spin_rpm=800)
        draw = Shot(171, 10.4, 2545, side_spin_rpm=-800)
        self.assertGreater(simulate(fade).offline_yd, 5)
        self.assertLess(simulate(draw).offline_yd, -5)

    def test_altitude_adds_distance(self):
        sea = simulate(DRIVER).carry_yd
        abq = simulate(DRIVER, Conditions(altitude_m=1600)).carry_yd
        self.assertGreater(abq, sea + 5)

    def test_headwind_shortens_and_tailwind_lengthens(self):
        calm = simulate(DRIVER).carry_yd
        head = simulate(DRIVER, Conditions(wind_speed_mph=15, wind_from_deg=0)).carry_yd
        tail = simulate(DRIVER, Conditions(wind_speed_mph=15, wind_from_deg=180)).carry_yd
        self.assertLess(head, calm)
        self.assertGreater(tail, calm)

    def test_crosswind_from_right_pushes_ball_left(self):
        r = simulate(DRIVER, Conditions(wind_speed_mph=15, wind_from_deg=90))
        self.assertLess(r.offline_yd, 0)

    def test_no_spin_flies_lower_than_with_spin(self):
        knuckle = simulate(Shot(171, 10.4, 0)).apex_ft
        self.assertLess(knuckle, simulate(DRIVER).apex_ft)

    def test_ball_lands_at_ground_level(self):
        r = simulate(DRIVER)
        self.assertAlmostEqual(r.positions[-1, 1], 0.0, places=6)

    def test_result_is_stable_across_timesteps(self):
        coarse = simulate(DRIVER, dt=0.01).carry_yd
        fine = simulate(DRIVER, dt=0.001).carry_yd
        self.assertAlmostEqual(coarse, fine, delta=0.5)


if __name__ == "__main__":
    unittest.main()
