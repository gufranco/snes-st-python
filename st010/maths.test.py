import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from st010 import maths


class CompassTest(unittest.TestCase):
    """Which way a point lies, folded into one octant pair and put back."""

    def test_a_point_ahead_and_to_the_right_needs_no_folding(self):
        found = maths.compass(0x100, 0x100)

        self.assertEqual(found.quadrant, 0x0000)

    def test_a_point_due_east_answers_a_quarter_turn_back(self):
        found = maths.compass(0x100, 0)

        self.assertEqual(found.theta, -0x4000)

    def test_a_point_due_north_answers_half_a_turn_back(self):
        found = maths.compass(0, 0x100)

        self.assertEqual(found.theta, -0x8000)

    def test_a_point_due_west_reads_as_three_quarters(self):
        found = maths.compass(-0x100, 0x10)

        self.assertEqual(found.quadrant, -0x4000)

    def test_a_point_behind_and_to_the_left_reads_as_a_half(self):
        found = maths.compass(-0x100, -0x100)

        self.assertEqual(found.quadrant, -0x8000)

    def test_the_folded_point_is_brought_inside_the_lookup(self):
        found = maths.compass(0x4000, 0x2000)

        self.assertLessEqual(found.across, 0x1F)
        self.assertLessEqual(found.down, 0x1F)

    def test_a_point_at_the_origin_folds_to_nothing(self):
        found = maths.compass(0, 0)

        self.assertEqual((found.across, found.down), (0, 0))

    def test_a_point_straight_down_is_given_a_quadrant_of_its_own(self):
        found = maths.compass(0, -0x100)

        self.assertEqual(found.quadrant, 0x4000)

    def test_the_angle_turns_with_the_point(self):
        east = maths.compass(0x100, 0).theta
        north = maths.compass(0, 0x100).theta

        self.assertNotEqual(east, north)

    def test_a_point_that_is_already_small_is_not_folded(self):
        found = maths.compass(3, 4)

        self.assertEqual((found.across, found.down), (3, 4))


class ScaleTest(unittest.TestCase):
    def test_scaling_by_nothing_is_nothing(self):
        self.assertEqual(maths.scale(0, 0x100, 0x200), (0, 0))

    def test_scaling_doubles_the_product(self):
        self.assertEqual(maths.scale(2, 3, 4), (12, 16))

    def test_a_negative_multiplier_turns_the_point_around(self):
        self.assertEqual(maths.scale(-1, 3, 4), (-6, -8))


class MultiplyTest(unittest.TestCase):
    def test_a_product_is_doubled_before_it_is_answered(self):
        self.assertEqual(maths.multiply(3, 4), 24)

    def test_a_negative_multiplicand_gives_a_negative_product(self):
        self.assertEqual(maths.multiply(-3, 4), -24)

    def test_the_widest_product_wraps_rather_than_growing(self):
        self.assertEqual(maths.multiply(-0x8000, -0x8000), -0x80000000)


class RotateTest(unittest.TestCase):
    def test_turning_by_nothing_loses_a_part_in_thirty_two_thousand(self):
        self.assertEqual(maths.rotate(0, 0x100, 0x200), (0xFF, 0x1FF))

    def test_turning_by_a_quarter_swaps_the_axes(self):
        across, down = maths.rotate(0x4000, 0x100, 0)

        self.assertEqual(across, 0)
        self.assertEqual(down, -0xFF)


class DistanceTest(unittest.TestCase):
    """How far away something is, from a straight line fit rather than a root."""

    def test_the_distance_to_the_origin_is_nothing(self):
        self.assertEqual(maths.distance(0, 0), 0)

    def test_a_point_on_an_axis_is_as_far_as_its_coordinate(self):
        self.assertEqual(maths.distance(0x400, 0), 0x3D8)

    def test_the_fit_is_the_same_whichever_axis_is_longer(self):
        self.assertEqual(maths.distance(0x300, 0x100), maths.distance(0x100, 0x300))

    def test_a_negative_coordinate_is_as_far_as_a_positive_one(self):
        self.assertEqual(maths.distance(-0x300, 0x100), maths.distance(0x300, 0x100))

    def test_a_diagonal_is_further_than_either_side(self):
        self.assertGreater(maths.distance(0x200, 0x200), maths.distance(0x200, 0))


class SortTest(unittest.TestCase):
    """The race order, sorted downwards, carrying the drivers with it."""

    def test_a_field_of_one_is_already_in_order(self):
        places = [5]
        drivers = [9]

        maths.sort_drivers(1, places, drivers)

        self.assertEqual((places, drivers), ([5], [9]))

    def test_a_field_is_ordered_from_the_front(self):
        places = [1, 3, 2]
        drivers = [10, 30, 20]

        maths.sort_drivers(3, places, drivers)

        self.assertEqual(places, [3, 2, 1])

    def test_and_the_drivers_follow_their_places(self):
        places = [1, 3, 2]
        drivers = [10, 30, 20]

        maths.sort_drivers(3, places, drivers)

        self.assertEqual(drivers, [30, 20, 10])

    def test_a_field_of_none_is_left_alone(self):
        places = [4, 1]

        maths.sort_drivers(0, places, [0, 0])

        self.assertEqual(places, [4, 1])


class RasterTest(unittest.TestCase):
    def test_a_raster_has_a_line_for_every_line_of_the_screen(self):
        found = maths.raster(0)

        self.assertEqual(len(found.across), maths.RASTER_LINES)

    def test_at_no_angle_the_whole_scale_is_across(self):
        found = maths.raster(0)

        self.assertEqual(found.down[0], 0)

    def test_and_at_a_quarter_turn_it_is_all_down(self):
        found = maths.raster(0x4000)

        self.assertEqual(found.across[0], 0)

    def test_the_mirrored_line_is_the_complement_of_the_other(self):
        found = maths.raster(0x2000)

        self.assertEqual(found.mirrored[0], ~found.down[0] & 0xFFFF)

    def test_a_line_that_came_out_at_nothing_is_not_complemented(self):
        found = maths.raster(0)

        self.assertEqual(found.mirrored[0], 0)


class NavigationTest(unittest.TestCase):
    """Where a driver steers next, which is the only command that carries state."""

    def start(self, **changes):
        state = maths.Navigation(
            max_x=0x0100,
            max_y=0x0100,
            x=0x0080_0000,
            y=0x0080_0000,
            theta=0,
            radius=0x0100,
            compass=0,
            flags=0,
        )
        for name, value in changes.items():
            setattr(state, name, value)
        return state

    def test_steering_towards_a_target_turns_towards_it(self):
        state = self.start()

        maths.navigate(state, increment=0x10, max_radius=0x0800, new_max_x=0, new_max_y=0)

        self.assertNotEqual(state.theta, 0)

    def test_a_driver_pointed_at_its_target_speeds_up(self):
        state = self.start(theta=-0x6000)

        maths.navigate(state, increment=0x40, max_radius=0x0800, new_max_x=0, new_max_y=0)

        self.assertEqual(state.radius, 0x0140)

    def test_and_one_pointed_at_it_already_stops_speeding_up_at_the_limit(self):
        state = self.start(theta=-0x6000, radius=0x07F0)

        maths.navigate(state, increment=0x40, max_radius=0x0800, new_max_x=0, new_max_y=0)

        self.assertEqual(state.radius, 0x0800)

    def test_and_one_pointed_away_from_it_slows_down(self):
        state = self.start(theta=0x4000, max_x=-0x0400, max_y=-0x0400, radius=0x0700)

        maths.navigate(state, increment=0x10, max_radius=0x0800, new_max_x=0, new_max_y=0)

        self.assertLess(state.radius, 0x0700)

    def test_the_position_stays_inside_the_range_the_chip_carries(self):
        state = self.start()

        maths.navigate(state, increment=0x40, max_radius=0x0800, new_max_x=0, new_max_y=0)

        self.assertLessEqual(state.x, 0x1FFFFFFF)
        self.assertLessEqual(state.y, 0x1FFFFFFF)

    def test_arriving_takes_the_next_target_and_says_so(self):
        state = self.start(max_x=0x00C0, max_y=0x0084)

        maths.navigate(state, increment=0x10, max_radius=0x0800, new_max_x=0x0200, new_max_y=0x0300)

        self.assertEqual(state.max_x, 0x0200)
        self.assertEqual(state.flags & 0x0008, 0x0008)

    def test_and_the_next_target_carries_which_way_the_track_turns(self):
        state = self.start(max_x=0x00C0, max_y=0x0084)

        maths.navigate(
            state, increment=0x10, max_radius=0x0800, new_max_x=0x0200, new_max_y=-0x0300
        )

        self.assertEqual(state.compass, -1)

    def test_a_target_that_is_still_far_off_is_kept(self):
        state = self.start(max_x=0x4000, max_y=0x4000)

        maths.navigate(state, increment=0x10, max_radius=0x0800, new_max_x=0x0200, new_max_y=0x0300)

        self.assertEqual(state.max_x, 0x4000)

    def test_which_way_the_track_turns_decides_which_way_arriving_is_measured(self):
        wide = self.start(max_x=0x00C0, max_y=0x0084, compass=0)
        tall = self.start(max_x=0x00C0, max_y=0x0084, compass=-1)

        maths.navigate(wide, increment=0x10, max_radius=0x0800, new_max_x=1, new_max_y=1)
        maths.navigate(tall, increment=0x10, max_radius=0x0800, new_max_x=1, new_max_y=1)

        self.assertNotEqual(wide.flags & 0x0008, tall.flags & 0x0008)


if __name__ == "__main__":
    unittest.main()
