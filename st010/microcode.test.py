"""The checks that need real microcode, which is why they live apart.

A skipped test contributes no coverage, so on a runner with no image every line
here would read as uncovered and fail the coverage gate for a reason that has
nothing to do with the code. Keeping them in one file lets that file sit outside
the gate while everything else stays inside it.

What they check is the part itself: that it reaches the wait its program has,
that it stays there until something is started, and that a command run on it
answers what the part answers.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from st010 import models, silicon

PRESENT = silicon.available()


@unittest.skipUnless(PRESENT, silicon.WHY_NOT_FIRMWARE)
class RealMicrocodeTest(unittest.TestCase):
    """The part itself, which only a machine holding its microcode can run."""

    def test_the_handshake_leaves_it_waiting_for_a_command(self) -> None:
        chip = silicon.Silicon()

        self.assertIn(chip.chip.registers.pc, silicon.COMMAND_LOOP["st010"])

    def test_and_it_stays_there_until_one_is_started(self) -> None:
        chip = silicon.Silicon()

        for _ in range(4096):
            chip.chip.step()

        self.assertIn(chip.chip.registers.pc, silicon.COMMAND_LOOP["st010"])

    def test_the_other_part_waits_in_its_own_place(self) -> None:
        chip = silicon.Silicon("st011")

        for _ in range(4096):
            chip.chip.step()

        self.assertIn(chip.chip.registers.pc, silicon.COMMAND_LOOP["st011"])

    def test_every_part_the_package_covers_reaches_a_wait_of_its_own(self) -> None:
        for name in models.MODELS:
            chip = silicon.Silicon(name)

            self.assertIn(chip.chip.registers.pc, silicon.COMMAND_LOOP[name], name)

    def test_a_command_runs_and_answers(self) -> None:
        chip = silicon.Silicon()
        chip.write(0x000000, 0x00)
        for at, value in enumerate((0x00, 0x01, 0x00, 0x02)):
            chip.write(0x680000 + at, value)
        chip.write(0x680000 + silicon.COMMAND_REGISTER, 0x01)

        chip.write(0x680000 + silicon.START_REGISTER, silicon.START)

        self.assertEqual(chip.read(0x680010) | (chip.read(0x680011) << 8), 0x9300)

    def test_and_the_start_byte_is_clear_once_it_has(self) -> None:
        chip = silicon.Silicon()
        chip.write(0x000000, 0x00)
        for at, value in enumerate((0x00, 0x01, 0x00, 0x02)):
            chip.write(0x680000 + at, value)
        chip.write(0x680000 + silicon.COMMAND_REGISTER, 0x01)
        chip.write(0x680000 + silicon.START_REGISTER, silicon.START)

        self.assertFalse(chip.execute & silicon.START)


if __name__ == "__main__":
    unittest.main()
