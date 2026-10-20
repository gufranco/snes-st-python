import json
import random
import sys
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import Protocol, override, runtime_checkable

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent

WRITE = "write"

READ = "read"

POLL = "poll"

STEPS = (WRITE, READ, POLL)

KNOWN = ""

RAN = "*"

TRACED = "~"

ASSUMED = "?"

MARKS = (RAN, TRACED)

ASSUMED_WIDTH = 1

DEFAULT_SEED = 0x51A7C0

Shapes = tuple[tuple["tuple[Step, ...]", int], ...]

Pace = Callable[["Step", "Step | None"], None]


class Malformed(Exception): ...


@runtime_checkable
class Addressed(Protocol):
    def write(self, address: int, value: int) -> None: ...

    def read(self, address: int) -> int: ...


@runtime_checkable
class Clocked(Addressed, Protocol):
    def step(self, steps: int = 1) -> object: ...


class Step:
    __slots__ = ("address", "label", "what", "width")

    def __init__(self, what: str, width: int, address: int, label: str = KNOWN) -> None:
        self.what = what
        self.width = width
        self.address = address
        self.label = label

    @property
    def moves(self) -> bool:
        return self.what in (WRITE, READ)

    @property
    def assumed(self) -> bool:
        return self.label == ASSUMED

    @property
    def spelled_width(self) -> str:
        return ASSUMED if self.assumed else f"{self.width}{self.label}"

    @override
    def __repr__(self) -> str:
        return f"{self.what}{self.spelled_width}@{self.address:#08x}"

    def _key(self) -> tuple[str, int, int, str]:
        return (self.what, self.width, self.address, self.label)

    @override
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Step):
            return NotImplemented
        return self._key() == other._key()

    @override
    def __hash__(self) -> int:
        return hash(self._key())


def spell(steps: "Iterable[Step]") -> str:
    return " ".join(repr(step) for step in steps)


def assumptions(steps: "Iterable[Step]") -> int:
    return sum(1 for step in steps if step.assumed)


def width_of(word: str, spelled: str) -> tuple[int, str]:
    if spelled == ASSUMED:
        return ASSUMED_WIDTH, ASSUMED
    label = spelled[-1] if spelled[-1:] in MARKS else KNOWN
    digits = spelled[: len(spelled) - len(label)]
    if not digits.isdigit():
        raise Malformed(f"{word} does not say how wide it is")
    return int(digits), label


def parse(shape: str) -> "tuple[Step, ...]":
    found = []
    for word in shape.split():
        kind, _, rest = word.partition("@")
        if not rest:
            raise Malformed(f"{word} names no address; a shape here is kind, width, then @address")
        known = next((one for one in STEPS if kind.startswith(one)), None)
        if known is None:
            raise Malformed(f"{kind} is not one of {', '.join(STEPS)}")
        width, label = width_of(word, kind[len(known) :])
        try:
            address = int(rest, 16)
        except ValueError as reason:
            raise Malformed(f"{rest} is not an address") from reason
        found.append(Step(known, width, address, label))
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
    part: "Addressed",
    steps: "Iterable[Step]",
    payload: Iterable[Sequence[int]],
    pace: "Pace | None" = None,
) -> list[list[int]]:
    giving = iter(payload)
    said: list[list[int]] = []
    ordered = tuple(steps)
    for step, following in zip(ordered, (*ordered[1:], None), strict=True):
        if pace is not None:
            pace(step, following)
        if step.what == WRITE:
            for at, byte in enumerate(next(giving)):
                part.write(step.address + at, byte)
        else:
            said.append([part.read(step.address + at) for at in range(step.width)])
    return said


def rolls(seed: int = DEFAULT_SEED) -> random.Random:
    return random.Random(seed)
