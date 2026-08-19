"""Which parts this package covers, and what each one is.

Seta made two coprocessors for the Super Nintendo under the ST name and they have
nothing in common beyond the maker and the socket. The ST010 does navigation maths
for a racing cartridge: eight commands, each one a function of its arguments, which
is why it can be written down. The ST011 plays shogi.

That difference is why only one of them is here, and it is a difference in kind
rather than in effort. What the console sends the ST011 is a board and what it
reads back is a move, so its behaviour is not a set of commands that could be
listed; its behaviour is the player masked into it. Writing that down would mean
writing a shogi engine and calling the result a model of that part, which it would
not be.

The honest way to reach it is the processor underneath running the part's own
firmware, and that is a different package: `nec-upd7725-python` carries the NEC
uPD96050 this part is built on, and runs a firmware image its owner supplies. This
package stays what it is, eight commands written down as functions of their
arguments, because that is what the ST010 actually is.
"""


class UnknownModelError(Exception):
    pass


class Model:
    """One part: what it is, what it holds, and how to build it."""

    def __init__(self, name, summary, memory_bytes, core, aliases=()):
        self.name = name
        self.summary = summary
        self.memory_bytes = memory_bytes
        self.core = core
        self.aliases = tuple(aliases)

    def build(self, **options):
        return self.core(self, **options)

    def __repr__(self):
        return f"<Model {self.name}, {self.memory_bytes} bytes of shared memory>"


def _build_st010(model, **options):
    from .chip import St010

    chip = St010(**options)
    chip.model = model.name
    return chip


_CATALOGUE = (
    Model(
        name="st010",
        summary=(
            "The Seta ST010, shipped in exactly one racing cartridge. Eight commands "
            "over four kilobytes of shared memory: a compass, a distance, a race "
            "order, two scalings, a rotation, a screen of mode seven scale, and one "
            "step of a driver steering towards its next target."
        ),
        memory_bytes=0x1000,
        core=_build_st010,
        aliases=("st-010", "seta010", "setast010"),
    ),
)

MODELS = {model.name: model for model in _CATALOGUE}

NOT_MODELLED = {
    "st011": (
        "the ST011 plays shogi, so its behaviour is the player masked into it rather "
        "than a set of commands that could be written down; it is reached instead by "
        "running its own firmware on the processor underneath, which lives in "
        "nec-upd7725-python"
    ),
}
"""Parts of the same family that are named here so that asking about one explains itself."""

_BY_ALIAS = {}
for _model in _CATALOGUE:
    _BY_ALIAS[_model.name] = _model
    for _alias in _model.aliases:
        _BY_ALIAS[_alias] = _model


def _normalise(name):
    return str(name).strip().lower().replace("-", "").replace("_", "")


def describe(name):
    """The model of that name, however it happens to be written."""
    wanted = _normalise(name)
    found = _BY_ALIAS.get(wanted)
    if found is not None:
        return found
    if wanted in NOT_MODELLED:
        raise UnknownModelError(f"{name} is not modelled here: {NOT_MODELLED[wanted]}")
    raise UnknownModelError(
        f"{name} is not a model this package covers; it has {', '.join(sorted(MODELS))}"
    )
