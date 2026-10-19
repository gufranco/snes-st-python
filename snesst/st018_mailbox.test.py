from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import snesst  # noqa: E402

PROGRAM_BYTES = 131072
DATA_BYTES = 32768

FROM_PART = 0x3800
TO_PART = 0x3802
STATUS = 0x3804

TO_PART_PORT = 0x10
STATUS_PORT = 0x20

WAITING = 0x01
SENT = 0x08
READY = 0x80


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


def a_part(image: bytes = IDLE) -> snesst.ST018:
    return snesst.ST018(image=image)


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
