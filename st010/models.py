"""Which parts this package covers, and what each one is.

Seta made two coprocessors for the Super Nintendo under the ST name, and they have
nothing in common beyond the maker, the socket, and the NEC uPD96050 they are both
built on. The ST010 does navigation maths for a racing cartridge. The ST011 plays
shogi.

Only one of them could ever have been written down. What the console sends the
ST011 is a board and what it reads back is a move, so its behaviour is not a set
of commands that could be listed: its behaviour is the player masked into it, and
writing that down would mean writing a shogi engine and calling the result a model
of the part, which it would not be.

Running the program removes that distinction entirely. A part that plays shogi and
a part that computes a bearing are the same arrangement, a processor and a mask
ROM, and both are reached the same way. So both are here, and neither is described.
"""

from collections.abc import Sequence
from typing import override


class UnknownModelError(Exception):
    pass


class Model:
    """One part: what it is, and which image it runs."""

    def __init__(self, name: str, summary: str, aliases: Sequence[str] = ()) -> None:
        self.name = name
        self.summary = summary
        self.aliases = tuple(aliases)

    @property
    def image(self) -> str:
        """The name of the image this part runs, which is its own."""
        return self.name

    @override
    def __repr__(self) -> str:
        return f"<Model {self.name}, running the {self.image} image>"


_CATALOGUE = (
    Model(
        name="st010",
        summary=(
            "The Seta ST010, shipped in exactly one racing cartridge. Eight commands "
            "over four kilobytes of shared memory: a compass, a distance, a race "
            "order, two scalings, a rotation, a screen of mode seven scale, and one "
            "step of a driver steering towards its next target."
        ),
        aliases=("st-010", "seta010", "setast010"),
    ),
    Model(
        name="st011",
        summary=(
            "The Seta ST011, shipped in exactly one shogi cartridge. It plays the "
            "game rather than answering a set of commands, so what it does is the "
            "player masked into it: nothing that could be written down as a command "
            "table, and nothing that needs to be, because the program is run."
        ),
        aliases=("st-011", "seta011", "setast011"),
    ),
)

MODELS = {model.name: model for model in _CATALOGUE}

_BY_ALIAS = {}
for _model in _CATALOGUE:
    _BY_ALIAS[_model.name] = _model
    for _alias in _model.aliases:
        _BY_ALIAS[_alias] = _model


def _normalise(name: str) -> str:
    return str(name).strip().lower().replace("-", "").replace("_", "")


def describe(name: str) -> "Model":
    """The model of that name, however it happens to be written."""
    wanted = _normalise(name)
    found = _BY_ALIAS.get(wanted)
    if found is not None:
        return found
    raise UnknownModelError(
        f"{name} is not a model this package covers; it has {', '.join(sorted(MODELS))}"
    )
