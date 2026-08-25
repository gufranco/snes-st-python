import json
import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import st010
from st010 import errors, models

EVERY_PART = {"st010", "st011"}


class CatalogueTest(unittest.TestCase):
    def test_the_package_names_every_part_it_covers(self) -> None:
        self.assertEqual(set(models.MODELS), EVERY_PART)

    def test_the_part_that_plays_shogi_is_one_of_them(self) -> None:
        self.assertIn("st011", models.MODELS)

    def test_a_part_says_what_it_is(self) -> None:
        self.assertTrue(models.describe("st010").summary)

    def test_and_which_image_it_runs(self) -> None:
        self.assertEqual(models.describe("st011").image, "st011")

    def test_a_part_prints_as_itself_and_the_image_it_runs(self) -> None:
        printed = repr(models.describe("st010"))

        self.assertIn("st010", printed)

    def test_every_part_carries_a_summary(self) -> None:
        for name in models.MODELS:
            self.assertTrue(models.describe(name).summary, name)


class NamingTest(unittest.TestCase):
    def test_a_part_name_is_matched_however_it_is_written(self) -> None:
        for written in ("ST010", "st-010", "ST_010", "seta-st010"):
            self.assertEqual(models.describe(written).name, "st010")

    def test_the_other_part_is_matched_the_same_way(self) -> None:
        for written in ("ST011", "st-011", "seta-st011"):
            self.assertEqual(models.describe(written).name, "st011")

    def test_a_name_no_part_answers_to_is_refused(self) -> None:
        with self.assertRaises(errors.UnknownModelError):
            models.describe("nonsense")

    def test_and_the_refusal_lists_what_there_is(self) -> None:
        with self.assertRaises(errors.UnknownModelError) as raised:
            models.describe("nonsense")

        for name in EVERY_PART:
            self.assertIn(name, str(raised.exception))

    def test_no_alias_belongs_to_two_parts(self) -> None:
        seen = [alias for name in models.MODELS for alias in models.describe(name).aliases]

        self.assertEqual(len(seen), len(set(seen)))


class DeclaredImageTest(unittest.TestCase):
    """That every part names an image the processor will recognise and confirm.

    This is what a machine with no microcode can still check, and it is the check
    that matters most: a user who supplies a file gets it identified by digest
    before a byte of it is run, so a wrong file is refused rather than executed.
    """

    def _manifest(self) -> Any:
        where = Path(__file__).resolve().parent / "artifacts.manifest.json"
        return json.loads(where.read_text())

    def test_every_part_runs_an_image_the_processor_declares(self) -> None:
        declared = {one["part"] for one in self._manifest()["artifacts"]}

        for name in models.MODELS:
            self.assertIn(models.describe(name).image, declared, name)

    def test_every_declared_image_carries_a_deciding_digest(self) -> None:
        for one in self._manifest()["artifacts"]:
            for accepted in one["accepted"]:
                self.assertEqual(len(accepted["sha256"]), 64, one["part"])

    def test_both_parts_of_this_family_run_the_same_processor(self) -> None:
        declared = {one["part"]: one["processor"] for one in self._manifest()["artifacts"]}

        for name in models.MODELS:
            self.assertEqual(declared[models.describe(name).image], "upd96050", name)


class BuildingTest(unittest.TestCase):
    def test_a_name_no_part_answers_to_is_refused_before_any_image_is_looked_for(self) -> None:
        with self.assertRaises(errors.UnknownModelError):
            st010.Chip("nonsense")

    def test_the_default_part_is_one_the_catalogue_knows(self) -> None:
        self.assertIn(st010.DEFAULT_MODEL, models.MODELS)

    def test_the_family_name_reaches_the_same_thing(self) -> None:
        self.assertIs(st010.Chip, st010.Chip)


if __name__ == "__main__":
    unittest.main()
