"""Drive a part through the exchanges a real cartridge has with it.

Running a part's microcode is only half of getting it right. The other half is
sending it what a console sends: these parts have no framing, so a byte means
whatever the state left by the bytes before it decides, and a sequence no game
ever sent asks a question nobody has an answer for.

What a game sends is not something to derive. It is written down in the game, as
ordinary 65816 code, and `snes-driver-python` reads it out by disassembling the
routine rather than running it. What comes back is a shape: the accesses a
routine makes, in order, with the width of each, where in the shared memory each
one landed, and no payload attached. Those shapes are recorded beside this, with
the digests of the cartridges they came from and none of their bytes.

This plays them at the part and prints what it said. It is not a comparison
against anything written down, because there is nothing left to compare against:
neither part has a datasheet and the part is the authority. What it catches is
the part not answering at all, which is what a broken decode, a wrong image or a
command started at the wrong moment look like.

**One part for the whole run.** A console does not reset a coprocessor between
routines, and these two answer through memory: a routine that reads an address
is reading what an earlier routine left there. Building a fresh part per shape
would ask every read a question with nothing behind it.

**Most shapes say nothing, and that is not a fault.** The bytes filling a shape
are generated, so a parameter is rarely one that makes the part write where the
game later reads. What a run establishes is that the part answers at all under
exchanges a real cartridge makes, which is exactly what a wrong image or a broken
decode takes away. A count of how many answered is printed rather than asserted,
because nothing here can say what the count should be.

**No command byte is swept, unlike the DSP's run.** There the first byte a shape
writes is the command, so trying each of the 256 in turn asks the part every
question it has. Here the first byte a shape writes is a parameter: across both
cartridges no recorded shape writes the register that starts a command, and the
one beside it is only ever polled. Sweeping would put a command byte where a
number belongs and report the result as though a question had been asked. Why the
starting write is absent from the record is written down in the open questions,
and it is a limit of what a walk can see rather than something the games do not
do.

Needs an image, so on a machine without one it says so and stops rather than
reporting a pass.

Usage:
    python3 conformance/against_cartridges.py [part]
"""

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


class Usage(Exception):
    """The run was asked for a part nothing is recorded for."""


class Played:
    """One shape, and everything the part said while it was played.

    Named for the run rather than for the part: this holds what came back, and
    the thing that came back is not something anybody can drive.
    """

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
        """Whether this shape reads at all.

        A routine that only leaves parameters behind is a real exchange and it
        has no answer to give. Counting one as silence would report a working
        part as a dead one, and the two ST010 cartridges carry eleven of them.
        """
        return shapes.READ in self.kinds_in_order

    @property
    def answered(self) -> bool:
        """Whether anything came back from the shared memory that was not a zero.

        Reads only. A part that is doing nothing still has a control pair, and a
        pair that reads as ready is not an answer: counting it would let a part
        that computes nothing look like one that does.

        A part answering nothing but zeroes to every exchange a real game makes
        is not answering. It is the shape a wrong image, an unbooted part and a
        command started at the wrong moment all take.
        """
        return any(
            byte
            for kind, run in zip(self.kinds, self.said, strict=False)
            if kind == shapes.READ
            for byte in run
        )

    @override
    def __repr__(self) -> str:
        return f"<Played {self.shape}, {len(self.said)} answers>"


def _silicon(part: str) -> "shapes.Addressed":  # pragma: no cover
    return snesst.Chip(part)


def driven(
    part: str = DEFAULT_PART,
    build: Build = _silicon,
    seed: int | None = None,
    where: Path | str | None = None,
) -> "list[Played]":
    """Every recorded shape for that part, played in order at one part."""
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
    """The lines a person reads, one exchange at a time."""
    said = []
    for one in found[:SHOWN]:
        said.append(f"    {one.shape}: {[[hex(byte) for byte in run] for run in one.said]}")
    return said


def silent(found: "Iterable[Played]") -> "list[Played]":
    """Every exchange the part answered nothing to, having been asked in order."""
    return [one for one in found if one.asks and not one.answered]


def spoken(found: "Iterable[Played]") -> "list[Played]":
    """Every exchange that got something other than a zero back."""
    return [one for one in found if one.answered]


def wordless(found: "Iterable[Played]") -> "list[Played]":
    """Every exchange that never reads, so the part was never asked anything."""
    return [one for one in found if not one.asks]


def lines_for(found: "Sequence[Played]", part: str) -> list[str]:
    """What the run says about one part."""
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
