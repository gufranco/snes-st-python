import json
import sys
import unittest
from pathlib import Path
from typing import Any, override

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import snesst
from snesst import firmware

HERE = Path(__file__).resolve().parent

WORD_BYTES = 2

DATA_RAM_WORDS = 2048


def declared(name: str) -> dict[str, Any]:
    held = json.loads((HERE / name).read_text())
    assert isinstance(held, dict), f"{name} does not hold an object"
    return held


class DocumentTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.declared = declared("hardware.json")
        self.facts: dict[str, Any] = self.declared["facts"]

    def test_the_authority_puts_the_microcode_first(self) -> None:
        order = self.declared["authority"]["order"]

        self.assertIn("the microcode", order[0])

    def test_the_missing_data_sheet_is_named_and_not_duplicated(self) -> None:
        missing = self.declared["authority"]["whatIsMissing"]

        self.assertIn("nothing is duplicated here", missing)

    def test_no_constant_claims_to_be_documented(self) -> None:
        claimed = [name for name, fact in self.facts.items() if fact["verified"]]

        self.assertEqual(claimed, [])

    def test_every_constant_names_its_evidence_and_what_would_settle_it(self) -> None:
        missing = [
            name
            for name, fact in self.facts.items()
            if not (fact.get("evidence") and fact.get("howToSettleIt"))
        ]

        self.assertEqual(missing, [])

    def test_what_nothing_settles_is_recorded_rather_than_filled_in(self) -> None:
        stated = self.declared["notStated"]

        self.assertGreaterEqual(len(stated), 4)


LOAD_A_WORD_FOR_THE_CONSOLE = 0xC00000 | 0xBEEF << 6 | 6

PROGRAM_WORDS = 16384


def a_part(*words: int, boot: int = 0) -> Any:
    body = b"".join(word.to_bytes(3, "big") for word in words)
    image = body.ljust(PROGRAM_WORDS * 3, b"\x00") + bytes(DATA_RAM_WORDS * WORD_BYTES)
    identity = firmware.Identity("st010", "upd96050", "MADE UP", PROGRAM_WORDS, DATA_RAM_WORDS)
    return snesst.Chip("st010", image=image, identity=identity, boot=boot)


class ConstantTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.facts: dict[str, Any] = declared("hardware.json")["facts"]

    def window(self) -> int:
        return int(self.facts["enableBit"]["value"])

    def test_the_shared_memory_is_the_size_declared(self) -> None:
        # Arrange
        part = a_part()

        # Act
        found = len(part.memory)

        # Assert
        self.assertEqual(found, self.facts["sharedMemoryBytes"]["value"])

    def test_and_an_address_past_it_lands_back_at_its_start(self) -> None:
        # Arrange
        part = a_part()
        shared = self.facts["sharedMemoryBytes"]["value"]

        # Act
        part.write(self.window() + shared, 0x5A)

        # Assert
        self.assertEqual(part.read(self.window()), 0x5A)

    def test_and_it_is_the_data_ram_the_processor_is_asserted_to_have(self) -> None:
        # Arrange
        part = a_part()

        # Act
        found = len(part.core.stores.scratch) * WORD_BYTES

        # Assert
        self.assertEqual(found, self.facts["sharedMemoryBytes"]["value"])

    def test_the_enable_bit_is_the_one_declared(self) -> None:
        # Arrange
        part = a_part()

        # Act
        part.write(self.window() | 0x100, 0x42)

        # Assert
        self.assertEqual((part.enabled, part.memory[0x100]), (False, 0x42))

    def test_and_an_access_without_it_reaches_the_port_and_wakes_the_part(self) -> None:
        # Arrange
        part = a_part()

        # Act
        part.write(0x100, 0x42)

        # Assert
        self.assertEqual((part.enabled, part.memory[0x100]), (True, 0x00))

    def test_and_it_sits_above_the_shared_window(self) -> None:
        # Arrange
        shared = self.facts["sharedMemoryBytes"]["value"]

        # Act
        found = self.window()

        # Assert
        self.assertGreater(found, shared)

    def test_both_registers_are_where_they_are_declared(self) -> None:
        # Arrange
        registers = self.facts["registers"]["value"]
        part = a_part()

        # Act
        part.write(self.window() + int(registers["command"], 16), 0x04)
        part.write(self.window() + int(registers["start"], 16), 0x01)

        # Assert
        self.assertEqual((part.command, part.execute), (0x04, 0x01))

    def test_and_they_are_adjacent(self) -> None:
        # Arrange
        registers = self.facts["registers"]["value"]

        # Act
        found = int(registers["start"], 16) - int(registers["command"], 16)

        # Assert
        self.assertEqual(found, 1)

    def test_the_handshake_takes_the_declared_number_of_reads(self) -> None:
        # Arrange
        reads = self.facts["bootHandshake"]["value"]

        # Act
        part = a_part(LOAD_A_WORD_FOR_THE_CONSOLE)

        # Assert
        status = part.core.registers.sr
        self.assertEqual((reads, status.rqm, status.drs), (2, False, False))

    def test_and_the_record_says_it_came_from_running_the_program(self) -> None:
        # Arrange
        handshake = self.facts["bootHandshake"]

        # Act
        found = handshake["evidence"]

        # Assert
        self.assertIn("running the program", found)

    def test_and_the_two_parts_do_not_wait_alike(self) -> None:
        # Arrange
        waits = self.facts["waitWords"]["value"]

        # Act
        found = (waits["st010"], waits["st011"])

        # Assert
        self.assertEqual(found, ([3, 4, 5], [2]))


class DivergenceTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.entries: list[dict[str, Any]] = declared("divergences.json")["divergences"]

    def test_each_entry_says_which_source_the_package_follows(self) -> None:
        allowed = {"cartridges", "document", "reference", "microcode", "neither"}

        self.assertEqual({entry["packageFollows"] for entry in self.entries} - allowed, set())

    def test_each_entry_says_what_would_settle_or_reopen_it(self) -> None:
        missing = [
            entry["id"]
            for entry in self.entries
            if not (entry.get("wouldSettleIt") or entry.get("wouldReopenIt"))
        ]

        self.assertEqual(missing, [])

    def test_the_handshake_a_derived_model_missed_is_recorded(self) -> None:
        entry = next(
            item for item in self.entries if item["id"] == "a-derived-model-missed-the-handshake"
        )

        self.assertEqual(entry["packageFollows"], "microcode")

    def test_and_it_says_why_that_class_of_error_exists(self) -> None:
        entry = next(
            item for item in self.entries if item["id"] == "a-derived-model-missed-the-handshake"
        )

        self.assertIn("somebody thought to look at", entry["reasoning"])

    def test_the_interface_resting_on_a_reference_is_recorded(self) -> None:
        entry = next(
            item for item in self.entries if item["id"] == "the-interface-is-not-the-microcode"
        )

        self.assertIn("weakest evidence in this package", entry["reasoning"])

    def test_the_two_parts_waiting_differently_is_recorded(self) -> None:
        named = {entry["id"] for entry in self.entries}

        self.assertIn("the-two-parts-wait-differently", named)

    def test_carrying_no_image_is_recorded_as_a_boundary(self) -> None:
        entry = next(item for item in self.entries if item["id"] == "no-image-is-carried-here")

        self.assertEqual(entry["status"], "notADisagreement")


if __name__ == "__main__":
    unittest.main(verbosity=1)
