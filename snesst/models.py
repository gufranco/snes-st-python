from collections.abc import Sequence
from typing import override

from snesst.errors import UnknownModelError


class Model:
    __slots__ = ("aliases", "name", "summary")

    def __init__(self, name: str, summary: str, aliases: Sequence[str] = ()) -> None:
        self.name = name
        self.summary = summary
        self.aliases = tuple(aliases)

    @property
    def image(self) -> str:
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
    Model(
        name="st018",
        summary=(
            "The Seta ST018, shipped in exactly one shogi cartridge and sharing no "
            "silicon with the two above it: a 32 bit ARM on the cartridge's own "
            "crystal rather than a digital signal processor. It answers a table of "
            "twenty-eight commands over a one byte mailbox, and what it does with "
            "them is the same thing the ST011 does, which is play the game."
        ),
        aliases=("st-018", "seta018", "setast018"),
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


def lookup(name: str | None) -> Model:
    if name is None:
        raise UnknownModelError(
            "no model was named, and this package will not choose one for you."
            f" Name one of: {', '.join(sorted(MODELS))}"
        )
    wanted = _normalise(name)
    found = _BY_ALIAS.get(wanted)
    if found is not None:
        return found
    raise UnknownModelError(
        f"{name} is not a model this package covers; it has {', '.join(sorted(MODELS))}"
    )
