"""Drive a part the way a cartridge drives it, rather than the way a table says.

These two parts have no datasheet. What a console says to them is written down in
exactly one place, which is the routine the cartridge runs, and that is ordinary
65816 code that `snes-driver-python` reads without executing anything. What it
reads back is a shape: the accesses a routine makes, in order, with the width of
each and no payload attached.

**Why a shape here carries an address and the DSP's does not.** A DSP has two
registers, so knowing that an access was a write says where it went. These parts
answer through two windows: a two byte port, and four kilobytes both sides share
where the console leaves parameters, takes the answer back out, and finds the
pair that starts a command. An access with the address removed says nothing at
all, because a write to the second of those two bytes is what makes the part run,
a write four bytes lower is a number it will read later, and a write to the port
is neither.

The address recorded is the one the cartridge's own instruction carried, so the
bit that tells the two windows apart is still in it and nothing replaying a shape
has to know which window a step meant.

The bytes filling a shape are generated from a seed here, so a run needs nothing
belonging to a cartridge and stores nothing belonging to one. The shapes sit in a
JSON file beside this one with the digests of the cartridges they came from, so
anybody holding the same cartridge can confirm they are looking at the same
thing.
"""

import json
import random
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Protocol, override, runtime_checkable

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent

WRITE = "write"

READ = "read"

POLL = "poll"

STEPS = (WRITE, READ, POLL)

DEFAULT_SEED = 0x51A7C0

Shapes = tuple[tuple["tuple[Step, ...]", int], ...]
"""Recorded shapes and how many sites used each, longest first."""


class Malformed(Exception):
    """A shape that does not spell an access this file knows how to replay."""


@runtime_checkable
class Addressed(Protocol):
    """What a run needs a part to be, which is less than a part is.

    A byte in at an address and a byte out at an address. The real part also
    exposes its core, its clock and its ports, and a run that reached for any of
    those would be checking the model's insides rather than what a console can
    observe.
    """

    def write(self, address: int, value: int) -> None:
        """Give it one byte, at one address."""
        ...

    def read(self, address: int) -> int:
        """Take one byte, from one address."""
        ...


class Step:
    """One access in a shape: what kind, how wide, and where it landed."""

    __slots__ = ("address", "what", "width")

    def __init__(self, what: str, width: int, address: int) -> None:
        self.what = what
        self.width = width
        self.address = address

    @property
    def moves(self) -> bool:
        """Whether this access carries a payload rather than watching a register."""
        return self.what in (WRITE, READ)

    @override
    def __repr__(self) -> str:
        return f"{self.what}{self.width}@{self.address:#08x}"

    @override
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Step):
            return NotImplemented
        return (self.what, self.width, self.address) == (other.what, other.width, other.address)

    @override
    def __hash__(self) -> int:
        return hash((self.what, self.width, self.address))


def spell(steps: "Iterable[Step]") -> str:
    """One shape as the string the recorded file carries."""
    return " ".join(repr(step) for step in steps)


def parse(shape: str) -> "tuple[Step, ...]":
    """A recorded shape back into the accesses it names."""
    found = []
    for word in shape.split():
        kind, _, rest = word.partition("@")
        if not rest:
            raise Malformed(f"{word} names no address; a shape here is kind, width, then @address")
        known = next((one for one in STEPS if kind.startswith(one)), None)
        if known is None:
            raise Malformed(f"{kind} is not one of {', '.join(STEPS)}")
        width = kind[len(known) :]
        if not width.isdigit():
            raise Malformed(f"{word} does not say how wide it is")
        try:
            address = int(rest, 16)
        except ValueError as reason:
            raise Malformed(f"{rest} is not an address") from reason
        found.append(Step(known, int(width), address))
    if not found:
        raise Malformed("a shape with no accesses in it drives nothing")
    return tuple(found)


def recorded(part: str, where: Path | str | None = None) -> "Shapes":
    """Every shape read out of the cartridges that carry that part."""
    path = Path(where) if where is not None else ROOT / f"{part}shapes.json"
    if not path.is_file():
        return ()
    found = json.loads(path.read_text())
    rows = [(parse(one["shape"]), int(one["seen"])) for one in found["shapes"]]
    return tuple(sorted(rows, key=lambda row: (-len(row[0]), -row[1])))


def interesting(shapes: "Shapes") -> "Shapes":
    """The shapes worth playing, which is the ones that move a payload.

    A routine that only watches the control pair and never writes a parameter or
    reads an answer is a wait loop. Playing one asks the part nothing.
    """
    return tuple(row for row in shapes if any(step.moves for step in row[0]))


def payload_for(steps: "Iterable[Step]", chance: random.Random) -> list[list[int]]:
    """Bytes to fill one shape's writes, generated rather than taken from anywhere."""
    return [
        [chance.randrange(0x100) for _ in range(step.width)] for step in steps if step.what == WRITE
    ]


def drive(
    part: "Addressed", steps: "Iterable[Step]", payload: Iterable[Sequence[int]]
) -> list[list[int]]:
    """One shape through one part, returning everything it said back.

    Two calls, which is everything a console can do to one of these: put a byte
    at an address and take a byte from one. A poll is a read of the control pair
    and goes through the same call, because on the part it is the same access.

    The address a step carries is the one the cartridge's own instruction carried,
    so a step reaching the port and a step reaching the shared memory are told
    apart by the same bit the part tells them apart by. Nothing here has to know
    which is which.
    """
    giving = iter(payload)
    said: list[list[int]] = []
    for step in steps:
        if step.what == WRITE:
            for at, byte in enumerate(next(giving)):
                part.write(step.address + at, byte)
        else:
            said.append([part.read(step.address + at) for at in range(step.width)])
    return said


def rolls(seed: int = DEFAULT_SEED) -> random.Random:
    """The generator the payloads come from, seeded so a run repeats."""
    return random.Random(seed)
