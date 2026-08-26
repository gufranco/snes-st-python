"""Playing recorded cartridge exchanges at a part, and what the run reports."""

import contextlib
import json
import sys
import tempfile
import unittest
from collections.abc import Iterator
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from conformance import against_cartridges as against
from conformance import shapes


class Silent:
    """A part that answers zero to everything, which is what a dead one does."""

    def write(self, address: int, value: int) -> None:
        return None

    def read(self, address: int) -> int:
        return 0


class Echoing:
    """A part that hands back whatever was last put into that address."""

    def __init__(self, seed: int = 0x93) -> None:
        self.held: dict[int, int] = {}
        self.seed = seed

    def write(self, address: int, value: int) -> None:
        self.held[address] = value

    def read(self, address: int) -> int:
        return self.held.get(address, self.seed)


@contextlib.contextmanager
def _one_shape(shape: str) -> "Iterator[Path]":
    """A recorded file holding exactly the shape a test wants played."""
    with tempfile.TemporaryDirectory() as where:
        path = Path(where) / "made.json"
        path.write_text(json.dumps({"shapes": [{"shape": shape, "seen": 1}]}))
        yield path


class PlayedTest(unittest.TestCase):
    def test_a_run_that_got_a_nonzero_byte_back_answered(self) -> None:
        one = against.Played("read1@0x0010", [[0x01]], [shapes.READ])

        self.assertTrue(one.answered)

    def test_a_run_that_got_only_zeroes_back_did_not(self) -> None:
        one = against.Played("read1@0x0010", [[0x00]], [shapes.READ])

        self.assertFalse(one.answered)

    def test_a_ready_control_pair_is_not_an_answer(self) -> None:
        one = against.Played("poll1@0x0020", [[0xFF]], [shapes.POLL])

        self.assertFalse(one.answered)

    def test_a_shape_that_reads_asks_the_part_something(self) -> None:
        one = against.Played("read1@0x680268", [[0]], [shapes.READ])

        self.assertTrue(one.asks)

    def test_a_shape_that_only_writes_asks_it_nothing(self) -> None:
        one = against.Played("write1@0x680000", [], [])

        self.assertFalse(one.asks)

    def test_a_shape_that_only_polls_asks_it_nothing_either(self) -> None:
        one = against.Played("poll1@0x680020", [[0]], [shapes.POLL])

        self.assertFalse(one.asks)

    def test_a_run_prints_as_its_shape_and_how_much_came_back(self) -> None:
        one = against.Played("read1@0x0010", [[1]], [shapes.READ])

        self.assertIn("read1@0x0010", repr(one))


class DrivenTest(unittest.TestCase):
    def test_every_recorded_shape_for_a_part_is_played(self) -> None:
        held = shapes.interesting(shapes.recorded("st010"))

        found = against.driven("st010", lambda part: Echoing())

        self.assertEqual(len(found), len(held))

    def test_a_part_answering_something_leaves_nothing_silent(self) -> None:
        found = against.driven("st010", lambda part: Echoing())

        self.assertEqual(against.silent(found), [])

    def test_a_part_answering_nothing_leaves_prompted_shapes_silent(self) -> None:
        found = against.driven("st010", lambda part: Silent())

        self.assertNotEqual(against.silent(found), [])

    def test_a_shape_that_never_reads_is_not_counted_as_silence(self) -> None:
        found = against.driven("st010", lambda part: Silent())

        for one in against.wordless(found):
            self.assertNotIn(one, against.silent(found))

    def test_a_part_with_no_recorded_shapes_is_refused(self) -> None:
        with self.assertRaises(against.Usage):
            against.driven("nosuchpart", lambda part: Echoing())

    def test_the_same_seed_drives_the_same_run(self) -> None:
        first = against.driven("st011", lambda part: Echoing())

        self.assertEqual(
            [one.said for one in first],
            [one.said for one in against.driven("st011", lambda part: Echoing())],
        )


class ReportTest(unittest.TestCase):
    def test_the_lines_name_the_part_and_how_many_exchanges_were_played(self) -> None:
        found = against.driven("st011", lambda part: Echoing())

        lines = against.lines_for(found, "st011")

        self.assertIn("st011", lines[0])

    def test_the_run_says_how_many_answered_and_how_many_did_not(self) -> None:
        found = against.driven("st011", lambda part: Silent())

        lines = against.lines_for(found, "st011")

        self.assertTrue(any("got something back" in line for line in lines))

    def test_a_shape_that_never_reads_is_listed_apart_from_silence(self) -> None:
        found = against.driven("st010", lambda part: Silent())

        lines = against.lines_for(found, "st010")

        self.assertTrue(any("never read" in line for line in lines))

    def test_a_run_where_every_shape_reads_lists_nothing_apart(self) -> None:
        with _one_shape("read1@0x680010") as where:
            found = against.driven("st010", lambda part: Echoing(), where=where)

        lines = against.lines_for(found, "st010")

        self.assertFalse(any("never read" in line for line in lines))

    def test_a_run_is_shown_with_the_bytes_that_came_back(self) -> None:
        with _one_shape("read1@0x680010") as where:
            found = against.driven("st010", lambda part: Echoing(0x5A), where=where)

        self.assertIn("0x5a", against.report(found)[0])

    def test_no_more_than_a_handful_of_lines_are_printed(self) -> None:
        found = against.driven("st010", lambda part: Echoing())

        self.assertLessEqual(len(against.report(found)), against.SHOWN)


class MainTest(unittest.TestCase):
    def test_a_machine_with_no_microcode_says_so_and_stops(self) -> None:
        said: list[str] = []

        code = against.main([], why_not=lambda: "no image here", say=said.append)

        self.assertEqual((code, "nothing was driven" in said[0]), (2, True))

    def test_a_part_that_answers_reports_success(self) -> None:
        said: list[str] = []

        code = against.main(
            ["st010"], why_not=lambda: None, build=lambda part: Echoing(), say=said.append
        )

        self.assertEqual(code, 0)

    def test_a_part_that_says_nothing_reports_failure(self) -> None:
        said: list[str] = []

        code = against.main(
            ["st011"], why_not=lambda: None, build=lambda part: Silent(), say=said.append
        )

        self.assertEqual(code, 1)

    def test_with_no_part_named_it_drives_the_first_one(self) -> None:
        said: list[str] = []

        against.main([], why_not=lambda: None, build=lambda part: Echoing(), say=said.append)

        self.assertIn(against.DEFAULT_PART, said[0])


if __name__ == "__main__":
    unittest.main()
