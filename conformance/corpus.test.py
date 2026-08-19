import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import corpus

from st010 import chip as st010


class CaseTest(unittest.TestCase):
    def test_a_case_starts_from_a_whole_memory(self):
        self.assertEqual(len(corpus.arguments_for(0)), corpus.MEMORY_BYTES)

    def test_the_same_seed_builds_the_same_case(self):
        self.assertEqual(corpus.arguments_for(3), corpus.arguments_for(3))

    def test_seeds_walk_the_commands_in_turn(self):
        found = [corpus.command_for(seed) for seed in range(len(corpus.COMMANDS))]

        self.assertEqual(found, list(corpus.COMMANDS))

    def test_and_one_seed_in_nine_asks_for_a_command_that_does_not_exist(self):
        self.assertEqual(corpus.command_for(len(corpus.COMMANDS)), corpus.UNKNOWN)

    def test_every_command_the_chip_has_is_reached(self):
        reached = {corpus.command_for(seed) for seed in range(corpus.CASES)}

        for command in corpus.COMMANDS:
            self.assertIn(command, reached)

    def test_the_steering_command_is_run_more_than_once(self):
        seed = corpus.COMMANDS.index(st010.NAVIGATE)

        self.assertEqual(corpus.runs_for(seed), corpus.NAVIGATION_STEPS)

    def test_and_every_other_command_once(self):
        seed = corpus.COMMANDS.index(st010.MULTIPLY)

        self.assertEqual(corpus.runs_for(seed), 1)


class ScriptTest(unittest.TestCase):
    def test_a_script_opens_by_clearing_the_chip(self):
        self.assertTrue(corpus.script_for(0).startswith("reset\n"))

    def test_and_then_lets_it_listen_to_its_registers(self):
        self.assertIn("w 0 0", corpus.script_for(0))

    def test_it_ends_by_asking_for_the_whole_memory(self):
        self.assertTrue(corpus.script_for(0).endswith("dump\n"))

    def test_a_script_only_pokes_the_bytes_that_are_not_already_clear(self):
        seed = corpus.COMMANDS.index(st010.MULTIPLY)
        pokes = [line for line in corpus.script_for(seed).splitlines() if line.startswith("poke")]

        self.assertLess(len(pokes), corpus.MEMORY_BYTES)

    def test_the_steering_script_starts_its_command_once_per_step(self):
        seed = corpus.COMMANDS.index(st010.NAVIGATE)
        starts = [
            line
            for line in corpus.script_for(seed).splitlines()
            if line.startswith(f"w {st010.ENABLE_BIT | st010.START_REGISTER}")
        ]

        self.assertEqual(len(starts), corpus.NAVIGATION_STEPS)


class ReplayTest(unittest.TestCase):
    def test_replaying_a_case_answers_a_whole_memory(self):
        self.assertEqual(len(corpus.replay(0)), corpus.MEMORY_BYTES)

    def test_the_same_case_replays_the_same_way(self):
        self.assertEqual(corpus.replay(1), corpus.replay(1))

    def test_a_case_leaves_the_command_registers_clear(self):
        found = corpus.replay(corpus.COMMANDS.index(st010.MULTIPLY))

        self.assertEqual(found[st010.START_REGISTER], 0)


class CorpusTest(unittest.TestCase):
    def test_the_corpus_that_ships_holds_cases(self):
        self.assertTrue(corpus.load()["cases"])

    def test_every_case_names_its_seed_and_its_expected_answer(self):
        for case in corpus.load()["cases"]:
            self.assertIn("seed", case)
            self.assertIn("expected", case)

    def test_the_corpus_says_where_its_answers_came_from(self):
        self.assertIn("reference", corpus.load())

    def test_a_corpus_can_be_read_from_somewhere_else(self):
        where = Path(tempfile.mkdtemp()) / "other.json"
        where.write_text(json.dumps({"reference": "x", "cases": []}))

        self.assertEqual(corpus.load(where)["cases"], [])

    def test_every_command_appears_among_the_recorded_seeds(self):
        reached = {corpus.command_for(case["seed"]) for case in corpus.load()["cases"]}

        for command in corpus.COMMANDS:
            self.assertIn(command, reached)


class ComparisonTest(unittest.TestCase):
    def test_two_identical_memories_report_nothing(self):
        self.assertIsNone(corpus.disagreement(b"\x01\x02", b"\x01\x02"))

    def test_a_byte_that_differs_is_named_with_its_address(self):
        self.assertEqual(corpus.disagreement(b"\x01\x02", b"\x01\x03"), (1, 2, 3))

    def test_a_memory_that_stops_early_is_reported(self):
        self.assertEqual(corpus.disagreement(b"\x01\x02", b"\x01")[0], 1)


class EncodingTest(unittest.TestCase):
    def test_a_memory_survives_being_written_down_and_read_back(self):
        self.assertEqual(corpus.expected_of({"expected": corpus.encode(b"\x01\x02")}), b"\x01\x02")


class AgainstCorpusTest(unittest.TestCase):
    def test_the_model_reproduces_every_memory_the_reference_left(self):
        for case in corpus.load()["cases"]:
            found = corpus.disagreement(corpus.expected_of(case), corpus.replay(case["seed"]))

            self.assertIsNone(found, f"seed {case['seed']}")


class RunTest(unittest.TestCase):
    def test_a_full_run_reports_clean(self):
        self.assertEqual(corpus.run([]), 0)

    def test_a_corpus_whose_answers_are_wrong_makes_the_run_fail(self):
        where = Path(tempfile.mkdtemp()) / "wrong.json"
        where.write_text(
            json.dumps(
                {"reference": "x", "cases": [{"seed": 0, "expected": corpus.encode(b"\x00")}]}
            )
        )

        self.assertEqual(corpus.run(["--corpus", str(where)]), 1)

    def test_a_corpus_of_many_wrong_answers_stops_reporting_after_a_handful(self):
        where = Path(tempfile.mkdtemp()) / "wrong.json"
        cases = [
            {"seed": seed, "expected": corpus.encode(b"\x00")}
            for seed in range(corpus.REPORT_LIMIT + 3)
        ]
        where.write_text(json.dumps({"reference": "x", "cases": cases}))

        self.assertEqual(corpus.run(["--corpus", str(where)]), 1)

    def test_an_option_it_does_not_know_is_refused(self):
        with self.assertRaises(corpus.Usage):
            corpus.options(["--nonsense"])

    def test_an_option_with_no_value_is_refused(self):
        with self.assertRaises(corpus.Usage):
            corpus.options(["--corpus"])

    def test_a_case_count_is_taken_as_a_number(self):
        self.assertEqual(corpus.options(["--cases", "7"]).cases, 7)


class RecordTest(unittest.TestCase):
    def scripted(self, body):
        where = Path(tempfile.mkdtemp()) / "fake"
        where.write_text(body)
        where.chmod(where.stat().st_mode | stat.S_IXUSR)
        return where

    def answering(self, cases=1):
        dump = "00" * corpus.MEMORY_BYTES
        echo = "\\n".join([dump] * cases)
        return self.scripted(f"#!/bin/sh\ncat > /dev/null\nprintf '{echo}\\n'\n")

    def test_a_driver_that_fails_is_reported_rather_than_recorded(self):
        wrong = self.scripted("#!/bin/sh\ncat > /dev/null\nexit 1\n")

        with self.assertRaises(corpus.Usage):
            corpus.ask([0], str(wrong))

    def test_a_driver_that_answers_the_wrong_number_of_cases_is_reported(self):
        with self.assertRaises(corpus.Usage):
            corpus.ask([0, 1], str(self.answering(cases=1)))

    def test_recording_asks_the_driver_for_every_case(self):
        found = corpus.record(str(self.answering(cases=3)), 3)

        self.assertEqual(len(found["cases"]), 3)

    def test_and_says_where_the_answers_came_from(self):
        found = corpus.record(str(self.answering()), 1)

        self.assertIn("reference", found)

    def test_recording_writes_the_corpus_where_it_was_asked(self):
        where = Path(tempfile.mkdtemp()) / "recorded.json"

        answered = corpus.run(
            [
                "--record",
                "--driver",
                str(self.answering(cases=2)),
                "--corpus",
                str(where),
                "--cases",
                "2",
            ]
        )

        self.assertEqual(answered, 0)
        self.assertEqual(len(json.loads(where.read_text())["cases"]), 2)


class EntryTest(unittest.TestCase):
    def test_a_run_from_the_command_line_returns_what_the_run_returned(self):
        self.assertEqual(corpus.main([]), 0)

    def test_an_option_it_does_not_know_is_reported(self):
        self.assertEqual(corpus.main(["--nonsense"]), 2)


if __name__ == "__main__":
    unittest.main()
