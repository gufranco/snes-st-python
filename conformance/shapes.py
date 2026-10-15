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


class Malformed(Exception): ...


@runtime_checkable
class Addressed(Protocol):
    def write(self, address: int, value: int) -> None: ...

    def read(self, address: int) -> int: ...


class Step:
    __slots__ = ("address", "what", "width")

    def __init__(self, what: str, width: int, address: int) -> None:
        self.what = what
        self.width = width
        self.address = address

    @property
    def moves(self) -> bool:
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
    return " ".join(repr(step) for step in steps)


def parse(shape: str) -> "tuple[Step, ...]":
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
    path = Path(where) if where is not None else ROOT / f"{part}shapes.json"
    if not path.is_file():
        return ()
    found = json.loads(path.read_text())
    rows = [(parse(one["shape"]), int(one["seen"])) for one in found["shapes"]]
    return tuple(sorted(rows, key=lambda row: (-len(row[0]), -row[1])))


def interesting(shapes: "Shapes") -> "Shapes":
    return tuple(row for row in shapes if any(step.moves for step in row[0]))


def payload_for(steps: "Iterable[Step]", chance: random.Random) -> list[list[int]]:
    return [
        [chance.randrange(0x100) for _ in range(step.width)] for step in steps if step.what == WRITE
    ]


def drive(
    part: "Addressed", steps: "Iterable[Step]", payload: Iterable[Sequence[int]]
) -> list[list[int]]:
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
    return random.Random(seed)
