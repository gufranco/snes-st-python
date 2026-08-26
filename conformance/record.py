"""Read the shapes out of the cartridges that carry these parts.

Run once, against copies you own, to produce the two files
`conformance/st010shapes.json` and `conformance/st011shapes.json`. What it writes
is the sequence of accesses each driver routine makes, with a name, a length and
four digests for every cartridge it read. No byte any cartridge carries is
recorded and none can be recovered from what is.

**Which part a cartridge carries.** The header does not say. All three declare
the same chipset byte and the same layout, so the length decides: the two racing
games are a megabyte and carry the ST010, the shougi game is half that and
carries the ST011. That is a rule rather than a reading, and it is written here
rather than left implied.

**Why it is not run by the conformance suite.** It needs cartridges, which nobody
can be assumed to hold, and its output is checked into the repository so that a
machine holding none can still play the shapes at the part.

Usage: python3 conformance/record.py <directory of cartridges> <output directory>
"""

import collections
import hashlib
import json
import sys
import zlib
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

HEADER_AT = 0x7FC0
"""Where a low cartridge keeps the header, which is where all three keep theirs."""

TITLE_BYTES = 21

SETA = 0xF6
"""The chipset byte all three cartridges declare."""

BY_LENGTH = {0x100000: "st010", 0x080000: "st011"}

DRIVER = "https://github.com/gufranco/snes-driver-python"

SUFFIXES = (".sfc", ".smc")


class NotACartridge(Exception):
    """A file that is not one of the cartridges this reads."""


class Usage(Exception):
    """The tool was asked for something it cannot produce."""


def digests_of(image: bytes) -> dict[str, str]:
    """The four a manifest publishes, so a reader can cross-check any of them."""
    return {
        "crc32": f"{zlib.crc32(image):08x}",
        "md5": hashlib.md5(image).hexdigest(),
        "sha1": hashlib.sha1(image).hexdigest(),
        "sha256": hashlib.sha256(image).hexdigest(),
    }


def describe(image: bytes) -> dict[str, Any]:
    """What the cartridge says about itself, or a refusal naming why not."""
    if len(image) < HEADER_AT + 32:
        raise NotACartridge("too short to hold a header where a low cartridge keeps one")
    title = image[HEADER_AT : HEADER_AT + TITLE_BYTES].decode("shift_jis", "replace")
    chipset = image[HEADER_AT + 22]
    if chipset != SETA:
        raise NotACartridge(f"declares chipset {chipset:#04x}, and a Seta part is {SETA:#04x}")
    return {
        "title": title.strip("\x00 "),
        "bytes": len(image),
        "layout": "lorom",
        "chipset": f"{chipset:#04x}",
    }


def part_of(length: int) -> str | None:
    """Which part a cartridge of that length carries, if either."""
    return BY_LENGTH.get(length)


LAYOUTS = ("lorom", "lorom-shared")
"""Both windows the part answers in, because a routine uses whichever it needs."""


class Anywhere:
    """Several windows asked as one, so a routine is walked once rather than twice.

    A routine that leaves a parameter in the shared memory and then pokes the
    port is one exchange. Walking it once per window would report two halves,
    and neither half on its own starts the part.
    """

    def __init__(self, covered: "Sequence[Any]") -> None:
        self.covered = tuple(covered)

    def reaches(self, bank: int, address: int) -> str | None:
        """Which register an access lands on, in whichever window covers it."""
        for one in self.covered:
            found = one.reaches(bank, address)
            if found is not None:
                return str(found)
        return None


def through_the_driver(image: bytes) -> dict[str, int]:
    """Every distinct exchange in one image, read out of its own code.

    Both windows in one pass. A routine that leaves a parameter in the shared
    memory and then pokes the port is one exchange, and reading the two windows
    separately would report it as two halves neither of which starts the part.
    """
    here = Path(__file__).resolve().parent.parent / "snes-driver-python"
    for where in (here, here / "mos65xx-python", here / "snes-mapper-python"):
        if str(where) not in sys.path:
            sys.path.insert(0, str(where))
    from snesdriver import conversation, window_for

    reached = [window_for("st", layout) for layout in LAYOUTS]
    assert all(one is not None for one in reached), "the driver is missing a window for these parts"
    both = Anywhere([one for one in reached if one is not None])

    counted: collections.Counter[str] = collections.Counter()
    seen: set[int] = set()
    for site in conversation.sites(image, both):
        if site in seen:
            continue
        talk = conversation.at(image, site, both)
        seen.update(talk.covered)
        counted[" ".join(f"{one.what}{one.width}@{one.whole:#08x}" for one in talk.steps)] += 1
    return dict(counted)


def assemble(part: str, gathered: "Sequence[tuple[bytes, str, dict[str, int]]]") -> dict[str, Any]:
    """One recorded file from everything read for one part."""
    if not gathered:
        raise Usage(f"no cartridge carrying {part} was read")

    counted: collections.Counter[str] = collections.Counter()
    carried: collections.Counter[str] = collections.Counter()
    where = []
    for image, name, found in gathered:
        row = describe(image)
        row["name"] = name
        row["shapes"] = len(found)
        row.update(digests_of(image))
        where.append(row)
        for shape, seen in found.items():
            counted[shape] += seen
            carried[shape] += 1

    return {
        "note": (
            "The shapes real cartridges use to drive this part: which accesses each "
            "routine makes, in what order, how wide each one was and where in the "
            "shared memory it landed. No byte any cartridge carries is recorded here "
            "and none can be recovered from this. Read out of the games named below, "
            "every one of them confirmed against all four of its digests first."
        ),
        "part": part,
        "producedBy": DRIVER,
        "readFrom": sorted(where, key=lambda row: str(row["name"])),
        "shapes": [
            {"shape": shape, "seen": counted[shape], "cartridges": carried[shape]}
            for shape in sorted(counted, key=lambda one: (-counted[one], one))
        ],
    }


def _images(where: Path) -> "Iterable[tuple[bytes, str]]":
    for path in sorted(where.rglob("*")):
        if path.suffix.lower() in SUFFIXES and path.is_file():
            yield path.read_bytes(), path.name


def main(
    argv: Sequence[str],
    say: Callable[[str], object] = print,
    read: Callable[[bytes], dict[str, int]] = through_the_driver,
) -> int:
    if len(argv) < 2:
        say("usage: record.py <directory of cartridges> <output directory>")
        return 2

    source, out = Path(argv[0]), Path(argv[1])
    if not source.is_dir():
        say(f"  no such directory: {source}")
        return 2

    gathered: dict[str, list[tuple[bytes, str, dict[str, int]]]] = collections.defaultdict(list)
    for image, name in _images(source):
        try:
            describe(image)
        except NotACartridge:
            continue
        part = part_of(len(image))
        if part is None:
            continue
        gathered[part].append((image, name, read(image)))

    if not gathered:
        say(f"  no cartridge carrying either part was found under {source}")
        return 2

    quiet = 0
    for part, rows in sorted(gathered.items()):
        found = assemble(part, rows)
        if not found["shapes"]:
            say(f"  {part}: no exchange was read out of {len(rows)} cartridges")
            quiet += 1
            continue
        path = out / f"{part}shapes.json"
        path.write_text(json.dumps(found, indent=2) + "\n")
        say(
            f"  {part}: {len(found['shapes'])} shapes from {len(rows)} cartridges"
            f", written to {path}"
        )
    return 1 if quiet else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
