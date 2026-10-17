import contextlib
import sys
import tempfile
import unittest
from collections.abc import Iterator
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import snesst
from snesst import firmware

SHARED_BYTES = 4096

WINDOW = 0x680000

COMMAND = WINDOW + 0x20

START = WINDOW + 0x21

START_BIT = 0x80

PROGRAM_WORDS = 16384

DATA_WORDS = 2048

POINT_AT_THE_REGISTERS = 0xC00404

CLEAR_WHERE_POINTED = 0xC0000F

JUMP_TO_THE_TOP = 0xA00000

SUBMODULE_ADVICE = "git submodule update --init --recursive"


def an_identity(part: str = "st010") -> Any:
    return firmware.Identity(part, "upd96050", "MADE UP", PROGRAM_WORDS, DATA_WORDS)


def a_program(*words: int) -> bytes:
    body = b"".join(word.to_bytes(3, "big") for word in words)
    return body.ljust(PROGRAM_WORDS * 3, b"\x00") + bytes(DATA_WORDS * 2)


def built(image: bytes | None = None, **options: Any) -> Any:
    program = a_program() if image is None else image
    return snesst.Chip("st010", image=program, identity=an_identity(), boot=64, **options)


def woken(**options: Any) -> Any:
    part = built(**options)
    part.write(0x000000, 0x00)
    return part


@contextlib.contextmanager
def without_the_processor() -> Iterator[None]:
    held = {
        name: module
        for name, module in sys.modules.items()
        if name == "upd7725" or name.startswith("upd7725.")
    }
    for name in held:
        del sys.modules[name]
    sys.modules["upd7725"] = None  # type: ignore[assignment]
    try:
        yield
    finally:
        del sys.modules["upd7725"]
        sys.modules.update(held)


class WithoutTest(unittest.TestCase):
    def test_with_no_processor_it_offers_nothing(self) -> None:
        # Arrange
        found: dict[str, Any] = {"not": "asked yet"}

        # Act
        with without_the_processor():
            found = snesst.available()

        # Assert
        self.assertEqual(found, {})

    def test_and_says_the_submodule_is_the_thing_that_is_missing(self) -> None:
        # Arrange
        found: str | None = None

        # Act
        with without_the_processor():
            found = snesst.why_not()

        # Assert
        self.assertIn(SUBMODULE_ADVICE, str(found))

    def test_and_refuses_to_build_a_part(self) -> None:
        # Arrange
        image = a_program()

        # Act
        with without_the_processor(), self.assertRaises(snesst.NoFirmware) as raised:
            snesst.Chip("st010", image=image, identity=an_identity())

        # Assert
        self.assertIn(SUBMODULE_ADVICE, str(raised.exception))

    def test_with_a_processor_but_no_image_it_says_that_instead(self) -> None:
        # Arrange
        nothing: dict[str, Any] = {}

        # Act
        found = snesst.why_not(nothing)

        # Assert
        self.assertIn("no firmware image was found", str(found))

    def test_a_part_with_no_image_is_refused_by_name(self) -> None:
        # Arrange
        nothing: dict[str, Any] = {}

        # Act
        with self.assertRaises(snesst.NoFirmware) as raised:
            snesst.Chip("st011", images=nothing)

        # Assert
        self.assertIn("there is no firmware image for st011", str(raised.exception))

    def test_an_image_with_nothing_saying_what_it_is_is_refused(self) -> None:
        # Arrange
        image = a_program()

        # Act
        with self.assertRaises(snesst.NoFirmware) as raised:
            snesst.Chip("st010", image=image)

        # Assert
        self.assertIn("how much of it is program", str(raised.exception))


class WhereTheImagesAreTest(unittest.TestCase):
    def catalogue(self, part: str = "st010") -> Any:
        where = Path(tempfile.mkdtemp()) / "made-up.bin"
        where.write_bytes(a_program())
        return {part: (an_identity(part), where)}

    def test_an_image_that_was_found_is_read_from_its_file(self) -> None:
        # Arrange
        images = self.catalogue()

        # Act
        part = snesst.Chip("st010", images=images, boot=64)

        # Assert
        self.assertEqual((part.part, part.identity.revision), ("st010", "MADE UP"))

    def test_the_other_part_is_reached_the_same_way(self) -> None:
        # Arrange
        images = self.catalogue("st011")

        # Act
        part = snesst.Chip("st011", images=images, boot=64)

        # Assert
        self.assertEqual(part.part, "st011")

    def test_with_an_image_present_there_is_no_reason_it_cannot_run(self) -> None:
        # Arrange
        images = self.catalogue()

        # Act
        found = snesst.why_not(images)

        # Assert
        self.assertIsNone(found)

    def test_a_catalogue_handed_in_is_the_one_offered(self) -> None:
        # Arrange
        images = self.catalogue()

        # Act
        found = snesst.available(images)

        # Assert
        self.assertEqual(found, images)


class ShapeTest(unittest.TestCase):
    def test_it_carries_the_part_it_was_asked_for_and_the_model_name(self) -> None:
        # Arrange
        asked = "st010"

        # Act
        part = snesst.Chip(asked, image=a_program(), identity=an_identity(), boot=1)

        # Assert
        self.assertEqual((part.part, part.model), ("st010", "st010"))

    def test_it_names_the_processor_the_image_says_it_runs_on(self) -> None:
        # Arrange
        part = built()

        # Act
        found = part.processor

        # Assert
        self.assertEqual(found, "upd96050")

    def test_it_prints_as_the_part_and_how_it_is_run(self) -> None:
        # Arrange
        part = built()

        # Act
        printed = repr(part)

        # Assert
        self.assertEqual(printed, "<Chip st010 on upd96050>")

    def test_the_shared_memory_is_the_size_the_model_shares(self) -> None:
        # Arrange
        part = built()

        # Act
        found = part.memory

        # Assert
        self.assertEqual(len(found), SHARED_BYTES)

    def test_memory_can_be_handed_over_at_the_start(self) -> None:
        # Arrange
        memory = bytearray([0x5A]) * SHARED_BYTES

        # Act
        part = built(memory=memory)

        # Assert
        self.assertEqual(part.memory, bytes(memory))

    def test_memory_longer_than_the_shared_memory_is_taken_up_to_it(self) -> None:
        # Arrange
        memory = bytearray([0x11]) * (SHARED_BYTES * 2)

        # Act
        part = built(memory=memory)

        # Assert
        self.assertEqual(part.memory, bytes([0x11]) * SHARED_BYTES)


class HandshakeTest(unittest.TestCase):
    def test_a_freshly_built_part_is_past_the_boot_exchange(self) -> None:
        # Arrange
        image = a_program()

        # Act
        part = built(image)

        # Assert
        self.assertIs(part.core.registers.sr.rqm, False)

    def test_the_exchange_can_be_asked_for_again_without_reloading(self) -> None:
        # Arrange
        part = built()

        # Act
        handed = part.handshake()

        # Assert
        self.assertEqual((handed, part.core.registers.sr.rqm), (part, False))


class DecodeTest(unittest.TestCase):
    def test_the_window_with_the_bit_clear_is_the_port_rather_than_a_refusal(self) -> None:
        # Arrange
        part = built()
        status = part.console.read(1)

        # Act
        found = part.read(0x000001)

        # Assert
        self.assertEqual(found, status)

    def test_the_write_with_the_bit_clear_wakes_it(self) -> None:
        # Arrange
        part = built()

        # Act
        part.write(0x000000, 0x00)

        # Assert
        self.assertIs(part.enabled, True)

    def test_a_woken_part_reads_its_shared_memory(self) -> None:
        # Arrange
        part = woken()

        # Act
        part.write(WINDOW + 0x100, 0x37)

        # Assert
        self.assertEqual(part.read(WINDOW + 0x100), 0x37)

    def test_the_command_address_holds_a_copy_of_the_command(self) -> None:
        # Arrange
        part = woken()

        # Act
        part.write(COMMAND, 0x04)

        # Assert
        self.assertEqual(part.command, 0x04)

    def test_the_start_address_holds_what_was_written_to_it(self) -> None:
        # Arrange
        part = woken()

        # Act
        part.write(START, 0x01)

        # Assert
        self.assertEqual(part.execute, 0x01)

    def test_a_sleeping_part_takes_no_command(self) -> None:
        # Arrange
        part = built()

        # Act
        part.write(COMMAND, 0x04)

        # Assert
        self.assertIs(part.enabled, False)

    def test_forgetting_it_was_woken_does_not_reload_the_part(self) -> None:
        # Arrange
        part = woken()
        part.write(WINDOW + 0x100, 0x42)

        # Act
        handed = part.reset()

        # Assert
        self.assertEqual((handed, part.enabled, part.memory[0x100]), (part, False, 0x42))


class RunningTest(unittest.TestCase):
    def test_a_program_that_never_clears_the_start_byte_is_given_up_on(self) -> None:
        # Arrange
        part = woken(patience=64)
        part.write(COMMAND, 0x03)

        # Act
        with self.assertRaises(snesst.NeverFinished) as raised:
            part.write(START, START_BIT)

        # Assert
        self.assertEqual(
            str(raised.exception), "st010 did not finish command 0x03 within 64 instructions"
        )

    def test_a_write_without_the_start_bit_starts_nothing(self) -> None:
        # Arrange
        part = woken(patience=64)

        # Act
        part.write(START, 0x01)

        # Assert
        self.assertEqual(part.execute, 0x01)

    def test_a_program_that_clears_the_start_byte_is_taken_at_its_word(self) -> None:
        # Arrange
        image = a_program(POINT_AT_THE_REGISTERS, CLEAR_WHERE_POINTED, JUMP_TO_THE_TOP)
        part = woken(image=image, patience=8)

        # Act
        part.write(START, START_BIT)

        # Assert
        self.assertEqual(part.execute, 0x00)

    def test_the_odd_address_in_the_port_window_is_the_status_side(self) -> None:
        # Arrange
        part = built()
        before = part.core.registers.pc

        # Act
        part.write(0x000001, 0x00)

        # Assert
        self.assertEqual((part.enabled, part.core.registers.pc), (True, before))

    def test_a_write_to_the_even_address_reaches_the_data_port(self) -> None:
        # Arrange
        part = built()

        # Act
        part.write(0x000000, 0x5A)

        # Assert
        self.assertEqual(part.core.registers.dr & 0xFF, 0x5A)


if __name__ == "__main__":
    unittest.main()
