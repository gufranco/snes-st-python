from typing import Any

from . import chip as chip
from . import firmware as firmware
from . import models as models
from . import st018 as st018
from .chip import available, why_not
from .errors import (
    Corrupt,
    NeverFinished,
    NoFirmware,
    UnknownModelError,
    UnknownPort,
    Unrecognised,
    WrongShape,
)
from .models import MODELS, Model
from .st018 import ST018
from .version import VERSION

__version__ = VERSION


def Chip(model: str | None = None, **options: Any) -> "chip.Chip | st018.ST018":  # noqa: N802
    name = models.lookup(model).name
    if name == st018.PART:
        return st018.ST018(**options)
    return chip.Chip(name, **options)


__all__ = [
    "MODELS",
    "ST018",
    "Chip",
    "Corrupt",
    "Model",
    "NeverFinished",
    "NoFirmware",
    "UnknownModelError",
    "UnknownPort",
    "Unrecognised",
    "WrongShape",
    "__version__",
    "available",
    "why_not",
]
