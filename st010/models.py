"""Which parts this package covers, and what each one is.

Seta made two coprocessors for the Super Nintendo under the ST name and they have
nothing in common beyond the maker. The ST010 does navigation maths for a racing
cartridge. The ST011 plays shogi, and no implementation of it exists to be held
to: the one in the emulator this package is measured against answers a handful of
canned values and does not play anything.

So the ST011 is not here, and asking for it says that rather than building
something. A model with nothing behind it would make its fidelity a claim rather
than a measurement, and a claim about a chip that plays a board game would be a
particularly empty one.
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
        "the ST011 plays shogi, and the reference this package is measured against "
        "answers a handful of canned values rather than playing anything, so there "
        "is nothing to hold a model to"
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
