"""Hold this package's constants to hardware.json, and to their standing.

Running the part's own microcode settles what it computes. It settles nothing
about where the console reaches it, and those constants come from a reference.
The point of this file is that the two kinds of fact stay visibly apart, so
nobody inherits the interface with the confidence the microcode earns.
"""

import json
import sys
import unittest
from pathlib import Path
from typing import Any, override

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from snesst import chip

HERE = Path(__file__).resolve().parent

WORD_BYTES = 2
"""Bytes to a word on this processor, from NEC's data sheet by way of the sibling."""

DATA_RAM_WORDS = 2048
"""Words of data RAM the uPD96050 is asserted to have, unverified in that sibling."""


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


class ConstantTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.facts: dict[str, Any] = declared("hardware.json")["facts"]

    def test_the_shared_memory_is_the_size_declared(self) -> None:
        shared = self.facts["sharedMemoryBytes"]

        self.assertEqual(shared["value"], chip.MEMORY_BYTES)

    def test_and_it_is_the_data_ram_the_processor_is_asserted_to_have(self) -> None:
        self.assertEqual(chip.MEMORY_BYTES, DATA_RAM_WORDS * WORD_BYTES)

    def test_the_enable_bit_is_the_one_declared(self) -> None:
        enable = self.facts["enableBit"]

        self.assertEqual(enable["value"], chip.ENABLE_BIT)

    def test_and_it_sits_above_the_shared_window(self) -> None:
        self.assertGreater(chip.ENABLE_BIT, chip.MEMORY_BYTES)

    def test_both_registers_are_where_they_are_declared(self) -> None:
        registers = self.facts["registers"]["value"]

        found = (int(registers["command"], 16), int(registers["start"], 16))

        self.assertEqual(found, (chip.COMMAND_REGISTER, chip.START_REGISTER))

    def test_and_they_are_adjacent(self) -> None:
        self.assertEqual(chip.START_REGISTER - chip.COMMAND_REGISTER, 1)

    def test_the_handshake_takes_the_declared_number_of_reads(self) -> None:
        handshake = self.facts["bootHandshake"]

        self.assertEqual(handshake["value"], chip.HANDSHAKE_READS)

    def test_and_the_record_says_it_came_from_running_the_program(self) -> None:
        handshake = self.facts["bootHandshake"]

        self.assertIn("running the program", handshake["evidence"])

    def test_each_part_waits_where_it_is_declared_to(self) -> None:
        waits = self.facts["waitWords"]["value"]

        found = {name: tuple(words) for name, words in waits.items()}

        self.assertEqual(found, dict(chip.COMMAND_LOOP))

    def test_and_the_two_parts_do_not_wait_alike(self) -> None:
        waits = self.facts["waitWords"]["value"]

        self.assertNotEqual(waits["st010"], waits["st011"])


class DivergenceTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.entries: list[dict[str, Any]] = declared("divergences.json")["divergences"]

    def test_each_entry_says_which_source_the_package_follows(self) -> None:
        allowed = {"document", "reference", "microcode", "neither"}

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
