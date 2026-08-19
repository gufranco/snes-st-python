import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from st010 import chip as st010

ENABLED = st010.ENABLE_BIT

COMMAND = ENABLED | st010.COMMAND_REGISTER

START = ENABLED | st010.START_REGISTER


def enabled():
    part = st010.St010()
    part.write(0x0000, 0x00)
    return part


def word(part, at, value):
    part.write(ENABLED | at, value & 0xFF)
    part.write(ENABLED | (at + 1), (value >> 8) & 0xFF)


def read_word(part, at):
    return part.read(ENABLED | at) | (part.read(ENABLED | (at + 1)) << 8)


def commanded(part, command):
    part.write(COMMAND, command)
    part.write(START, st010.START)
    return part


class EnableTest(unittest.TestCase):
    def test_a_fresh_chip_is_not_listening_to_its_registers(self):
        self.assertFalse(st010.St010().enabled)

    def test_a_write_below_the_window_is_what_starts_it_listening(self):
        part = st010.St010()

        part.write(0x0000, 0x00)

        self.assertTrue(part.enabled)

    def test_and_that_write_lands_nowhere(self):
        part = st010.St010()

        part.write(0x0000, 0xAB)

        self.assertEqual(part.memory[0], 0)

    def test_reading_below_the_window_answers_the_same_byte_every_time(self):
        self.assertEqual(st010.St010().read(0x0000), st010.NOT_ENABLED)

    def test_a_command_written_before_it_is_listening_lands_in_memory_instead(self):
        part = st010.St010()

        part.write(COMMAND, 0x07)

        self.assertEqual(part.command, 0)
        self.assertEqual(part.memory[st010.COMMAND_REGISTER], 0x07)


class RegisterTest(unittest.TestCase):
    def test_the_command_register_reads_back_what_was_written(self):
        part = enabled()

        part.write(COMMAND, 0x04)

        self.assertEqual(part.read(COMMAND), 0x04)

    def test_the_command_register_also_keeps_a_copy_in_memory(self):
        part = enabled()

        part.write(COMMAND, 0x04)

        self.assertEqual(part.memory[st010.COMMAND_REGISTER], 0x04)

    def test_the_start_register_reads_back_what_was_written(self):
        part = enabled()

        part.write(START, 0x01)

        self.assertEqual(part.read(START), 0x01)

    def test_the_start_register_does_not_keep_one(self):
        part = enabled()

        part.write(START, 0x01)

        self.assertEqual(part.memory[st010.START_REGISTER], 0)

    def test_a_start_bit_clears_both_registers_once_the_command_has_run(self):
        part = enabled()

        commanded(part, st010.MULTIPLY)

        self.assertEqual((part.command, part.execute), (0, 0))

    def test_a_command_the_chip_does_not_know_still_clears_them(self):
        part = enabled()

        commanded(part, 0x7F)

        self.assertEqual((part.command, part.execute), (0, 0))

    def test_an_ordinary_address_is_ordinary_memory(self):
        part = enabled()

        part.write(ENABLED | 0x0100, 0x5A)

        self.assertEqual(part.read(ENABLED | 0x0100), 0x5A)


class ArithmeticTest(unittest.TestCase):
    def test_a_product_lands_as_four_bytes(self):
        part = enabled()
        word(part, 0x0000, 3)
        word(part, 0x0002, 4)

        commanded(part, st010.MULTIPLY)

        self.assertEqual(read_word(part, 0x0010), 24)

    def test_a_scale_lands_as_two_long_words(self):
        part = enabled()
        word(part, 0x0000, 3)
        word(part, 0x0002, 4)
        word(part, 0x0004, 2)

        commanded(part, st010.SCALE)

        self.assertEqual(read_word(part, 0x0010), 12)
        self.assertEqual(read_word(part, 0x0014), 16)

    def test_a_distance_lands_as_one_word(self):
        part = enabled()
        word(part, 0x0000, 0x400)
        word(part, 0x0002, 0)

        commanded(part, st010.DISTANCE)

        self.assertEqual(read_word(part, 0x0010), 0x3D8)

    def test_a_rotation_lands_as_two_words(self):
        part = enabled()
        word(part, 0x0000, 0x100)
        word(part, 0x0002, 0)
        word(part, 0x0004, 0)

        commanded(part, st010.ROTATE)

        self.assertEqual(read_word(part, 0x0010), 0xFF)


class CompassCommandTest(unittest.TestCase):
    def test_the_original_height_is_copied_before_the_point_is_folded(self):
        part = enabled()
        word(part, 0x0000, 0x0100)
        word(part, 0x0002, 0x0200)

        commanded(part, st010.COMPASS)

        self.assertEqual(read_word(part, 0x0006), 0x0200)

    def test_the_folded_point_replaces_the_one_it_was_given(self):
        part = enabled()
        word(part, 0x0000, 0x0100)
        word(part, 0x0002, 0x0200)

        commanded(part, st010.COMPASS)

        self.assertLessEqual(read_word(part, 0x0000), 0x1F)

    def test_and_the_angle_lands_past_the_quadrant(self):
        part = enabled()
        word(part, 0x0000, 0x0100)
        word(part, 0x0002, 0)

        commanded(part, st010.COMPASS)

        self.assertEqual(read_word(part, 0x0010), 0xC000)


class SortCommandTest(unittest.TestCase):
    def test_the_field_comes_back_ordered_from_the_front(self):
        part = enabled()
        word(part, 0x0024, 3)
        for at, place in enumerate((1, 3, 2)):
            word(part, 0x0040 + at * 2, place)
        for at, driver in enumerate((10, 30, 20)):
            word(part, 0x0080 + at * 2, driver)

        commanded(part, st010.SORT)

        self.assertEqual([read_word(part, 0x0040 + at * 2) for at in range(3)], [3, 2, 1])

    def test_and_the_drivers_follow_their_places(self):
        part = enabled()
        word(part, 0x0024, 3)
        for at, place in enumerate((1, 3, 2)):
            word(part, 0x0040 + at * 2, place)
        for at, driver in enumerate((10, 30, 20)):
            word(part, 0x0080 + at * 2, driver)

        commanded(part, st010.SORT)

        self.assertEqual([read_word(part, 0x0080 + at * 2) for at in range(3)], [30, 20, 10])


class RasterCommandTest(unittest.TestCase):
    def test_a_screen_of_scale_lands_in_four_places(self):
        part = enabled()
        word(part, 0x0000, 0x2000)

        commanded(part, st010.RASTER)

        first = read_word(part, st010.RASTER_ACROSS)
        self.assertEqual(read_word(part, st010.RASTER_COPY), first)

    def test_the_mirrored_copy_is_the_complement_of_the_other_one(self):
        part = enabled()
        word(part, 0x0000, 0x2000)

        commanded(part, st010.RASTER)

        down = read_word(part, st010.RASTER_DOWN)
        self.assertEqual(read_word(part, st010.RASTER_MIRRORED), ~down & 0xFFFF)

    def test_the_angle_is_shifted_down_a_byte_once_the_screen_is_built(self):
        part = enabled()
        word(part, 0x0000, 0x2000)

        commanded(part, st010.RASTER)

        self.assertEqual(read_word(part, 0x0000), 0x0020)


class NavigateCommandTest(unittest.TestCase):
    def steering(self):
        part = enabled()
        word(part, 0x00C0, 0x0100)
        word(part, 0x00C2, 0x0100)
        word(part, 0x00C4, 0x0000)
        word(part, 0x00C6, 0x0080)
        word(part, 0x00C8, 0x0000)
        word(part, 0x00CA, 0x0080)
        word(part, 0x00CC, 0xA000)
        word(part, 0x00D4, 0x0100)
        word(part, 0x00D6, 0x0040)
        word(part, 0x00D8, 0x0800)
        return part

    def test_steering_leaves_a_heading_that_is_already_right_alone(self):
        part = self.steering()

        commanded(part, st010.NAVIGATE)

        self.assertEqual(read_word(part, 0x00CC), 0xA000)

    def test_and_moves_one_that_is_not(self):
        part = self.steering()
        word(part, 0x00CC, 0x0000)

        commanded(part, st010.NAVIGATE)

        self.assertNotEqual(read_word(part, 0x00CC), 0)

    def test_and_writes_how_far_off_the_target_still_is(self):
        part = self.steering()

        commanded(part, st010.NAVIGATE)

        self.assertEqual(read_word(part, 0x00D0), 0x0080)

    def test_the_position_moves_with_it(self):
        part = self.steering()

        commanded(part, st010.NAVIGATE)

        self.assertNotEqual(read_word(part, 0x00C4), 0x0000)


class PrintingTest(unittest.TestCase):
    def test_a_chip_prints_as_its_command_and_whether_it_is_listening(self):
        printed = repr(st010.St010())

        self.assertIn("0x00", printed)
        self.assertIn("False", printed)


class MemoryTest(unittest.TestCase):
    def test_a_chip_can_be_given_the_memory_it_starts_with(self):
        part = st010.St010(memory=bytes([0xAA]) * st010.MEMORY_BYTES)

        self.assertEqual(part.read(ENABLED | 0x0500), 0xAA)

    def test_and_one_that_is_not_given_any_starts_cleared(self):
        self.assertEqual(len(st010.St010().memory), st010.MEMORY_BYTES)


if __name__ == "__main__":
    unittest.main()
