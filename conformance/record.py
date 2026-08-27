"""Read the shapes out of the cartridges that carry these parts.

Run once, against copies you own, to produce one file per part under
`conformance/`. What it writes is the sequence of accesses each driver routine
makes, with a name, a length and four digests for every cartridge it read. No
byte any cartridge carries is recorded and none can be recovered from what is.

**Which part a cartridge carries.** The header does not say outright. The chipset
byte and the length together do, and neither alone: see `PARTS`.

**Which files it will read.** Only the ones the manifest names, matched on all
four digests. The tree these are read from also holds fan translations and
modified dumps, whose driver code is a copy of a shipped cartridge's rather than
a second witness to what the part expects.

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

PARTS = {
    (0xF6, 0x100000): "st010",
    (0xF6, 0x080000): "st011",
    (0xF5, 0x080000): "st018",
}
"""Which part a cartridge carries, by the chipset byte it declares and its length.

Neither field decides alone. The two DSP cartridges and the first shougi game all
declare `0xF6` and are told apart by length, a megabyte against half of one. The
second shougi game is the same half megabyte and declares `0xF5`, so length alone
would read it as the part it does not carry. Both fields together are exact for
every cartridge on hand, and this is a rule rather than a reading, which is why
it is written here rather than left implied.
"""

CHIPSETS = frozenset(chipset for chipset, _ in PARTS)

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


def what_it_says_about_itself(image: bytes) -> dict[str, Any]:
    """What the cartridge says about itself, or a refusal naming why not."""
    if len(image) < HEADER_AT + 32:
        raise NotACartridge("too short to hold a header where a low cartridge keeps one")
    title = image[HEADER_AT : HEADER_AT + TITLE_BYTES].decode("shift_jis", "replace")
    chipset = image[HEADER_AT + 22]
    if chipset not in CHIPSETS:
        named = ", ".join(f"{one:#04x}" for one in sorted(CHIPSETS))
        raise NotACartridge(f"declares chipset {chipset:#04x}, and a Seta part is {named}")
    return {
        "title": title.strip("\x00 "),
        "bytes": len(image),
        "layout": "lorom",
        "chipset": f"{chipset:#04x}",
    }


def part_of(chipset: int, length: int) -> str | None:
    """Which part a cartridge declaring that and running that long carries, if any."""
    return PARTS.get((chipset, length))


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


MANIFEST = (
    Path(__file__).resolve().parent.parent / "snes-driver-python" / "cartridges.manifest.json"
)
"""The published list of cartridges, which lives with the tool that reads them.

One list rather than one per member, because a cartridge is a cartridge whichever
part it carries and two lists would disagree the first time either moved.
"""


DIGESTS = ("crc32", "md5", "sha1", "sha256")


def published() -> dict[str, dict[str, Any]]:
    """Every cartridge the manifest names, by its sha256."""
    held = json.loads(MANIFEST.read_text())
    assert isinstance(held, dict), f"{MANIFEST} does not hold an object"
    return {str(row["sha256"]): row for row in held["cartridges"]}


def confirmed(image: bytes, named: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    """The manifest row this image is, or nothing if the manifest does not name it.

    All four digests, not the one the lookup used, because a manifest row that
    disagrees with itself is worth reporting rather than half-checking. And a
    manifest at all, because a directory of files is not an evidence base: the
    tree this reads from also holds fan translations and modified dumps, whose
    driver code is a copy of a shipped cartridge's. Counting one of those would
    inflate agreement with a copy of the evidence rather than a second witness.
    """
    found = digests_of(image)
    row = named.get(found["sha256"])
    if row is None:
        return None
    if any(str(row[one]) != found[one] for one in DIGESTS):
        raise Usage(f"{row['name']} is named in the manifest with digests it does not have")
    return row


def _driver() -> Any:
    here = Path(__file__).resolve().parent.parent / "snes-driver-python"
    for where in (here, here / "mos65xx-python", here / "snes-mapper-python"):
        if str(where) not in sys.path:
            sys.path.insert(0, str(where))
    import snesdriver

    return snesdriver


def windows_for(part: str) -> "Anywhere":
    """Where that part answers, asked as one question however many windows it has.

    The two DSPs answer at a port in one bank range and through shared memory in
    the next, and a routine that leaves a parameter in the second and then pokes
    the first is one exchange. Reading the windows separately would report it as
    two halves, neither of which starts the part.
    """
    driver = _driver()
    known = "st018" if part == "st018" else "st"
    named = ("lorom",) if part == "st018" else LAYOUTS
    reached = [driver.window_for(known, one) for one in named]
    assert all(one is not None for one in reached), f"the driver has no window for {part}"
    return Anywhere([one for one in reached if one is not None])


def through_the_driver(image: bytes, part: str = "st010") -> tuple[dict[str, int], bool]:
    """Every distinct exchange in one image, read out of its own code.

    How the accesses are found depends on how the part is reached. The two DSPs
    are reached with a long store, whose four bytes spell a bank and an address
    no other encoding puts there, so searching the image for those bytes is
    exact. The ST018 is reached with an ordinary absolute access, whose two bytes
    any pair of data bytes spells just as well, so that search would report
    places the console never touched. For it the driver starts at the reset
    vector and follows control flow instead.

    The second value is whether every access carried the bank it reached. A long
    one spells all three bytes; an absolute one takes its bank from a register
    nothing here tracks, and a file that did not say so would claim more than it
    knows.
    """
    driver = _driver()
    reaching = windows_for(part)
    find = driver.reached if part == "st018" else driver.conversation.sites

    counted: collections.Counter[str] = collections.Counter()
    seen: set[int] = set()
    banked = True
    for site in find(image, reaching):
        if site in seen:
            continue
        talk = driver.conversation.at(image, site, reaching)
        seen.update(talk.covered)
        banked = banked and talk.banked
        counted[" ".join(f"{one.what}{one.width}@{one.whole:#08x}" for one in talk.steps)] += 1
    return dict(counted), banked


def assemble(
    part: str, gathered: "Sequence[tuple[bytes, str, dict[str, int], bool]]"
) -> dict[str, Any]:
    """One recorded file from everything read for one part."""
    if not gathered:
        raise Usage(f"no cartridge carrying {part} was read")

    counted: collections.Counter[str] = collections.Counter()
    carried: collections.Counter[str] = collections.Counter()
    where = []
    banked = True
    for image, name, found, carried_bank in gathered:
        row = what_it_says_about_itself(image)
        row["name"] = name
        row["shapes"] = len(found)
        row.update(digests_of(image))
        where.append(row)
        banked = banked and carried_bank
        for shape, seen in found.items():
            counted[shape] += seen
            carried[shape] += 1

    return {
        "note": (
            "The shapes real cartridges use to drive this part: which accesses each "
            "routine makes, in what order, how wide each one was and where in the "
            "shared memory it landed. No byte any cartridge carries is recorded here "
            "and none can be recovered from this. Read out of the games named below, "
            "every one of them named in the manifest and confirmed against all four "
            "of its digests first."
        ),
        "part": part,
        "banked": banked,
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
    read: Callable[[bytes, str], tuple[dict[str, int], bool]] = through_the_driver,
    named: dict[str, dict[str, Any]] | None = None,
) -> int:
    if len(argv) < 2:
        say("usage: record.py <directory of cartridges> <output directory>")
        return 2

    source, out = Path(argv[0]), Path(argv[1])
    if not source.is_dir():
        say(f"  no such directory: {source}")
        return 2

    catalogue = published() if named is None else named
    gathered: dict[str, list[tuple[bytes, str, dict[str, int], bool]]] = collections.defaultdict(
        list
    )
    for image, name in _images(source):
        if confirmed(image, catalogue) is None:
            continue
        try:
            what_it_says_about_itself(image)
        except NotACartridge:
            continue
        part = part_of(image[HEADER_AT + 22], len(image))
        if part is None:
            continue
        seen, banked = read(image, part)
        gathered[part].append((image, name, seen, banked))

    if not gathered:
        say(f"  no cartridge carrying any of these parts was found under {source}")
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
