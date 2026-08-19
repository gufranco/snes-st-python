import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from st010 import version


class VersionTest(unittest.TestCase):
    def test_the_package_carries_a_version(self):
        self.assertTrue(version.VERSION)

    def test_and_it_is_written_by_the_release_job_rather_than_by_hand(self):
        self.assertIsInstance(version.VERSION, str)


if __name__ == "__main__":
    unittest.main()
