import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import snesst
from snesst import firmware

sys.path.append(str(Path(__file__).resolve().parent.parent / "nec-upd7725-96050-python"))

from upd7725 import models as upd_models


def an_image(program_words: int = 2048, data_words: int = 1024, filler: int = 0xAB) -> bytes:
    return bytes([filler]) * (program_words * 3 + data_words * 2)


class LoadTest(unittest.TestCase):
    def test_a_loaded_image_fills_the_program_store(self) -> None:
        chip = upd_models.lookup("upd7725").build(fill=0)
        image = bytes(range(256)) * 32 + bytes(2048)

        firmware.load(chip, image[: 2048 * 3] + image[: 1024 * 2])

        self.assertEqual(chip.stores.program[0], 0x000102)

    def test_and_the_table_after_it(self) -> None:
        chip = upd_models.lookup("upd7725").build(fill=0)
        program = bytes(2048 * 3)
        table = bytes([0xAA, 0xBB]) * 1024

        firmware.load(chip, program + table)

        self.assertEqual(chip.stores.table[0], 0xAABB)

    def test_an_image_that_does_not_match_the_processor_is_refused(self) -> None:
        # Arrange
        chip = upd_models.lookup("upd7725").build(fill=0)

        # Act
        with self.assertRaises(snesst.WrongShape) as raised:
            firmware.load(chip, bytes(53248))

        # Assert
        self.assertIn("53248", str(raised.exception))


class FoundTest(unittest.TestCase):
    def test_a_directory_with_nothing_in_it_yields_nothing(self) -> None:
        self.assertEqual(list(firmware.found(Path(tempfile.mkdtemp()))), [])

    def test_a_directory_that_is_not_there_yields_nothing_either(self) -> None:
        self.assertEqual(list(firmware.found(Path("/nowhere/at/all"))), [])

    def test_a_file_the_manifest_knows_is_yielded_with_its_name(self) -> None:
        where = Path(tempfile.mkdtemp())
        image = an_image()
        (where / "made-up.bin").write_bytes(image)
        catalogue = {
            "artifacts": [
                {
                    "part": "made-up",
                    "processor": "upd7725",
                    "bytes": len(image),
                    "programWords": 2048,
                    "dataWords": 1024,
                    "accepted": [{"revision": "one", "sha256": hashlib.sha256(image).hexdigest()}],
                }
            ]
        }

        found = list(firmware.found(where, catalogue))

        self.assertEqual(found[0][0].part, "made-up")

    def test_a_file_that_is_not_an_image_at_all_is_passed_over(self) -> None:
        where = Path(tempfile.mkdtemp())
        (where / "README.md").write_text("notes, not an image")
        (where / "notes.txt").write_text("also not one")

        self.assertEqual(list(firmware.found(where, {"artifacts": []})), [])

    def test_a_file_the_manifest_does_not_know_is_passed_over(self) -> None:
        where = Path(tempfile.mkdtemp())
        (where / "nonsense.bin").write_bytes(b"\x00" * 99)

        self.assertEqual(list(firmware.found(where, {"artifacts": []})), [])

    def test_the_directory_comes_from_the_environment_when_one_is_named(self) -> None:
        self.assertEqual(firmware.directory({firmware.DIRECTORY_VARIABLE: "/x"}), Path("/x"))

    def test_and_from_the_repository_when_none_is(self) -> None:
        self.assertEqual(firmware.directory({}).name, "firmware")


class SearchPathTest(unittest.TestCase):
    def test_the_package_always_looks_in_its_own_directory(self) -> None:
        self.assertIn(firmware.DEFAULT_DIRECTORY, firmware.directories({}))

    def test_and_in_the_project_that_carries_it_as_a_submodule(self) -> None:
        self.assertIn(firmware.ALONGSIDE, firmware.directories({}))

    def test_the_project_above_is_looked_at_before_the_package_itself(self) -> None:
        found = firmware.directories({})

        self.assertLess(found.index(firmware.ALONGSIDE), found.index(firmware.DEFAULT_DIRECTORY))

    def test_a_named_directory_is_looked_at_before_either(self) -> None:
        found = firmware.directories({firmware.DIRECTORY_VARIABLE: "/x"})

        self.assertEqual(found[0], Path("/x"))

    def test_more_than_one_can_be_named_at_once(self) -> None:
        found = firmware.directories({firmware.DIRECTORY_VARIABLE: f"/x{os.pathsep}/y"})

        self.assertEqual(found[:2], (Path("/x"), Path("/y")))

    def test_an_empty_entry_between_two_names_is_passed_over(self) -> None:
        found = firmware.directories({firmware.DIRECTORY_VARIABLE: f"/x{os.pathsep}{os.pathsep}/y"})

        self.assertEqual(found[:2], (Path("/x"), Path("/y")))

    def test_no_directory_appears_twice(self) -> None:
        found = firmware.directories({firmware.DIRECTORY_VARIABLE: str(firmware.DEFAULT_DIRECTORY)})

        self.assertEqual(len(found), len(set(found)))

    def test_the_name_this_member_used_to_share_still_works(self) -> None:
        found = firmware.directories({firmware.SHARED_DIRECTORY_VARIABLE: "/x"})

        self.assertEqual(found[0], Path("/x"))

    def test_but_the_members_own_name_is_looked_at_first(self) -> None:
        found = firmware.directories(
            {firmware.SHARED_DIRECTORY_VARIABLE: "/shared", firmware.DIRECTORY_VARIABLE: "/mine"}
        )

        self.assertEqual(found[:2], (Path("/mine"), Path("/shared")))

    def test_the_two_names_are_not_the_same_name(self) -> None:
        self.assertNotEqual(firmware.DIRECTORY_VARIABLE, firmware.SHARED_DIRECTORY_VARIABLE)

    def test_searching_finds_an_image_in_any_of_them(self) -> None:
        first = Path(tempfile.mkdtemp())
        second = Path(tempfile.mkdtemp())
        image = an_image()
        (second / "made-up.bin").write_bytes(image)
        catalogue = {
            "artifacts": [
                {
                    "part": "made-up",
                    "processor": "upd7725",
                    "bytes": len(image),
                    "programWords": 2048,
                    "dataWords": 1024,
                    "accepted": [{"revision": "one", "sha256": hashlib.sha256(image).hexdigest()}],
                }
            ]
        }

        found = list(firmware.search((first, second), catalogue))

        self.assertEqual(found[0][0].part, "made-up")

    def test_the_first_directory_holding_a_part_is_the_one_that_answers(self) -> None:
        first = Path(tempfile.mkdtemp())
        second = Path(tempfile.mkdtemp())
        image = an_image()
        (first / "from-first.bin").write_bytes(image)
        (second / "from-second.bin").write_bytes(image)
        catalogue = {
            "artifacts": [
                {
                    "part": "made-up",
                    "processor": "upd7725",
                    "bytes": len(image),
                    "programWords": 2048,
                    "dataWords": 1024,
                    "accepted": [{"revision": "one", "sha256": hashlib.sha256(image).hexdigest()}],
                }
            ]
        }

        found = list(firmware.search((first, second), catalogue))

        self.assertEqual(len(found), 1)
        self.assertEqual(found[0][1].name, "from-first.bin")


if __name__ == "__main__":
    unittest.main()
