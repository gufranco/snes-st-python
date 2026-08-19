import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import st010
from st010 import models


class CatalogueTest(unittest.TestCase):
    def test_the_package_names_every_model_it_covers(self):
        self.assertEqual(set(models.MODELS), {"st010"})

    def test_a_model_says_what_it_is_and_what_it_holds(self):
        found = models.describe("st010")

        self.assertTrue(found.summary)
        self.assertEqual(found.memory_bytes, 0x1000)

    def test_a_model_name_is_matched_however_it_is_written(self):
        for written in ("ST010", "st-010", "ST_010", "seta-st010"):
            self.assertEqual(models.describe(written).name, "st010")

    def test_the_other_part_of_the_family_is_refused_by_name(self):
        with self.assertRaises(models.UnknownModelError):
            models.describe("st011")

    def test_and_the_refusal_says_why_rather_than_only_that(self):
        with self.assertRaises(models.UnknownModelError) as raised:
            models.describe("st011")

        self.assertIn("st011", str(raised.exception))

    def test_the_refusal_lists_what_is_available(self):
        with self.assertRaises(models.UnknownModelError) as raised:
            models.describe("nonsense")

        self.assertIn("st010", str(raised.exception))

    def test_a_model_prints_as_its_name_and_size(self):
        printed = repr(models.describe("st010"))

        self.assertIn("st010", printed)
        self.assertIn("4096", printed)


class BuildTest(unittest.TestCase):
    def test_a_chip_is_built_from_its_model_name(self):
        self.assertEqual(st010.Seta(model="st010").model, "st010")

    def test_the_default_model_is_the_one_the_cartridge_carries(self):
        self.assertEqual(st010.Seta().model, "st010")

    def test_options_reach_the_chip_that_gets_built(self):
        built = st010.Seta(memory=bytes([0xAA]) * 0x1000)

        self.assertEqual(built.memory[0], 0xAA)

    def test_a_model_the_package_does_not_have_is_refused_at_construction(self):
        with self.assertRaises(models.UnknownModelError):
            st010.Seta(model="st011")


if __name__ == "__main__":
    unittest.main()
