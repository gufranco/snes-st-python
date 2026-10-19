import json
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import snesst  # noqa: E402

PRESENT = snesst.available()

BOTH = {"st010", "st011"} <= set(PRESENT)

WHY_SKIPPED = snesst.why_not() or "this machine does not hold both the st010 and st011 images"

WAITS: dict[str, list[int]] = json.loads((ROOT / "conformance" / "hardware.json").read_text())[
    "facts"
]["waitWords"]["value"]

WINDOW = 0x680000

COMMAND = WINDOW + 0x20

START = WINDOW + 0x21

START_BIT = 0x80


def pointed_at(part: Any) -> Any:
    part.write(0x000000, 0x00)
    for at, value in enumerate((0x00, 0x01, 0x00, 0x02)):
        part.write(WINDOW + at, value)
    part.write(COMMAND, 0x01)
    return part


@unittest.skipUnless(BOTH, WHY_SKIPPED)
class RealMicrocodeTest(unittest.TestCase):
    def test_the_handshake_leaves_it_waiting_for_a_command(self) -> None:
        # Arrange
        model = "st010"

        # Act
        part = snesst.Chip(model)

        # Assert
        self.assertIn(part.core.registers.pc, WAITS["st010"])

    def test_and_it_stays_there_until_one_is_started(self) -> None:
        # Arrange
        part = snesst.Chip("st010")

        # Act
        part.step(4096)

        # Assert
        self.assertIn(part.core.registers.pc, WAITS["st010"])

    def test_the_other_part_waits_in_its_own_place(self) -> None:
        # Arrange
        part = snesst.Chip("st011")

        # Act
        part.step(4096)

        # Assert
        self.assertIn(part.core.registers.pc, WAITS["st011"])

    def test_every_part_this_class_covers_reaches_a_wait_of_its_own(self) -> None:
        # Arrange
        names = sorted(WAITS)

        # Act
        found = {name: snesst.Chip(name).core.registers.pc in WAITS[name] for name in names}

        # Assert
        self.assertEqual(found, {"st010": True, "st011": True})

    def test_a_command_runs_and_answers(self) -> None:
        # Arrange
        part = pointed_at(snesst.Chip("st010"))
        part.write(START, START_BIT)

        # Act
        part.finish()

        # Assert
        self.assertEqual(part.read(WINDOW + 0x10) | (part.read(WINDOW + 0x11) << 8), 0x9300)

    def test_and_the_start_byte_is_clear_once_it_has(self) -> None:
        # Arrange
        part = pointed_at(snesst.Chip("st010"))
        part.write(START, START_BIT)

        # Act
        part.finish()

        # Assert
        self.assertEqual(part.execute & START_BIT, 0)

    def test_a_console_polling_the_start_byte_sees_the_part_busy_first(self) -> None:
        # Arrange
        part = pointed_at(snesst.Chip("st010"))

        # Act
        part.write(START, START_BIT)

        # Assert
        self.assertEqual(part.read(START) & START_BIT, START_BIT)


if __name__ == "__main__":
    unittest.main()
