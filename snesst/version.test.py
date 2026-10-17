import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import snesst

SEMANTIC_VERSION = r"\d+\.\d+\.\d+"


class VersionTest(unittest.TestCase):
    def test_the_package_carries_a_semantic_version(self) -> None:
        # Arrange
        pattern = re.compile(SEMANTIC_VERSION)

        # Act
        found = pattern.fullmatch(snesst.__version__)

        # Assert
        self.assertIsNotNone(found)


if __name__ == "__main__":
    unittest.main()
