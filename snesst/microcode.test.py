import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from snesst import chip

PRESENT = chip.available()


@unittest.skipUnless(PRESENT, chip.WHY_NOT_FIRMWARE)
class RealMicrocodeTest(unittest.TestCase):
    def test_the_handshake_leaves_it_waiting_for_a_command(self) -> None:
        part = chip.Chip("st010")

        self.assertIn(part.core.registers.pc, chip.COMMAND_LOOP["st010"])

    def test_and_it_stays_there_until_one_is_started(self) -> None:
        part = chip.Chip("st010")

        for _ in range(4096):
            part.core.step()

        self.assertIn(part.core.registers.pc, chip.COMMAND_LOOP["st010"])

    def test_the_other_part_waits_in_its_own_place(self) -> None:
        part = chip.Chip("st011")

        for _ in range(4096):
            part.core.step()

        self.assertIn(part.core.registers.pc, chip.COMMAND_LOOP["st011"])

    def test_every_part_this_class_covers_reaches_a_wait_of_its_own(self) -> None:
        for name in chip.COMMAND_LOOP:
            part = chip.Chip(name)

            self.assertIn(part.core.registers.pc, chip.COMMAND_LOOP[name], name)

    def test_a_command_runs_and_answers(self) -> None:
        part = chip.Chip("st010")
        part.write(0x000000, 0x00)
        for at, value in enumerate((0x00, 0x01, 0x00, 0x02)):
            part.write(0x680000 + at, value)
        part.write(0x680000 + chip.COMMAND_REGISTER, 0x01)

        part.write(0x680000 + chip.START_REGISTER, chip.START)

        self.assertEqual(part.read(0x680010) | (part.read(0x680011) << 8), 0x9300)

    def test_and_the_start_byte_is_clear_once_it_has(self) -> None:
        part = chip.Chip("st010")
        part.write(0x000000, 0x00)
        for at, value in enumerate((0x00, 0x01, 0x00, 0x02)):
            part.write(0x680000 + at, value)
        part.write(0x680000 + chip.COMMAND_REGISTER, 0x01)
        part.write(0x680000 + chip.START_REGISTER, chip.START)

        self.assertFalse(part.execute & chip.START)


if __name__ == "__main__":
    unittest.main()
