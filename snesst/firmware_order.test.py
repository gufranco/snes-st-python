import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import snesst
from snesst import firmware

PROGRAM_WORDS = 16384

DATA_WORDS = 2048

ARM_PROGRAM_BYTES = 131072

ARM_DATA_BYTES = 32768


def a_program() -> bytes:
    program = b"".join((0xA00000 | at).to_bytes(3, "big") for at in range(PROGRAM_WORDS))
    table = b"".join((0x1234 + at).to_bytes(2, "big") for at in range(DATA_WORDS))
    return program + table


def low_byte_first(image: bytes) -> bytes:
    split = PROGRAM_WORDS * 3
    program = b"".join(image[at : at + 3][::-1] for at in range(0, split, 3))
    table = b"".join(image[at : at + 2][::-1] for at in range(split, len(image), 2))
    return program + table


def a_catalogue(image: bytes) -> dict[str, Any]:
    return {
        "artifacts": [
            {
                "part": "st010",
                "processor": "upd96050",
                "bytes": len(image),
                "programWords": PROGRAM_WORDS,
                "dataWords": DATA_WORDS,
                "accepted": [{"revision": "ST010", "sha256": hashlib.sha256(image).hexdigest()}],
            }
        ]
    }


def an_arm_catalogue(image: bytes) -> dict[str, Any]:
    return {
        "artifacts": [
            {
                "part": "st018",
                "processor": "arm60",
                "bytes": len(image),
                "programBytes": ARM_PROGRAM_BYTES,
                "dataBytes": ARM_DATA_BYTES,
                "accepted": [{"revision": "ST018", "sha256": hashlib.sha256(image).hexdigest()}],
            }
        ]
    }


def written(image: bytes) -> Path:
    where = Path(tempfile.mkdtemp()) / "dump.bin"
    where.write_bytes(image)
    return where


class LowByteFirstTest(unittest.TestCase):
    def test_a_dump_storing_each_word_low_byte_first_is_named_for_its_part(self) -> None:
        # Arrange
        image = a_program()

        # Act
        found = firmware.identify(low_byte_first(image), a_catalogue(image))

        # Assert
        self.assertEqual((found.part, found.low_byte_first), ("st010", True))

    def test_an_image_in_the_manifest_s_own_order_is_not_marked(self) -> None:
        # Arrange
        image = a_program()

        # Act
        found = firmware.identify(image, a_catalogue(image))

        # Assert
        self.assertIs(found.low_byte_first, False)

    def test_reading_such_a_dump_gives_the_bytes_in_the_manifest_s_order(self) -> None:
        # Arrange
        image = a_program()
        where = written(low_byte_first(image))
        identity = firmware.identify(where.read_bytes(), a_catalogue(image))

        # Act
        found = firmware.read(where, identity)

        # Assert
        self.assertEqual(hashlib.sha256(found).digest(), hashlib.sha256(image).digest())

    def test_reading_one_in_that_order_already_gives_it_back_unchanged(self) -> None:
        # Arrange
        image = a_program()
        where = written(image)
        identity = firmware.identify(image, a_catalogue(image))

        # Act
        found = firmware.read(where, identity)

        # Assert
        self.assertEqual(found, image)

    def test_a_part_measured_in_bytes_is_never_reordered(self) -> None:
        # Arrange
        image = bytes(range(256)) * ((ARM_PROGRAM_BYTES + ARM_DATA_BYTES) // 256)

        # Act
        def identifying() -> object:
            return firmware.identify(image[::-1], an_arm_catalogue(image))

        # Assert
        self.assertRaises(snesst.Unrecognised, identifying)

    def test_a_search_finds_such_a_dump_where_it_lies(self) -> None:
        # Arrange
        image = a_program()
        where = written(low_byte_first(image))

        # Act
        found = list(firmware.found(where.parent, a_catalogue(image)))

        # Assert
        self.assertEqual([(one.part, path) for one, path in found], [("st010", where)])

    def test_a_part_built_from_such_a_dump_runs_the_program_in_the_right_order(self) -> None:
        # Arrange
        image = a_program()
        where = written(low_byte_first(image))
        identity = firmware.identify(where.read_bytes(), a_catalogue(image))

        # Act
        part = snesst.Chip("st010", images={"st010": (identity, where)}, boot=0)

        # Assert
        self.assertEqual(
            (part.core.stores.program[1], part.core.stores.table[1]), (0xA00001, 0x1235)
        )


if __name__ == "__main__":
    unittest.main()
