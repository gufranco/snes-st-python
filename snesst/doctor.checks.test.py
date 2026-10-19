import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from snesst import doctor, firmware

PROCESSOR = str(Path(__file__).resolve().parent.parent / "nec-upd7725-96050-python")


class DigestTest(unittest.TestCase):
    def _catalogue(self, where: Path) -> "dict[str, tuple[object, Path]]":
        return {"st010": (firmware.Identity("st010", "upd7725", "MADE UP", 8, 8), where)}

    def test_a_part_whose_file_is_here_reports_its_digest(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp()) / "made-up.bin"
        where.write_bytes(b"nothing anybody owns")
        catalogue = self._catalogue(where)

        # Act
        found = doctor.digest_of("st010", catalogue)

        # Assert
        self.assertEqual(
            found, ", sha256 d57911c29fed03d95df95d0745a8a78c1cc6e0aa2bdcea932911435909f28c17"
        )

    def test_a_dump_storing_each_word_low_byte_first_reports_the_bytes_it_runs(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp()) / "made-up.bin"
        where.write_bytes(bytes(range(1, 9)))
        turned = firmware.Identity("st010", "upd7725", "MADE UP", 2, 1, low_byte_first=True)

        # Act
        found = doctor.digest_of("st010", {"st010": (turned, where)})

        # Assert
        self.assertEqual(
            found,
            ", sha256 27bc0714ef81fd9981322af16d7cc2467eda4b01d28ab1e6be80cbbcab3376df,"
            " read from a file that stores each word low byte first",
        )

    def test_a_file_that_cannot_be_read_says_so_rather_than_going_quiet(self) -> None:
        # Arrange
        catalogue = self._catalogue(Path("/nowhere/at/all.bin"))

        # Act
        found = doctor.digest_of("st010", catalogue)

        # Assert
        self.assertIn("could not be read", found)

    def test_a_catalogue_with_nothing_in_it_reports_no_digest(self) -> None:
        # Arrange
        nothing: dict[str, tuple[object, Path]] = {}

        # Act
        found = doctor.digest_of("st010", nothing)

        # Assert
        self.assertEqual(found, "")

    def test_and_a_catalogue_that_is_not_one_at_all_does_the_same(self) -> None:
        # Arrange
        missing = None

        # Act
        found = doctor.digest_of("st010", missing)

        # Assert
        self.assertEqual(found, "")


class ReachTest(unittest.TestCase):
    def test_a_path_without_it_gains_it(self) -> None:
        # Arrange
        path: list[str] = []

        # Act
        found = doctor.reach_processor(path)

        # Assert
        self.assertEqual(found, [PROCESSOR])

    def test_a_path_that_already_has_it_is_left_alone(self) -> None:
        # Arrange
        path = [PROCESSOR, "somewhere else"]

        # Act
        found = doctor.reach_processor(path)

        # Assert
        self.assertEqual(found, [PROCESSOR, "somewhere else"])

    def test_by_default_it_works_on_the_real_one(self) -> None:
        # Arrange
        wanted = PROCESSOR

        # Act
        found = doctor.reach_processor()

        # Assert
        self.assertIn(wanted, found)


class WaitsTest(unittest.TestCase):
    def test_a_part_that_will_not_build_is_reported_rather_than_raised(self) -> None:
        # Arrange
        def boom(part: str, images: Any) -> Any:
            raise RuntimeError("the core exploded")

        # Act
        found = doctor.check_waits(boom, {"st010": (None, Path("nowhere"))})

        # Assert
        self.assertEqual((found.ok, found.detail), (False, "RuntimeError: the core exploded"))

    def test_a_machine_with_no_image_says_nothing_was_run(self) -> None:
        # Arrange
        nothing: dict[str, tuple[object, Path]] = {}

        # Act
        found = doctor.check_waits(images=nothing)

        # Assert
        self.assertEqual((found.ok, found.detail), (True, "no image is here, so nothing was run"))

    def test_and_a_part_that_builds_reports_where_it_stopped(self) -> None:
        # Arrange
        def waiting(part: str, images: Any) -> Any:
            return SimpleNamespace(core=SimpleNamespace(registers=SimpleNamespace(pc=3)))

        # Act
        found = doctor.check_waits(waiting, {"st010": (None, Path("nowhere"))})

        # Assert
        self.assertEqual((found.ok, found.detail), (True, "st010 waits at 3"))


class ReachableTest(unittest.TestCase):
    def test_a_root_that_is_not_on_the_path_is_put_there(self) -> None:
        # Arrange
        path: list[str] = []

        # Act
        added = doctor.reachable(Path("/somewhere"), path)

        # Assert
        self.assertEqual((added, path), (True, ["/somewhere"]))

    def test_a_root_already_on_the_path_is_left_alone(self) -> None:
        # Arrange
        path = ["/somewhere"]

        # Act
        added = doctor.reachable(Path("/somewhere"), path)

        # Assert
        self.assertEqual((added, path), (False, ["/somewhere"]))


if __name__ == "__main__":
    unittest.main()
