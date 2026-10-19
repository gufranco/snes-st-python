import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance import testroms
from snesst import firmware

PROGRAM_WORDS = 16384

DATA_WORDS = 2048

ARM_PROGRAM_BYTES = 131072

ARM_DATA_BYTES = 32768

POINT_AT_THE_REGISTERS = 0xC00404

CLEAR_WHERE_POINTED = 0xC0000F

JUMP_TO_THE_TOP = 0xA00000

ECHO = (0xE3A0B101, 0xE5DB0010, 0xE5CB0000, 0xEAFFFFFE)

SPIN = (0xEAFFFFFE,)

HARDWARE = Path(__file__).resolve().parent / "hardware.json"


def a_program(*words: int) -> bytes:
    body = b"".join(word.to_bytes(3, "big") for word in words)
    return body.ljust(PROGRAM_WORDS * 3, b"\x00") + bytes(DATA_WORDS * 2)


def an_arm_program(*words: int) -> bytes:
    body = b"".join(word.to_bytes(4, "little") for word in words)
    return body.ljust(ARM_PROGRAM_BYTES, b"\x00") + bytes(ARM_DATA_BYTES)


def a_signal_identity(part: str) -> firmware.Identity:
    return firmware.Identity(part, "upd96050", "MADE UP", PROGRAM_WORDS, DATA_WORDS)


def an_arm_identity() -> firmware.Identity:
    return firmware.Identity(
        "st018", "arm60", "MADE UP", program_bytes=ARM_PROGRAM_BYTES, data_bytes=ARM_DATA_BYTES
    )


def waits() -> dict[str, list[int]]:
    held: dict[str, list[int]] = json.loads(HARDWARE.read_text())["facts"]["waitWords"]["value"]
    return held


class TheRecordedRunsTest(unittest.TestCase):
    def test_the_st010_program_waits_where_the_record_says(self) -> None:
        # Arrange
        expected = waits()["st010"][0]

        # Act
        found = testroms.measured()["st010-fa9bced8"]["waitsAt"]

        # Assert
        self.assertEqual(found, expected)

    def test_the_st010_program_answers_its_first_command_as_the_readme_shows(self) -> None:
        # Arrange
        expected = (106, 0x9300)

        # Act
        held = testroms.measured()["st010-fa9bced8"]

        # Assert
        self.assertEqual((held["command1Instructions"], held["command1Answer"]), expected)

    def test_the_st011_program_waits_where_the_record_says(self) -> None:
        # Arrange
        expected = waits()["st011"][0]

        # Act
        found = testroms.measured()["st011-8b2b3f3f"]["waitsAt"]

        # Assert
        self.assertEqual(found, expected)

    def test_the_st018_program_refuses_a_command_it_does_not_know(self) -> None:
        # Arrange
        expected = 0xEE

        # Act
        found = testroms.measured()["st018-6df209ab"]["unknownCommandAnswer"]

        # Assert
        self.assertEqual(found, expected)

    def test_every_run_was_of_the_file_the_record_names(self) -> None:
        # Arrange
        record = testroms.recorded()

        # Act
        found = sorted(testroms.measured())

        # Assert
        self.assertEqual(found, sorted(entry["id"] for entry in record))


class MeasureTest(unittest.TestCase):
    def test_a_signal_processor_part_is_measured_where_it_waits(self) -> None:
        # Arrange
        image = a_program(JUMP_TO_THE_TOP)

        # Act
        found = testroms.measure(a_signal_identity("st011"), image)

        # Assert
        self.assertEqual(found, {"part": "st011", "waitsAt": 0})

    def test_the_racing_part_is_also_asked_its_first_command(self) -> None:
        # Arrange
        image = a_program(POINT_AT_THE_REGISTERS, CLEAR_WHERE_POINTED, JUMP_TO_THE_TOP)

        # Act
        found = testroms.measure(a_signal_identity("st010"), image)

        # Assert
        self.assertEqual(
            sorted(found), ["command1Answer", "command1Instructions", "part", "waitsAt"]
        )

    def test_the_arm_part_is_asked_a_command_and_its_answer_kept(self) -> None:
        # Arrange
        image = an_arm_program(*ECHO)

        # Act
        found = testroms.measure(an_arm_identity(), image)

        # Assert
        self.assertEqual(found, {"part": "st018", "unknownCommandAnswer": 0x00})

    def test_an_arm_part_that_never_answers_is_kept_as_no_answer(self) -> None:
        # Arrange
        image = an_arm_program(*SPIN)

        # Act
        found = testroms.measure(an_arm_identity(), image)

        # Assert
        self.assertEqual(found, {"part": "st018", "unknownCommandAnswer": None})


class Folder:
    def __init__(self, image: bytes) -> None:
        self.where = Path(tempfile.mkdtemp())
        (self.where / "dump.bin").write_bytes(image)
        (self.where / "notes.txt").write_text("not an image")
        (self.where / "inner").mkdir()
        digest = hashlib.sha256(image).hexdigest()
        self.entries = [{"id": "made-up", "sha256": digest}]
        self.catalogue: dict[str, Any] = {
            "artifacts": [
                {
                    "part": "st011",
                    "processor": "upd96050",
                    "bytes": len(image),
                    "programWords": PROGRAM_WORDS,
                    "dataWords": DATA_WORDS,
                    "accepted": [{"revision": "MADE UP", "sha256": digest}],
                }
            ]
        }
        self.measured = Path(tempfile.mkdtemp()) / "measured.json"

    def run(self, argv: list[str], held: dict[str, Any] | None = None) -> tuple[int, list[str]]:
        said: list[str] = []
        if held is not None:
            self.measured.write_text(json.dumps(held))
        code = testroms.main(
            argv,
            say=said.append,
            measure=lambda identity, image: {"part": identity.part, "waitsAt": 2},
            entries=self.entries,
            catalogue=self.catalogue,
            measured_path=self.measured,
        )
        return code, said


class MainTest(unittest.TestCase):
    def test_with_no_folder_named_it_says_how_to_use_it(self) -> None:
        # Arrange
        folder = Folder(a_program())

        # Act
        code, said = folder.run([])

        # Assert
        self.assertEqual((code, said), (2, [testroms.USAGE]))

    def test_a_folder_holding_nothing_the_record_names_is_a_counted_skip(self) -> None:
        # Arrange
        folder = Folder(a_program())

        # Act
        code, said = folder.run([str(folder.where / "inner")])

        # Assert
        self.assertEqual(
            (code, said[-1]), (2, "  0 of 1 recorded images were found, so nothing was run")
        )

    def test_a_run_that_agrees_with_the_record_passes(self) -> None:
        # Arrange
        folder = Folder(a_program())

        # Act
        code, said = folder.run([str(folder.where)], {"made-up": {"part": "st011", "waitsAt": 2}})

        # Assert
        self.assertEqual((code, said), (0, ["  made-up: agrees with the record"]))

    def test_a_run_that_disagrees_with_the_record_fails_and_says_where(self) -> None:
        # Arrange
        folder = Folder(a_program())

        # Act
        code, said = folder.run([str(folder.where)], {"made-up": {"part": "st011", "waitsAt": 3}})

        # Assert
        self.assertEqual(
            (code, said),
            (
                1,
                [
                    "  made-up: ran {'part': 'st011', 'waitsAt': 2}, the record holds"
                    " {'part': 'st011', 'waitsAt': 3}"
                ],
            ),
        )

    def test_recording_writes_what_ran(self) -> None:
        # Arrange
        folder = Folder(a_program())

        # Act
        code, _said = folder.run([testroms.RECORDING, str(folder.where)])

        # Assert
        self.assertEqual(
            (code, json.loads(folder.measured.read_text())),
            (0, {"made-up": {"part": "st011", "waitsAt": 2, "storedLowByteFirst": False}}),
        )

    def test_a_folder_that_is_not_one_is_a_counted_skip_too(self) -> None:
        # Arrange
        folder = Folder(a_program())

        # Act
        code, _said = folder.run(["/nowhere/at/all"])

        # Assert
        self.assertEqual(code, 2)


class CommandTest(unittest.TestCase):
    def test_it_leaves_with_the_code_the_run_returned(self) -> None:
        # Arrange
        held = sys.argv
        sys.argv = ["testroms"]

        # Act
        with self.assertRaises(SystemExit) as raised:
            testroms.entry(say=lambda line: None)
        sys.argv = held

        # Assert
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
