"""The ST010 and ST011, run rather than described.

    from st010 import St010

    chip = St010()
    chip.write(0x000000, 0x00)
    for at, value in enumerate((0x00, 0x01, 0x00, 0x02)):
        chip.write(0x680000 + at, value)
    chip.write(0x680020, 0x01)
    chip.write(0x680021, 0x80)
    chip.read(0x680010) | (chip.read(0x680011) << 8)
    # 0x9300

Both are a NEC uPD96050 with microcode masked into it, so what a command computes
is the program the part carries. This runs that program. There is nothing here
that works out what the answers are, because the part already knows.

That is a deliberate narrowing. The tables this chip works from cannot be
restated as the formulas that made them: each agrees with school mathematics to
within a unit or two and none agrees exactly, which is what a table computed by
an iterative routine on the machine that would use it looks like. Carrying them
means carrying the chip's content, and deriving them means being slightly wrong
everywhere. Running the program is neither.

What it costs is the microcode, which belongs to whoever made the part and is
never carried here. A copy you already own goes in the firmware directory of this
project, or of the project this one sits inside, or in any directory named by
`UPD7725_FIRMWARE_DIR`. Without one this refuses and says so.

Four kilobytes of memory shared with the console, and two registers just past the
end of it. The console writes the arguments in, names a command, sets a bit, and
reads the answers out of the same memory. Eight commands: which way a point lies,
how far away it is, the race order, two kinds of scaling, a rotation, a screen of
mode seven scale, and one step of a driver steering towards its next target.

The part is not listening when it arrives. A write below the shared window is
what starts it listening, and until that arrives its two registers cannot be set
at all. On the part that write is not a switch: the window below the shared
memory is the processor's own data port, and the microcode is waiting for the
console to speak to it.
"""

from typing import Any

from .models import MODELS, UnknownModelError, describe
from .silicon import NeverFinished, NoFirmware, Silicon, available, why_not
from .version import VERSION

__version__ = VERSION

DEFAULT_MODEL = "st010"


def St010(model: str = DEFAULT_MODEL, **options: Any) -> Any:  # noqa: N802
    """One part of that name, running its own microcode.

    Refuses when there is no image for it rather than answering from somewhere
    else, because an answer that did not come from the part is worse than none.
    """
    return Silicon(describe(model).name, **options)


Seta = St010
"""The family name, for a caller who prefers to say which family they mean."""


__all__ = [
    "MODELS",
    "NeverFinished",
    "NoFirmware",
    "Seta",
    "Silicon",
    "St010",
    "UnknownModelError",
    "__version__",
    "available",
    "describe",
    "why_not",
]
