import json
import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import snesst
from snesst import errors, models

EVERY_PART = {"st010", "st011", "st018"}


class CatalogueTest(unittest.TestCase):
    def test_the_package_names_every_part_it_covers(self) -> None:
        self.assertEqual(set(models.MODELS), EVERY_PART)

    def test_the_part_that_plays_shogi_is_one_of_them(self) -> None:
        self.assertIn("st011", models.MODELS)

    def test_a_part_says_what_it_is(self) -> None:
        self.assertTrue(models.lookup("st010").summary)

    def test_and_which_image_it_runs(self) -> None:
        self.assertEqual(models.lookup("st011").image, "st011")

    def test_a_part_prints_as_itself_and_the_image_it_runs(self) -> None:
        printed = repr(models.lookup("st010"))

        self.assertIn("st010", printed)

    def test_every_part_carries_a_summary(self) -> None:
        for name in models.MODELS:
            self.assertTrue(models.lookup(name).summary, name)


class NamingTest(unittest.TestCase):
    def test_a_part_name_is_matched_however_it_is_written(self) -> None:
        for written in ("ST010", "st-010", "ST_010", "seta-st010"):
            self.assertEqual(models.lookup(written).name, "st010")

    def test_the_other_part_is_matched_the_same_way(self) -> None:
        for written in ("ST011", "st-011", "seta-st011"):
            self.assertEqual(models.lookup(written).name, "st011")

    def test_a_name_no_part_answers_to_is_refused(self) -> None:
        with self.assertRaises(errors.UnknownModelError):
            models.lookup("nonsense")

    def test_and_the_refusal_lists_what_there_is(self) -> None:
        with self.assertRaises(errors.UnknownModelError) as raised:
            models.lookup("nonsense")

        for name in EVERY_PART:
            self.assertIn(name, str(raised.exception))

    def test_no_alias_belongs_to_two_parts(self) -> None:
        seen = [alias for name in models.MODELS for alias in models.lookup(name).aliases]

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
            self.assertIn(models.lookup(name).image, declared, name)

    def test_every_declared_image_carries_a_deciding_digest(self) -> None:
        for one in self._manifest()["artifacts"]:
            for accepted in one["accepted"]:
                self.assertEqual(len(accepted["sha256"]), 64, one["part"])

    def test_the_two_signal_processor_parts_run_the_same_processor(self) -> None:
        """And the third does not, which is the whole reason it is modelled apart.

        The name is the trap: three parts under one vendor prefix, two of them the
        same digital signal processor and the third a 32 bit ARM.
        """
        declared = {one["part"]: one["processor"] for one in self._manifest()["artifacts"]}

        found = {name: declared[models.lookup(name).image] for name in models.MODELS}

        self.assertEqual(found, {"st010": "upd96050", "st011": "upd96050", "st018": "arm60"})


class DispatchTest(unittest.TestCase):
    """That one factory reaches both arrangements, which is what a caller wants."""

    def named(self, model: str) -> str:
        """What the factory did with a name, on a machine with the image or without.

        Both answers come through the same branch, which is the thing being
        checked here. A runner holds no image and a reader's machine may hold
        one, so a check that only worked on the second would be a check nobody
        on the first has seen run.
        """
        from snesst import errors

        try:
            return str(snesst.Chip(model).part)
        except errors.NoFirmware as refused:
            found = str(refused)
            return next((one for one in models.MODELS if one in found), found)

    def test_the_signal_processor_parts_are_built_by_the_class_that_runs_one(self) -> None:
        self.assertEqual(self.named("seta010"), "st010")

    def test_the_arm_part_is_built_by_the_class_that_runs_an_arm(self) -> None:
        from snesst import errors

        with self.assertRaises(errors.NoFirmware) as raised:
            snesst.Chip("setast018")

        self.assertIn("st018", str(raised.exception))


class BuildingTest(unittest.TestCase):
    def test_a_name_no_part_answers_to_is_refused_before_any_image_is_looked_for(self) -> None:
        with self.assertRaises(errors.UnknownModelError):
            snesst.Chip("nonsense")

    def test_the_default_part_is_one_the_catalogue_knows(self) -> None:
        self.assertIn("st010", models.MODELS)

    def test_the_family_name_reaches_the_same_thing(self) -> None:
        self.assertIs(snesst.Chip, snesst.Chip)


class NamingNoneTest(unittest.TestCase):
    """That leaving the model out is refused, and refused usefully."""

    def test_building_without_naming_a_model_is_refused(self) -> None:
        with self.assertRaises(errors.UnknownModelError):
            snesst.Chip()

    def test_and_the_refusal_names_every_model_there_is(self) -> None:
        with self.assertRaises(errors.UnknownModelError) as caught:
            snesst.Chip()

        missing = [name for name in snesst.MODELS if name not in str(caught.exception)]

        self.assertEqual(missing, [])

    def test_nothing_named_describe_is_published(self) -> None:
        self.assertFalse(hasattr(snesst, "describe"))

    def test_and_no_default_model_is_published_either(self) -> None:
        self.assertFalse(hasattr(snesst, "DEFAULT_MODEL"))


if __name__ == "__main__":
    unittest.main()
