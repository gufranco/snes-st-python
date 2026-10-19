from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import snesst  # noqa: E402

PROGRAM_BYTES = 131072
DATA_BYTES = 32768

READY = 0x80

BRANCH_SEQUENTIAL = 2
BRANCH_NONSEQUENTIAL = 1
BRANCH_CYCLES = BRANCH_SEQUENTIAL + BRANCH_NONSEQUENTIAL

TIMER_LOW = 0x20
TIMER_MIDDLE = 0x24
TIMER_HIGH = 0x28
TIMER_COMMIT = 0x2C


def arm(*words: int) -> bytes:
    body = b"".join(word.to_bytes(4, "little") for word in words)
    program = body.ljust(PROGRAM_BYTES, b"\x00")
    return program + bytes(DATA_BYTES)


IDLE = arm(0xEAFFFFFE)


def a_part(image: bytes = IDLE) -> snesst.ST018:
    return snesst.ST018(image=image)


class TimerTest(unittest.TestCase):
    def test_three_latch_bytes_are_committed_as_one_twenty_four_bit_count(self) -> None:
        # Arrange
        found = a_part()
        found.drive(TIMER_LOW, 0x56)
        found.drive(TIMER_MIDDLE, 0x34)
        found.drive(TIMER_HIGH, 0x12)

        # Act
        found.drive(TIMER_COMMIT, 0x00)

        # Assert
        self.assertEqual((found.latch, found.timer), (0x123456, 0x123456))

    def test_a_latch_byte_alone_does_not_reach_the_count(self) -> None:
        # Arrange
        found = a_part()

        # Act
        found.drive(TIMER_LOW, 0x56)

        # Assert
        self.assertEqual((found.latch, found.timer), (0x56, 0))

    def test_rewriting_a_latch_byte_replaces_only_that_byte(self) -> None:
        # Arrange
        found = a_part()
        found.drive(TIMER_LOW, 0x56)
        found.drive(TIMER_MIDDLE, 0x34)

        # Act
        found.drive(TIMER_LOW, 0x9A)

        # Assert
        self.assertEqual(found.latch, 0x349A)

    def test_the_count_falls_by_one_for_every_cycle_the_arm_spends(self) -> None:
        # Arrange
        found = a_part()
        found.drive(TIMER_LOW, 0x10)
        found.drive(TIMER_COMMIT, 0x00)

        # Act
        found.step(1)

        # Assert
        self.assertEqual(found.timer, 0x10 - BRANCH_CYCLES)

    def test_and_stops_at_zero_rather_than_wrapping(self) -> None:
        # Arrange
        found = a_part()
        found.drive(TIMER_LOW, 0x02)
        found.drive(TIMER_COMMIT, 0x00)

        # Act
        found.step(1)

        # Assert
        self.assertEqual(found.timer, 0)

    def test_driving_an_offset_the_firmware_never_writes_changes_nothing(self) -> None:
        # Arrange
        found = a_part()

        # Act
        found.drive(0x04, 0xFF)

        # Assert
        self.assertEqual((found.latch, found.timer, found.status()), (0, 0, READY))

    def test_a_reset_empties_the_latch_and_the_count(self) -> None:
        # Arrange
        found = a_part()
        found.drive(TIMER_LOW, 0x40)
        found.drive(TIMER_COMMIT, 0x00)

        # Act
        found.reset()

        # Assert
        self.assertEqual((found.latch, found.timer), (0, 0))


class TimingTest(unittest.TestCase):
    def test_a_branch_costs_the_cycles_the_arm_spends_on_its_bus(self) -> None:
        # Arrange
        found = a_part()
        before = found.cycles

        # Act
        found.step(1)

        # Assert
        self.assertEqual(found.cycles - before, BRANCH_CYCLES)

    def test_the_cycles_are_kept_in_the_manufacturer_s_own_terms(self) -> None:
        # Arrange
        found = a_part()
        before = (found.tally.s, found.tally.n)

        # Act
        found.step(1)

        # Assert
        self.assertEqual(
            (found.tally.s - before[0], found.tally.n - before[1]),
            (BRANCH_SEQUENTIAL, BRANCH_NONSEQUENTIAL),
        )

    def test_a_budget_is_spent_in_whole_instructions_and_overshoots(self) -> None:
        # Arrange
        found = a_part()

        # Act
        spent = found.run_for(BRANCH_CYCLES * 2 + 1)

        # Assert
        self.assertEqual((spent, found.steps), (BRANCH_CYCLES * 3, 3))

    def test_a_budget_of_nothing_spends_nothing(self) -> None:
        # Arrange
        found = a_part()

        # Act
        spent = found.run_for(0)

        # Assert
        self.assertEqual(spent, 0)


if __name__ == "__main__":
    unittest.main()
