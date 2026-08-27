"""That the third part answers the way the two artifacts say it does.

Every check here runs a program this project wrote against the modelled part.
The real firmware is not carried and is not needed: what is being checked is the
interface, which was read off the cartridge and off the firmware, and an ARM
program of four instructions exercises it exactly as 160 kilobytes would.

The one thing a made-up program cannot show is that the real firmware answers.
That belongs to the doctor rather than here: it needs an image nobody can carry,
so a check for it would report success by skipping on every machine that has
none, which is the failure the doctor exists to prevent.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from snesst import errors, firmware, st018  # noqa: E402


def arm(*words: int) -> bytes:
    """A program at the reset vector, padded to the shape an image has."""
    body = b"".join(word.to_bytes(4, "little") for word in words)
    program = body.ljust(st018.PROGRAM_BYTES, b"\x00")
    return program + bytes(st018.DATA_BYTES)


IDLE = arm(0xEAFFFFFE)
"""Branch to itself. The part is powered and doing nothing, which is what most
of these checks want underneath them.
"""

ANSWER = arm(
    0xE3A0B101,
    0xE5DB0010,
    0xE5CB0000,
    0xEAFFFFFE,
)
"""Read the byte the console sent and write it straight back.

`mov R11, #0x40000000`, `ldrb R0, [R11, #0x10]`, `strb R0, [R11]`, then spin.
Four instructions is the whole of the mailbox, which is the point.
"""


def _identity() -> firmware.Identity:
    return firmware.Identity(
        part="st018",
        processor="arm60",
        revision="ST018",
        program_bytes=st018.PROGRAM_BYTES,
        data_bytes=st018.DATA_BYTES,
    )


class Fixture(unittest.TestCase):
    def part(self, image: bytes = IDLE) -> st018.ST018:
        return st018.ST018(image=image)


class BuildingTest(Fixture):
    def test_a_part_can_be_built_from_an_image_in_hand(self) -> None:
        found = self.part()

        self.assertEqual(found.part, "st018")

    def test_an_image_of_the_wrong_length_is_refused(self) -> None:
        with self.assertRaises(errors.WrongShape) as raised:
            st018.ST018(image=b"\x00" * 16)

        self.assertIn("163840", str(raised.exception))

    def test_a_reset_hands_the_part_back(self) -> None:
        found = self.part()

        self.assertIs(found.reset(), found)

    def test_a_part_says_which_model_it_is(self) -> None:
        found = self.part()

        self.assertEqual(found.model, "st018")

    def test_a_part_says_which_processor_it_runs(self) -> None:
        found = self.part()

        self.assertEqual(found.processor, "arm60")

    def test_a_part_with_no_image_anywhere_says_so(self) -> None:
        with self.assertRaises(errors.NoFirmware) as raised:
            st018.ST018(images=iter(()))

        self.assertIn("st018", str(raised.exception))

    def test_an_image_the_search_turns_up_is_the_one_that_runs(self) -> None:
        with tempfile.TemporaryDirectory() as hold:
            where = Path(hold) / "st018.bin"
            where.write_bytes(IDLE)

            found = st018.ST018(images=iter([(_identity(), where)]))

        self.assertEqual(found.identity.revision, "ST018")

    def test_an_image_for_another_part_is_passed_over(self) -> None:
        with tempfile.TemporaryDirectory() as hold:
            where = Path(hold) / "st010.bin"
            where.write_bytes(IDLE)
            other = firmware.Identity(part="st010", processor="upd96050", revision="ST010")

            with self.assertRaises(errors.NoFirmware):
                st018.ST018(images=iter([(other, where)]))

    def test_a_core_that_is_not_beside_this_package_is_reported(self) -> None:
        """An empty directory is what a clone without --recurse-submodules leaves."""
        with tempfile.TemporaryDirectory() as hold, self.assertRaises(errors.NoFirmware) as raised:
            st018.ST018(image=IDLE, processor=hold)

        self.assertIn("arm6-python", str(raised.exception))

    def test_the_core_is_looked_for_rather_than_imported_hopefully(self) -> None:
        with tempfile.TemporaryDirectory() as hold:
            found = st018._processor(Path(hold))

        self.assertIsNone(found)


class MemoryTest(Fixture):
    def test_the_program_is_read_where_the_part_fetches_it(self) -> None:
        found = self.part()

        self.assertEqual(found.stores.read_word(0), 0xEAFFFFFE)

    def test_the_data_rom_is_read_where_the_firmware_names_it(self) -> None:
        image = bytearray(IDLE)
        image[st018.PROGRAM_BYTES] = 0x5A
        found = st018.ST018(image=bytes(image))

        self.assertEqual(found.stores.read_byte(st018.DATA_ROM), 0x5A)

    def test_neither_rom_can_be_written(self) -> None:
        found = self.part()

        found.stores.write_byte(0, 0xFF)
        found.stores.write_byte(st018.DATA_ROM, 0xFF)

        self.assertEqual(
            (found.stores.read_byte(0), found.stores.read_byte(st018.DATA_ROM)), (0xFE, 0x00)
        )

    def test_the_work_ram_keeps_what_is_put_in_it(self) -> None:
        found = self.part()

        found.stores.write_word(st018.WORK_RAM, 0x12345678)

        self.assertEqual(found.stores.read_word(st018.WORK_RAM), 0x12345678)

    def test_the_work_ram_wraps_at_the_size_the_stack_pointer_implies(self) -> None:
        found = self.part()

        found.stores.write_byte(st018.WORK_RAM, 0x99)

        self.assertEqual(found.stores.read_byte(st018.WORK_RAM + st018.WORK_RAM_BYTES), 0x99)

    def test_an_address_in_no_region_reads_as_nothing(self) -> None:
        found = self.part()

        self.assertEqual(found.stores.read_word(0x20000000), 0)

    def test_and_writing_there_changes_nothing(self) -> None:
        found = self.part()

        found.stores.write_word(0x20000000, 0xFFFFFFFF)

        self.assertEqual(found.stores.read_word(0x20000000), 0)


class ConsoleSideTest(Fixture):
    def test_the_status_says_the_part_is_up_once_it_has_been_reset(self) -> None:
        found = self.part()

        self.assertTrue(found.read(st018.STATUS) & st018.READY)

    def test_a_part_that_has_not_been_reset_is_not_up(self) -> None:
        found = self.part().reset()
        found.up = False

        self.assertFalse(found.read(st018.STATUS) & st018.READY)

    def test_writing_the_data_port_says_a_byte_is_waiting_for_the_part(self) -> None:
        found = self.part()

        found.write(st018.TO_PART, 0xF1)

        self.assertTrue(found.read(st018.STATUS) & st018.SENT)

    def test_the_part_reading_it_clears_that(self) -> None:
        found = self.part(ANSWER)
        found.write(st018.TO_PART, 0xF1)

        found.step(2)

        self.assertFalse(found.read(st018.STATUS) & st018.SENT)

    def test_a_byte_the_part_writes_is_offered_to_the_console(self) -> None:
        found = self.part(ANSWER)
        found.write(st018.TO_PART, 0x42)

        found.step(3)

        self.assertTrue(found.read(st018.STATUS) & st018.WAITING)

    def test_and_reading_it_gives_the_byte_and_clears_the_flag(self) -> None:
        found = self.part(ANSWER)
        found.write(st018.TO_PART, 0x42)
        found.step(3)

        byte = found.read(st018.FROM_PART)

        self.assertEqual((byte, bool(found.read(st018.STATUS) & st018.WAITING)), (0x42, False))

    def test_reading_the_data_port_with_nothing_offered_gives_nothing(self) -> None:
        found = self.part()

        self.assertEqual(found.read(st018.FROM_PART), 0)

    def test_a_reset_pulse_starts_the_part_over(self) -> None:
        found = self.part(ANSWER)
        found.write(st018.TO_PART, 0x42)
        found.step(3)

        found.write(st018.STATUS, 0)
        found.write(st018.STATUS, 1)

        self.assertEqual(found.read(st018.STATUS) & (st018.WAITING | st018.SENT), 0)

    def test_an_address_the_cartridge_never_touches_is_refused(self) -> None:
        """Nothing establishes what the other five bytes of the window do.

        The cartridge reads and writes three addresses and no others, so a fourth
        is a question this project cannot answer from either artifact. Answering
        it anyway would be inventing a register.
        """
        found = self.part()

        with self.assertRaises(errors.UnknownPort):
            found.read(0x3801)

    def test_and_so_is_writing_to_one(self) -> None:
        found = self.part()

        with self.assertRaises(errors.UnknownPort):
            found.write(0x3806, 0)

    def test_writing_the_port_the_part_writes_is_refused(self) -> None:
        found = self.part()

        with self.assertRaises(errors.UnknownPort):
            found.write(st018.FROM_PART, 0)


class PartSideTest(Fixture):
    """The three offsets the firmware reaches, driven from inside the program."""

    def test_reading_the_incoming_port_with_nothing_sent_gives_nothing(self) -> None:
        found = self.part()

        self.assertEqual(found.port(st018.TO_PART_PORT), 0)

    def test_reading_the_status_from_inside_gives_the_same_byte(self) -> None:
        found = self.part()

        self.assertEqual(found.port(st018.STATUS_PORT), found.read(st018.STATUS))

    def test_an_offset_the_firmware_never_reaches_reads_as_nothing(self) -> None:
        found = self.part()

        self.assertEqual(found.port(0x04), 0)

    def test_the_bytes_the_firmware_writes_once_at_boot_are_kept_and_nothing_else(self) -> None:
        """It loads three of them and commits at 0x2C. What sits behind that is
        somebody else's reading, so this keeps the write and models no timer.
        """
        found = self.part()

        found.drive(st018.STATUS_PORT, 0x02)
        found.drive(0x24, 0xFF)

        self.assertEqual(found.timer, 0x02)


class ExchangeTest(Fixture):
    def test_a_byte_goes_in_and_comes_back(self) -> None:
        found = self.part(ANSWER)

        found.write(st018.TO_PART, 0xAB)
        found.step(4)

        self.assertEqual(found.read(st018.FROM_PART), 0xAB)

    def test_the_part_counts_what_it_has_run(self) -> None:
        found = self.part()

        found.step(5)

        self.assertEqual(found.steps, 5)


if __name__ == "__main__":
    unittest.main()
