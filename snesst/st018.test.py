from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import snesst  # noqa: E402
from snesst import firmware  # noqa: E402

PROGRAM_BYTES = 131072
DATA_BYTES = 32768
DATA_ROM = 0xA0000000
PORT_REGION = 0x40000000
WORK_RAM = 0xE0000000
WORK_RAM_BYTES = 16 * 1024
NO_REGION = 0x20000000

FROM_PART = 0x3800
TO_PART = 0x3802
STATUS = 0x3804

TO_PART_PORT = 0x10
STATUS_PORT = 0x20

WAITING = 0x01
SENT = 0x08
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

ANSWER = arm(
    0xE3A0B101,
    0xE5DB0010,
    0xE5CB0000,
    0xEAFFFFFE,
)


def an_identity() -> firmware.Identity:
    return firmware.Identity(
        part="st018",
        processor="arm60",
        revision="ST018",
        program_bytes=PROGRAM_BYTES,
        data_bytes=DATA_BYTES,
    )


def a_part(image: bytes = IDLE) -> snesst.ST018:
    return snesst.ST018(image=image)


class BuildingTest(unittest.TestCase):
    def test_a_part_can_be_built_from_an_image_in_hand(self) -> None:
        # Arrange
        image = IDLE

        # Act
        found = snesst.Chip("st018", image=image)

        # Assert
        self.assertEqual((type(found), found.part), (snesst.ST018, "st018"))

    def test_an_image_of_the_wrong_length_is_refused(self) -> None:
        # Arrange
        image = b"\x00" * 16

        # Act
        with self.assertRaises(snesst.WrongShape) as raised:
            snesst.ST018(image=image)

        # Assert
        self.assertIn("163840", str(raised.exception))

    def test_a_reset_hands_the_part_back(self) -> None:
        # Arrange
        found = a_part()

        # Act
        handed = found.reset()

        # Assert
        self.assertIs(handed, found)

    def test_a_part_says_which_model_it_is(self) -> None:
        # Arrange
        found = a_part()

        # Act
        model = found.model

        # Assert
        self.assertEqual(model, "st018")

    def test_a_part_says_which_processor_it_runs(self) -> None:
        # Arrange
        found = a_part()

        # Act
        processor = found.processor

        # Assert
        self.assertEqual(processor, "arm60")

    def test_a_part_built_from_an_image_in_hand_has_no_identity(self) -> None:
        # Arrange
        image = IDLE

        # Act
        found = a_part(image)

        # Assert
        self.assertIsNone(found.identity)

    def test_a_part_with_no_image_anywhere_says_so(self) -> None:
        # Arrange
        images = iter(())

        # Act
        with self.assertRaises(snesst.NoFirmware) as raised:
            snesst.ST018(images=images)

        # Assert
        self.assertIn("st018", str(raised.exception))

    def test_an_image_the_search_turns_up_is_the_one_that_runs(self) -> None:
        # Arrange
        hold = Path(tempfile.mkdtemp())
        where = hold / "st018.bin"
        where.write_bytes(IDLE)

        # Act
        found = snesst.ST018(images=iter([(an_identity(), where)]))

        # Assert
        self.assertEqual(found.identity.revision, "ST018")

    def test_an_image_for_another_part_is_passed_over(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp()) / "st010.bin"
        where.write_bytes(IDLE)
        other = firmware.Identity(part="st010", processor="upd96050", revision="ST010")

        # Act
        with self.assertRaises(snesst.NoFirmware) as raised:
            snesst.ST018(images=iter([(other, where)]))

        # Assert
        self.assertIn("st018", str(raised.exception))

    def test_a_core_that_is_not_beside_this_package_is_reported(self) -> None:
        # Arrange
        hold = tempfile.mkdtemp()

        # Act
        with self.assertRaises(snesst.NoFirmware) as raised:
            snesst.ST018(image=IDLE, processor=hold)

        # Assert
        self.assertIn("arm6-python", str(raised.exception))

    def test_a_directory_without_the_package_in_it_is_refused_before_any_import(self) -> None:
        # Arrange
        hold = Path(tempfile.mkdtemp())
        (hold / "arm6").mkdir()

        # Act
        with self.assertRaises(snesst.NoFirmware) as raised:
            snesst.ST018(image=IDLE, processor=hold)

        # Assert
        self.assertIn("the ARM core is not here", str(raised.exception))


class MemoryTest(unittest.TestCase):
    def test_the_program_is_read_where_the_part_fetches_it(self) -> None:
        # Arrange
        found = a_part()

        # Act
        word = found.stores.read_word(0)

        # Assert
        self.assertEqual(word, 0xEAFFFFFE)

    def test_the_data_rom_is_read_where_the_firmware_names_it(self) -> None:
        # Arrange
        image = bytearray(IDLE)
        image[PROGRAM_BYTES] = 0x5A
        found = a_part(bytes(image))

        # Act
        byte = found.stores.read_byte(DATA_ROM)

        # Assert
        self.assertEqual(byte, 0x5A)

    def test_neither_rom_can_be_written(self) -> None:
        # Arrange
        found = a_part()

        # Act
        found.stores.write_byte(0, 0xFF)
        found.stores.write_byte(DATA_ROM, 0xFF)

        # Assert
        self.assertEqual(
            (found.stores.read_byte(0), found.stores.read_byte(DATA_ROM)), (0xFE, 0x00)
        )

    def test_the_work_ram_keeps_what_is_put_in_it(self) -> None:
        # Arrange
        found = a_part()

        # Act
        found.stores.write_word(WORK_RAM, 0x12345678)

        # Assert
        self.assertEqual(found.stores.read_word(WORK_RAM), 0x12345678)

    def test_the_work_ram_wraps_at_the_size_the_stack_pointer_implies(self) -> None:
        # Arrange
        found = a_part()

        # Act
        found.stores.write_byte(WORK_RAM, 0x99)

        # Assert
        self.assertEqual(found.stores.read_byte(WORK_RAM + WORK_RAM_BYTES), 0x99)

    def test_the_ports_are_the_mailbox_seen_from_the_arm(self) -> None:
        # Arrange
        found = a_part()
        found.write(TO_PART, 0x2A)

        # Act
        byte = found.stores.read_byte(PORT_REGION + TO_PART_PORT)

        # Assert
        self.assertEqual(byte, 0x2A)

    def test_and_a_byte_the_arm_stores_there_goes_to_the_console(self) -> None:
        # Arrange
        found = a_part()

        # Act
        found.stores.write_byte(PORT_REGION, 0x77)

        # Assert
        self.assertEqual(found.read(FROM_PART), 0x77)

    def test_an_address_in_no_region_reads_as_nothing(self) -> None:
        # Arrange
        found = a_part()

        # Act
        word = found.stores.read_word(NO_REGION)

        # Assert
        self.assertEqual(word, 0)

    def test_and_writing_there_changes_nothing(self) -> None:
        # Arrange
        found = a_part()

        # Act
        found.stores.write_word(NO_REGION, 0xFFFFFFFF)

        # Assert
        self.assertEqual(found.stores.read_word(NO_REGION), 0)


class ConsoleSideTest(unittest.TestCase):
    def test_the_status_says_the_part_is_up_once_it_has_been_reset(self) -> None:
        # Arrange
        found = a_part()

        # Act
        status = found.read(STATUS)

        # Assert
        self.assertEqual(status, READY)

    def test_a_part_that_is_not_up_does_not_say_it_is(self) -> None:
        # Arrange
        found = a_part().reset()
        found.up = False

        # Act
        status = found.read(STATUS)

        # Assert
        self.assertEqual(status & READY, 0)

    def test_writing_the_data_port_says_a_byte_is_waiting_for_the_part(self) -> None:
        # Arrange
        found = a_part()

        # Act
        found.write(TO_PART, 0xF1)

        # Assert
        self.assertEqual(found.read(STATUS), READY | SENT)

    def test_the_part_reading_it_clears_that(self) -> None:
        # Arrange
        found = a_part(ANSWER)
        found.write(TO_PART, 0xF1)

        # Act
        found.step(2)

        # Assert
        self.assertEqual(found.read(STATUS) & SENT, 0)

    def test_a_byte_the_part_writes_is_offered_to_the_console(self) -> None:
        # Arrange
        found = a_part(ANSWER)
        found.write(TO_PART, 0x42)

        # Act
        found.step(3)

        # Assert
        self.assertEqual(found.read(STATUS), READY | WAITING)

    def test_and_reading_it_gives_the_byte_and_clears_the_flag(self) -> None:
        # Arrange
        found = a_part(ANSWER)
        found.write(TO_PART, 0x42)
        found.step(3)

        # Act
        byte = found.read(FROM_PART)

        # Assert
        self.assertEqual((byte, found.read(STATUS) & WAITING), (0x42, 0))

    def test_reading_the_data_port_with_nothing_offered_gives_nothing(self) -> None:
        # Arrange
        found = a_part()

        # Act
        byte = found.read(FROM_PART)

        # Assert
        self.assertEqual(byte, 0)

    def test_a_reset_pulse_starts_the_part_over(self) -> None:
        # Arrange
        found = a_part(ANSWER)
        found.write(TO_PART, 0x42)
        found.step(3)
        found.write(STATUS, 0)

        # Act
        found.write(STATUS, 1)

        # Assert
        self.assertEqual(found.read(STATUS) & (WAITING | SENT), 0)

    def test_a_write_to_the_status_port_without_bit_zero_resets_nothing(self) -> None:
        # Arrange
        found = a_part()
        found.write(TO_PART, 0x42)

        # Act
        found.write(STATUS, 0xFE)

        # Assert
        self.assertEqual(found.read(STATUS), READY | SENT)

    def test_an_address_the_cartridge_never_touches_is_refused(self) -> None:
        # Arrange
        found = a_part()

        # Act
        with self.assertRaises(snesst.UnknownPort) as raised:
            found.read(0x3801)

        # Assert
        self.assertIn("$3801", str(raised.exception))

    def test_and_so_is_writing_to_one(self) -> None:
        # Arrange
        found = a_part()

        # Act
        with self.assertRaises(snesst.UnknownPort) as raised:
            found.write(0x3806, 0)

        # Assert
        self.assertIn("$3806", str(raised.exception))

    def test_writing_the_port_the_part_writes_is_refused(self) -> None:
        # Arrange
        found = a_part()

        # Act
        with self.assertRaises(snesst.UnknownPort) as raised:
            found.write(FROM_PART, 0)

        # Assert
        self.assertIn("$3800", str(raised.exception))


class PartSideTest(unittest.TestCase):
    def test_reading_the_incoming_port_with_nothing_sent_gives_nothing(self) -> None:
        # Arrange
        found = a_part()

        # Act
        byte = found.port(TO_PART_PORT)

        # Assert
        self.assertEqual(byte, 0)

    def test_reading_the_status_from_inside_gives_the_same_byte(self) -> None:
        # Arrange
        found = a_part()
        found.write(TO_PART, 0x01)

        # Act
        status = found.port(STATUS_PORT)

        # Assert
        self.assertEqual(status, READY | SENT)

    def test_an_offset_the_firmware_never_reaches_reads_as_nothing(self) -> None:
        # Arrange
        found = a_part()

        # Act
        byte = found.port(0x04)

        # Assert
        self.assertEqual(byte, 0)


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


class ExchangeTest(unittest.TestCase):
    def test_a_byte_goes_in_and_comes_back(self) -> None:
        # Arrange
        found = a_part(ANSWER)
        found.write(TO_PART, 0xAB)

        # Act
        found.step(4)

        # Assert
        self.assertEqual(found.read(FROM_PART), 0xAB)

    def test_the_part_counts_what_it_has_run(self) -> None:
        # Arrange
        found = a_part()

        # Act
        found.step(5)

        # Assert
        self.assertEqual(found.steps, 5)


if __name__ == "__main__":
    unittest.main()
