"""What a recorded shape means, and what replaying one at a part does."""

import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from conformance import shapes


class Recording:
    """A part that writes nothing down except what it was asked."""

    def __init__(self, answers: dict[int, int] | None = None) -> None:
        self.answers = answers or {}
        self.written: list[tuple[int, int]] = []
        self.taken: list[int] = []

    def write(self, address: int, value: int) -> None:
        self.written.append((address, value))

    def read(self, address: int) -> int:
        self.taken.append(address)
        return self.answers.get(address, 0)


class SpellingTest(unittest.TestCase):
    def test_a_step_prints_as_its_kind_its_width_and_where_it_landed(self) -> None:
        printed = repr(shapes.Step(shapes.WRITE, 2, 0x680020))

        self.assertEqual(printed, "write2@0x680020")

    def test_a_shape_spells_as_its_steps_in_order(self) -> None:
        spelled = shapes.spell(
            [shapes.Step(shapes.WRITE, 1, 0x600000), shapes.Step(shapes.READ, 1, 0x680010)]
        )

        self.assertEqual(spelled, "write1@0x600000 read1@0x680010")

    def test_spelling_and_parsing_are_the_same_journey_both_ways(self) -> None:
        steps = (shapes.Step(shapes.POLL, 1, 0x680021), shapes.Step(shapes.READ, 2, 0x680012))

        self.assertEqual(shapes.parse(shapes.spell(steps)), steps)

    def test_two_steps_that_say_the_same_thing_are_the_same_step(self) -> None:
        one = shapes.Step(shapes.READ, 1, 0x680010)

        self.assertEqual({one, shapes.Step(shapes.READ, 1, 0x680010)}, {one})

    def test_a_step_does_not_compare_equal_to_something_that_is_not_one(self) -> None:
        one = shapes.Step(shapes.READ, 1, 0x680010)

        self.assertNotEqual(one, "read1@0x680010")

    def test_only_a_write_or_a_read_carries_a_payload(self) -> None:
        moving = [
            shapes.Step(kind, 1, 0).moves for kind in (shapes.WRITE, shapes.READ, shapes.POLL)
        ]

        self.assertEqual(moving, [True, True, False])


class ParseTest(unittest.TestCase):
    def test_an_access_with_no_address_is_refused(self) -> None:
        with self.assertRaises(shapes.Malformed):
            shapes.parse("write1")

    def test_an_access_of_an_unknown_kind_is_refused(self) -> None:
        with self.assertRaises(shapes.Malformed):
            shapes.parse("shout1@0x680000")

    def test_an_access_that_does_not_say_how_wide_it_is_is_refused(self) -> None:
        with self.assertRaises(shapes.Malformed):
            shapes.parse("write@0x680000")

    def test_an_address_that_is_not_a_number_is_refused(self) -> None:
        with self.assertRaises(shapes.Malformed):
            shapes.parse("write1@nowhere")

    def test_a_shape_with_nothing_in_it_is_refused(self) -> None:
        with self.assertRaises(shapes.Malformed):
            shapes.parse("   ")


class RecordedTest(unittest.TestCase):
    def test_a_part_with_no_recorded_file_has_no_recorded_shapes(self) -> None:
        found = shapes.recorded("nosuchpart")

        self.assertEqual(found, ())

    def test_the_recorded_shapes_come_back_longest_first(self) -> None:
        found = shapes.recorded("st010")

        self.assertEqual(
            [len(steps) for steps, _ in found], sorted((len(s) for s, _ in found), reverse=True)
        )

    def test_every_recorded_shape_for_both_parts_parses(self) -> None:
        counted = sum(len(shapes.recorded(part)) for part in ("st010", "st011"))

        self.assertGreater(counted, 0)

    def test_a_shape_that_only_watches_is_not_worth_playing(self) -> None:
        held = ((shapes.parse("poll1@0x680021 poll1@0x680021"), 3),)

        self.assertEqual(shapes.interesting(held), ())

    def test_a_shape_that_moves_a_payload_is(self) -> None:
        held = ((shapes.parse("poll1@0x680021 read1@0x680010"), 3),)

        self.assertEqual(shapes.interesting(held), held)


class PayloadTest(unittest.TestCase):
    def test_one_run_of_bytes_is_generated_for_each_write(self) -> None:
        steps = shapes.parse("write1@0x680000 read2@0x680010 write2@0x680004")

        found = shapes.payload_for(steps, shapes.rolls())

        self.assertEqual([len(run) for run in found], [1, 2])

    def test_the_same_seed_generates_the_same_payload(self) -> None:
        steps = shapes.parse("write2@0x680000")

        first = shapes.payload_for(steps, shapes.rolls(7))

        self.assertEqual(first, shapes.payload_for(steps, shapes.rolls(7)))

    def test_a_different_seed_generates_a_different_one(self) -> None:
        steps = shapes.parse("write2@0x680000 write2@0x680002 write2@0x680004")

        first = shapes.payload_for(steps, shapes.rolls(7))

        self.assertNotEqual(first, shapes.payload_for(steps, shapes.rolls(8)))

    def test_the_generator_is_a_source_of_numbers(self) -> None:
        self.assertIsInstance(shapes.rolls(), random.Random)


class DriveTest(unittest.TestCase):
    def test_a_write_lands_at_the_address_the_shape_names(self) -> None:
        part = Recording()

        shapes.drive(part, shapes.parse("write1@0x680020"), [[0x7F]])

        self.assertEqual(part.written, [(0x680020, 0x7F)])

    def test_a_write_to_the_port_lands_there_rather_than_in_memory(self) -> None:
        part = Recording()

        shapes.drive(part, shapes.parse("write1@0x600000"), [[0x7F]])

        self.assertEqual(part.written, [(0x600000, 0x7F)])

    def test_a_wide_write_walks_upward_from_it(self) -> None:
        part = Recording()

        shapes.drive(part, shapes.parse("write2@0x680004"), [[0xAA, 0xBB]])

        self.assertEqual(part.written, [(0x680004, 0xAA), (0x680005, 0xBB)])

    def test_a_read_comes_back_as_the_bytes_the_part_held(self) -> None:
        part = Recording({0x680010: 0x93, 0x680011: 0x00})

        said = shapes.drive(part, shapes.parse("read2@0x680010"), [])

        self.assertEqual(said, [[0x93, 0x00]])

    def test_a_poll_reads_the_control_pair_the_same_way(self) -> None:
        part = Recording({0x680021: 0x80})

        said = shapes.drive(part, shapes.parse("poll1@0x680021"), [])

        self.assertEqual(said, [[0x80]])

    def test_a_shape_that_writes_and_reads_does_both_in_order(self) -> None:
        part = Recording({0x680010: 0x42})

        said = shapes.drive(part, shapes.parse("write1@0x680000 read1@0x680010"), [[0x01]])

        self.assertEqual((part.written, said), ([(0x680000, 0x01)], [[0x42]]))

    def test_the_contract_a_run_needs_is_smaller_than_a_part(self) -> None:
        self.assertIsInstance(Recording(), shapes.Addressed)


if __name__ == "__main__":
    unittest.main()
