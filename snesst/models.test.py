import json
import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import snesst
from snesst import chip, firmware

EVERY_PART = {"st010", "st011", "st018"}

ST018_IMAGE_BYTES = 163840


def an_identity(part: str) -> Any:
    return firmware.Identity(part, "upd96050", "MADE UP", 16384, 2048)


def a_program() -> bytes:
    return bytes(16384 * 3 + 2048 * 2)


def built(model: str) -> Any:
    return snesst.Chip(model, image=a_program(), identity=an_identity("st010"), boot=1)


def built_arm(model: str) -> Any:
    return snesst.Chip(model, image=bytes(ST018_IMAGE_BYTES))


class CatalogueTest(unittest.TestCase):
    def test_the_package_names_every_part_it_covers(self) -> None:
        # Arrange
        catalogue = snesst.MODELS

        # Act
        found = set(catalogue)

        # Assert
        self.assertEqual(found, EVERY_PART)

    def test_a_part_says_what_it_is(self) -> None:
        # Arrange
        model = snesst.MODELS["st010"]

        # Act
        found = model.summary

        # Assert
        self.assertIn("ST010", found)

    def test_and_which_image_it_runs(self) -> None:
        # Arrange
        model = snesst.MODELS["st011"]

        # Act
        found = model.image

        # Assert
        self.assertEqual(found, "st011")

    def test_a_part_prints_as_itself_and_the_image_it_runs(self) -> None:
        # Arrange
        model = snesst.MODELS["st018"]

        # Act
        printed = repr(model)

        # Assert
        self.assertEqual(printed, "<Model st018, running the st018 image>")

    def test_every_part_carries_a_summary_naming_it(self) -> None:
        # Arrange
        catalogue = snesst.MODELS

        # Act
        missing = [name for name, model in catalogue.items() if name.upper() not in model.summary]

        # Assert
        self.assertEqual(missing, [])

    def test_each_part_answers_to_the_aliases_the_readme_lists(self) -> None:
        # Arrange
        expected = {
            "st010": ("st-010", "seta010", "setast010"),
            "st011": ("st-011", "seta011", "setast011"),
            "st018": ("st-018", "seta018", "setast018"),
        }

        # Act
        found = {name: model.aliases for name, model in snesst.MODELS.items()}

        # Assert
        self.assertEqual(found, expected)


class NamingTest(unittest.TestCase):
    def test_a_part_name_is_matched_however_it_is_written(self) -> None:
        # Arrange
        written = ("ST010", "st-010", "ST_010", "seta-st010")

        # Act
        found = [built(one).model for one in written]

        # Assert
        self.assertEqual(found, ["st010"] * 4)

    def test_the_other_part_is_matched_the_same_way(self) -> None:
        # Arrange
        written = ("ST011", "st-011", "seta-st011")

        # Act
        found = [built(one).model for one in written]

        # Assert
        self.assertEqual(found, ["st011"] * 3)

    def test_and_so_is_the_third(self) -> None:
        # Arrange
        written = ("ST018", "st_018", "Seta-ST018")

        # Act
        found = [built_arm(one).model for one in written]

        # Assert
        self.assertEqual(found, ["st018"] * 3)

    def test_a_name_no_part_answers_to_is_refused(self) -> None:
        # Arrange
        asked = "nonsense"

        # Act
        with self.assertRaises(snesst.UnknownModelError) as raised:
            snesst.Chip(asked)

        # Assert
        self.assertEqual(
            str(raised.exception),
            "nonsense is not a model this package covers; it has st010, st011, st018",
        )

    def test_no_alias_belongs_to_two_parts(self) -> None:
        # Arrange
        catalogue = snesst.MODELS

        # Act
        seen = [alias for model in catalogue.values() for alias in model.aliases]

        # Assert
        self.assertEqual(len(seen), len(set(seen)))


class DeclaredImageTest(unittest.TestCase):
    def manifest(self) -> Any:
        where = Path(__file__).resolve().parent / "artifacts.manifest.json"
        return json.loads(where.read_text())

    def test_every_part_runs_an_image_the_processor_declares(self) -> None:
        # Arrange
        declared = {one["part"] for one in self.manifest()["artifacts"]}

        # Act
        missing = [name for name, model in snesst.MODELS.items() if model.image not in declared]

        # Assert
        self.assertEqual(missing, [])

    def test_every_declared_image_carries_a_deciding_digest(self) -> None:
        # Arrange
        artifacts = self.manifest()["artifacts"]

        # Act
        widths = {len(accepted["sha256"]) for one in artifacts for accepted in one["accepted"]}

        # Assert
        self.assertEqual(widths, {64})

    def test_the_two_signal_processor_parts_run_the_same_processor(self) -> None:
        # Arrange
        declared = {one["part"]: one["processor"] for one in self.manifest()["artifacts"]}

        # Act
        found = {name: declared[model.image] for name, model in snesst.MODELS.items()}

        # Assert
        self.assertEqual(found, {"st010": "upd96050", "st011": "upd96050", "st018": "arm60"})


class DispatchTest(unittest.TestCase):
    def test_the_signal_processor_parts_are_built_by_the_class_that_runs_one(self) -> None:
        # Arrange
        model = "seta010"

        # Act
        found = built(model)

        # Assert
        self.assertIs(type(found), chip.Chip)

    def test_the_arm_part_is_built_by_the_class_that_runs_an_arm(self) -> None:
        # Arrange
        model = "setast018"

        # Act
        found = built_arm(model)

        # Assert
        self.assertIs(type(found), snesst.ST018)

    def test_the_two_arrangements_are_not_the_same_class(self) -> None:
        # Arrange
        model = "seta011"

        # Act
        found = built(model)

        # Assert
        self.assertNotIsInstance(found, snesst.ST018)


class NamingNoneTest(unittest.TestCase):
    def test_building_without_naming_a_model_is_refused_with_every_name(self) -> None:
        # Arrange
        expected = (
            "no model was named, and this package will not choose one for you."
            " Name one of: st010, st011, st018"
        )

        # Act
        with self.assertRaises(snesst.UnknownModelError) as caught:
            snesst.Chip()

        # Assert
        self.assertEqual(str(caught.exception), expected)

    def test_nothing_named_describe_is_published(self) -> None:
        # Arrange
        published = set(snesst.__all__)

        # Act
        found = "describe" in published or hasattr(snesst, "describe")

        # Assert
        self.assertIs(found, False)

    def test_and_no_default_model_is_published_either(self) -> None:
        # Arrange
        published = set(snesst.__all__)

        # Act
        found = "DEFAULT_MODEL" in published or hasattr(snesst, "DEFAULT_MODEL")

        # Assert
        self.assertIs(found, False)


if __name__ == "__main__":
    unittest.main()
