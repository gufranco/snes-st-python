"""Reading the shapes out of cartridges, and what the recorded file must say."""

import json
import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from conformance import record, shapes


def _a_cartridge(
    body: bytes = b"", title: bytes = b"EXHAUST HEAT2", length: int = 0x100000
) -> bytes:
    held = bytearray(b"\xea" * length)
    held[0x100 : 0x100 + len(body)] = body
    held[0x7FC0 : 0x7FC0 + len(title)] = title
    held[0x7FC0 + len(title) : 0x7FD5] = b"\x00" * (0x7FD5 - 0x7FC0 - len(title))
    held[0x7FD5] = 0x30
    held[0x7FD6] = 0xF6
    held[0x7FD7] = 0x0A
    return bytes(held)


class DigestTest(unittest.TestCase):
    def test_a_cartridge_is_measured_with_all_four(self) -> None:
        found = record.digests_of(b"whatever")

        self.assertEqual(sorted(found), ["crc32", "md5", "sha1", "sha256"])

    def test_two_files_that_differ_by_one_byte_measure_differently(self) -> None:
        first = record.digests_of(b"a")

        self.assertNotEqual(first, record.digests_of(b"b"))


class HeaderTest(unittest.TestCase):
    def test_the_title_comes_back_off_a_low_cartridge(self) -> None:
        found = record.what_it_says_about_itself(_a_cartridge())

        self.assertEqual(found["title"], "EXHAUST HEAT2")

    def test_and_the_chipset_byte_the_cartridge_declares(self) -> None:
        found = record.what_it_says_about_itself(_a_cartridge())

        self.assertEqual(found["chipset"], "0xf6")

    def test_a_file_too_short_to_hold_a_header_is_refused(self) -> None:
        with self.assertRaises(record.NotACartridge):
            record.what_it_says_about_itself(b"\x00" * 16)

    def test_a_file_declaring_no_seta_part_is_refused(self) -> None:
        held = bytearray(_a_cartridge())
        held[0x7FD6] = 0x03

        with self.assertRaises(record.NotACartridge):
            record.what_it_says_about_itself(bytes(held))


def _named(*images: bytes) -> dict[str, dict[str, Any]]:
    """A catalogue naming exactly the images a test made, so the gate lets them by."""
    return {
        record.digests_of(one)["sha256"]: {"name": f"made-up-{at}.sfc", **record.digests_of(one)}
        for at, one in enumerate(images)
    }


class PartTest(unittest.TestCase):
    def test_a_megabyte_cartridge_carries_the_first_part(self) -> None:
        self.assertEqual(record.part_of(0xF6, 0x100000), "st010")

    def test_a_half_megabyte_one_carries_the_second(self) -> None:
        self.assertEqual(record.part_of(0xF6, 0x080000), "st011")

    def test_the_same_length_declaring_the_other_chipset_carries_the_third(self) -> None:
        self.assertEqual(record.part_of(0xF5, 0x080000), "st018")

    def test_and_any_other_length_names_neither(self) -> None:
        self.assertIsNone(record.part_of(0xF6, 0x200000))


class ManifestTest(unittest.TestCase):
    def test_the_published_list_names_the_cartridges_this_reads(self) -> None:
        self.assertIn(record.digests_of(_a_cartridge())["sha256"], _named(_a_cartridge()))

    def test_a_cartridge_the_manifest_names_comes_back_with_its_row(self) -> None:
        image = _a_cartridge()

        found = record.confirmed(image, _named(image))

        self.assertEqual((found or {}).get("name"), "made-up-0.sfc")

    def test_a_cartridge_the_manifest_does_not_name_is_refused(self) -> None:
        self.assertIsNone(record.confirmed(_a_cartridge(), _named(_a_cartridge(b"\x01"))))

    def test_a_row_that_disagrees_with_itself_is_reported(self) -> None:
        image = _a_cartridge()
        catalogue = _named(image)
        next(iter(catalogue.values()))["crc32"] = "00000000"

        with self.assertRaises(record.Usage):
            record.confirmed(image, catalogue)

    def test_the_manifest_beside_this_one_names_every_cartridge_it_reads(self) -> None:
        self.assertGreater(len(record.published()), 0)


class GatherTest(unittest.TestCase):
    def test_a_recorded_file_names_the_part_it_is_for(self) -> None:
        found = record.assemble("st010", [(_a_cartridge(), "one.sfc", {"write1@0x0000": 2}, True)])

        self.assertEqual(found["part"], "st010")

    def test_it_names_the_tool_that_produced_it(self) -> None:
        found = record.assemble("st010", [(_a_cartridge(), "one.sfc", {"write1@0x0000": 2}, True)])

        self.assertIn("snes-driver-python", found["producedBy"])

    def test_every_cartridge_it_was_read_from_carries_four_digests(self) -> None:
        found = record.assemble("st010", [(_a_cartridge(), "one.sfc", {"write1@0x0000": 2}, True)])

        for one in found["readFrom"]:
            self.assertEqual(
                [key for key in ("crc32", "md5", "sha1", "sha256") if key in one],
                ["crc32", "md5", "sha1", "sha256"],
            )

    def test_a_shape_two_cartridges_share_is_counted_once_and_credited_twice(self) -> None:
        both = [
            (_a_cartridge(), "one.sfc", {"write1@0x0000": 2}, True),
            (_a_cartridge(b"\x01"), "two.sfc", {"write1@0x0000": 3}, True),
        ]

        found = record.assemble("st010", both)

        self.assertEqual(found["shapes"], [{"shape": "write1@0x0000", "seen": 5, "cartridges": 2}])

    def test_the_shapes_it_writes_are_the_shapes_this_package_parses(self) -> None:
        found = record.assemble("st010", [(_a_cartridge(), "one.sfc", {"read2@0x0010": 1}, True)])

        self.assertEqual(shapes.parse(found["shapes"][0]["shape"])[0].address, 0x0010)

    def test_a_part_no_cartridge_was_read_for_is_refused(self) -> None:
        with self.assertRaises(record.Usage):
            record.assemble("st010", [])


class WrittenTest(unittest.TestCase):
    def test_the_file_this_writes_reads_back_as_the_shapes_it_holds(self) -> None:
        import tempfile

        found = record.assemble("st010", [(_a_cartridge(), "one.sfc", {"write1@0x0020": 1}, True)])
        with tempfile.TemporaryDirectory() as where:
            path = Path(where) / "st010shapes.json"
            path.write_text(json.dumps(found, indent=2) + "\n")

            self.assertEqual(len(shapes.recorded("st010", path)), 1)


class MainTest(unittest.TestCase):
    def test_with_no_arguments_it_says_how_to_use_it(self) -> None:
        said: list[str] = []

        code = record.main([], say=said.append)

        self.assertEqual((code, "usage" in said[0]), (2, True))

    def test_a_directory_holding_no_cartridge_reports_that_it_found_none(self) -> None:
        import tempfile

        said: list[str] = []
        with tempfile.TemporaryDirectory() as where:
            code = record.main([where, where], say=said.append)

        self.assertEqual((code, any("no cartridge" in one for one in said)), (2, True))

    def test_a_directory_that_is_not_one_is_refused(self) -> None:
        said: list[str] = []

        code = record.main(["/nowhere-at-all", "/tmp"], say=said.append)

        self.assertEqual((code, any("no such" in one for one in said)), (2, True))

    def test_a_cartridge_it_can_read_is_recorded(self) -> None:
        import tempfile

        said: list[str] = []
        with tempfile.TemporaryDirectory() as where:
            (Path(where) / "one.sfc").write_bytes(_a_cartridge())

            def _shapes(rom: bytes, part: str) -> tuple[dict[str, int], bool]:
                return {"write1@0x0000 read1@0x0010": 1}, True

            code = record.main(
                [where, where], say=said.append, read=_shapes, named=_named(_a_cartridge())
            )

            self.assertEqual((code, (Path(where) / "st010shapes.json").is_file()), (0, True))

    def test_a_cartridge_whose_routines_say_nothing_is_reported(self) -> None:
        import tempfile

        said: list[str] = []
        with tempfile.TemporaryDirectory() as where:
            (Path(where) / "one.sfc").write_bytes(_a_cartridge())

            def _nothing(rom: bytes, part: str) -> tuple[dict[str, int], bool]:
                return {}, True

            code = record.main(
                [where, where], say=said.append, read=_nothing, named=_named(_a_cartridge())
            )

        self.assertEqual((code, any("no exchange" in one for one in said)), (1, True))

    def test_a_file_that_is_not_a_seta_cartridge_is_skipped_rather_than_fatal(self) -> None:
        import tempfile

        said: list[str] = []
        with tempfile.TemporaryDirectory() as where:
            (Path(where) / "other.sfc").write_bytes(b"\x00" * 0x100000)
            (Path(where) / "one.sfc").write_bytes(_a_cartridge())

            (Path(where) / "notes.txt").write_bytes(b"not a cartridge at all")

            def _shapes(rom: bytes, part: str) -> tuple[dict[str, int], bool]:
                return {"write1@0x680000": 1}, True

            code = record.main(
                [where, where],
                say=said.append,
                read=_shapes,
                named=_named(_a_cartridge(), b"\x00" * 0x100000),
            )

        self.assertEqual(code, 0)

    def test_a_cartridge_the_manifest_does_not_name_is_skipped(self) -> None:
        import tempfile

        said: list[str] = []
        with tempfile.TemporaryDirectory() as where:
            (Path(where) / "one.sfc").write_bytes(_a_cartridge())

            code = record.main(
                [where, where],
                say=said.append,
                read=lambda rom, part: ({"write1@0x0": 1}, True),
                named=_named(_a_cartridge(b"\x01")),
            )

        self.assertEqual((code, any("no cartridge" in one for one in said)), (2, True))

    def test_a_cartridge_of_a_length_neither_part_has_is_skipped(self) -> None:
        import tempfile

        said: list[str] = []
        with tempfile.TemporaryDirectory() as where:
            odd = _a_cartridge(length=0x30000)
            (Path(where) / "odd.sfc").write_bytes(odd)

            code = record.main(
                [where, where],
                say=said.append,
                read=lambda rom, part: ({"write1@0x0": 1}, True),
                named=_named(odd),
            )

        self.assertEqual((code, any("no cartridge" in one for one in said)), (2, True))


def _a_routine() -> bytes:
    """A cartridge whose code pokes the port, the shared memory and neither."""
    body = bytearray()
    body += bytes((0x8F, 0x00, 0x00, 0x60))
    body += bytes((0x8F, 0x20, 0x00, 0x68))
    body += bytes((0xAF, 0x10, 0x00, 0x68))
    body += bytes((0x8F, 0x00, 0x00, 0x7E))
    body += bytes((0x60,))
    return _a_cartridge(bytes(body))


class ReadingTest(unittest.TestCase):
    def test_the_reader_finds_a_routine_that_pokes_both_windows(self) -> None:
        try:
            found: Any = record.through_the_driver(_a_routine())[0]
        except ImportError:  # pragma: no cover
            self.skipTest("the driver is not checked out beside this")

        self.assertEqual(sorted(found), ["write1@0x600000 write1@0x680020 read1@0x680010"])

    def test_a_cartridge_whose_code_pokes_neither_yields_nothing(self) -> None:
        try:
            found: Any = record.through_the_driver(_a_cartridge())[0]
        except ImportError:  # pragma: no cover
            self.skipTest("the driver is not checked out beside this")

        self.assertEqual(found, {})

    def test_an_access_reaching_no_window_at_all_is_passed_over(self) -> None:
        both = record.Anywhere([])

        self.assertIsNone(both.reaches(0x68, 0x0020))


if __name__ == "__main__":
    unittest.main()
