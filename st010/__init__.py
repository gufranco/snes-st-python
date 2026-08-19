"""The ST010, the navigation coprocessor one Super Nintendo racing cartridge carried.

    from st010 import St010

    chip = St010()
    chip.write(0x000000, 0x00)
    chip.write(0x680000, 0x00)
    chip.write(0x680001, 0x01)
    chip.write(0x680002, 0x00)
    chip.write(0x680003, 0x02)
    chip.write(0x680020, 0x01)
    chip.write(0x680021, 0x80)
    chip.read(0x680010)

Four kilobytes of memory shared with the console, and two registers just past the
end of it. The console writes the arguments in, names a command, sets a bit, and
reads the answers out of the same memory. Eight commands: which way a point lies,
how far away it is, the race order, two kinds of scaling, a rotation, a screen of
mode seven scale, and one step of a driver steering towards its next target.

The chip is not listening when it arrives. A write below the shared window is what
starts it listening, and until that arrives its two registers cannot be set at
all.
"""

from . import chip, maths, tables
from .chip import St010
from .models import MODELS, UnknownModelError, describe
from .version import VERSION

__version__ = VERSION

DEFAULT_MODEL = "st010"


def Seta(model=DEFAULT_MODEL, **options):  # noqa: N802
    """A chip of the named model, however the name happens to be written."""
    return describe(model).build(**options)


__all__ = [
    "MODELS",
    "Seta",
    "St010",
    "UnknownModelError",
    "__version__",
    "chip",
    "describe",
    "maths",
    "tables",
]
