import sys
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import override

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import snesst
from conformance import shapes
from snesst import chip

DEFAULT_PART = "st010"

SHOWN = 8


Build = Callable[[str], "shapes.Addressed"]


class Usage(Exception): ...


class Played:
    def __init__(
        self,
        shape: str,
        said: Sequence[Sequence[int]],
        kinds: Iterable[str] = (),
    ) -> None:
        self.shape = shape
        self.said = said
        self.kinds = tuple(kinds)
        self.kinds_in_order = tuple(one.what for one in shapes.parse(shape))

    @property
    def asks(self) -> bool:
        return shapes.READ in self.kinds_in_order

    @property
    def answered(self) -> bool:
        return any(
            byte
            for kind, run in zip(self.kinds, self.said, strict=False)
            if kind == shapes.READ
            for byte in run
        )

    @override
    def __repr__(self) -> str:
        return f"<Played {self.shape}, {len(self.said)} answers>"


def surface(part: str, where: Path | str | None = None) -> tuple[tuple[int, str], ...]:
    found = {
        (step.address, shapes.READ if step.what == shapes.POLL else step.what)
        for steps, _ in shapes.recorded(part, where)
        for step in steps
    }
    return tuple(sorted(found))


def _silicon(part: str) -> "shapes.Addressed":  # pragma: no cover
    return snesst.Chip(part)


def driven(
    part: str = DEFAULT_PART,
    build: Build = _silicon,
    seed: int | None = None,
    where: Path | str | None = None,
) -> "list[Played]":
    held = shapes.interesting(shapes.recorded(part, where))
    if not held:
        raise Usage(f"no cartridge exchanges are recorded for {part}")
    chance = shapes.rolls() if seed is None else shapes.rolls(seed)
    piece = build(part)
    found: list[Played] = []
    for steps, _seen in held:
        payload = shapes.payload_for(steps, chance)
        said = shapes.drive(piece, steps, payload)
        taken = [one.what for one in steps if one.what in (shapes.READ, shapes.POLL)]
        named = shapes.spell(steps)
        found.append(Played(named, said, taken))
    return found


def report(found: "Sequence[Played]") -> list[str]:
    said = []
    for one in found[:SHOWN]:
        said.append(f"    {one.shape}: {[[hex(byte) for byte in run] for run in one.said]}")
    return said


def silent(found: "Iterable[Played]") -> "list[Played]":
    return [one for one in found if one.asks and not one.answered]


def spoken(found: "Iterable[Played]") -> "list[Played]":
    return [one for one in found if one.answered]


def wordless(found: "Iterable[Played]") -> "list[Played]":
    return [one for one in found if not one.asks]


def lines_for(found: "Sequence[Played]", part: str) -> list[str]:
    quiet = silent(found)
    lines = [f"  {part}: {len(found)} exchanges a real cartridge makes, played at the part"]
    lines.extend(report(found))
    lines.append(f"  {len(spoken(found))} of them got something back, {len(quiet)} of them nothing")

    mute = wordless(found)
    if mute:
        lines.append(
            f"  {len(mute)} of them never read, so the part was not asked anything."
            " Not counted either way:"
        )
        lines.extend(f"    {one.shape}" for one in mute[:SHOWN])
    return lines


def main(
    argv: Sequence[str],
    why_not: Callable[[], str | None] = chip.why_not,
    build: Build = _silicon,
    say: Callable[[str], object] = print,
) -> int:
    reason = why_not()
    if reason:
        say(f"  nothing was driven: {reason}")
        return 2

    part = argv[0] if argv else DEFAULT_PART
    found = driven(part, build)
    for line in lines_for(found, part):
        say(line)
    return 0 if spoken(found) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
