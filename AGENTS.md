# Working in this repository

Read [FAMILY.md](FAMILY.md) first. It is the standard every member of this
family carries, byte for byte, and it decides most questions before they are
asked. What follows is only what is true of this member. [README.md](README.md)
is the document written for a person.

## What this project is, in one paragraph

The ST010 and ST011: the two coprocessors Seta made for the Super Nintendo, one
in a racing cartridge and one in a shogi cartridge. Both are a NEC uPD96050
carrying Seta's microcode, so nothing here describes what a command computes:
the program is run rather than read, on a copy a reader supplies whose digest is
confirmed first. What this repository models is the interface Seta wrapped around
that processor, which is a four kilobyte window shared with the console, two
registers past the end of it, and the handshake that wakes the part. The
processor itself is
[nec-upd7725-96050-python](https://github.com/gufranco/nec-upd7725-96050-python),
consumed as a submodule at the repository root. Seta published nothing.

## The interface a caller drives

The part answers accesses. The cycles are spent inside the processor it composes,
and that member is the one that reports them, so none of the family's clocked
interface appears here.

`Chip(model, **options)` builds one. The model comes first, which is the argument
every member of the family takes first, and the name is the kind rather than the
chip.

| Call | What it does |
|:--|:--|
| `read(address)`, `write(address, value)` | The two accesses a cartridge makes |
| `handshake()` | What the console does at power on to wake the part |
| `step(count)` | Run the processor for a number of its own instructions |
| `reset()` | Back to a part that has not been woken, handed back for chaining |

## The authority ladder

1. **The microcode**, which is the part. The program masked into the ROM decides
   what a command answers, and it is run rather than described.
2. **What NEC printed**, reached through the sibling that read it. Every fact
   about the uPD96050 lives in that member's record, not in this one.
3. **A reference implementation**, for the interface around the ROM: where the
   shared memory sits and which addresses are registers.

A rung above beats a rung below. The rung a Seta document would occupy is empty
and the record says so.

## What is settled and what is not

**Not settled: 5 things**, each in
[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) with the measurement that would close it.
They are all the interface rather than the behaviour: the memory map, the number
of registers, timing, and what a reset does.

Settled: what every command computes, because the program is run; where each
part's program waits, because it was measured on both; and which image each part
runs, because each is pinned by digest.

## The handshake is the whole reason this exists

The model this replaced treated one write as a switch that made the part start
listening. The part has no switch. The window below the shared memory is the
processor's own data port, the microcode raises its attention bit on its first
instruction, and it waits for the console to take a word off that port before it
ever reaches the loop that watches for a command.

A part spoken to without that reads as broken. This is recorded as a closed
divergence rather than deleted, because it is the clearest evidence here that
running a program beats describing one.

## Every gate, in the order to run them

```bash
ruff format --check .
ruff check .
mypy
pnpm run format:check
python3 -m coverage erase
for file in $(find st010 conformance -name '*.test.py' | sort); do
  python3 -m coverage run -a "$file"
done
python3 -m coverage report
```

Then the throughput floor, which runs outside the coverage step because a tracer
costs about ten times what the model does:

```bash
python3 -m conformance.speed
```

And the run that reports what it could not check rather than passing quietly:

```bash
python3 snesst/doctor.py
```

Everything under `conformance/` runs as a module. Run as a script, its own
directory goes on the import path and a file there shadows any standard library
module of the same name. `doctor.py` is the exception and runs as a file on
purpose, so that it still runs when the package itself will not import, which is
the case it exists for.

## Conventions that are not negotiable

- Python only, standard library only, no dependencies.
- No comments in source. Reasoning goes in docstrings, and a step that would need
  a comment is a step that should be a named function.
- Tests sit beside the module they cover as `<module>.test.py`. Arrange, blank
  line, one act, blank line, assert, with no section labels.
- 100% statement and branch coverage, enforced. `mypy` at strict, with every
  optional error class on.
- Everything a caller can catch is defined once, in `snesst/errors.py`, and
  imported from there.
- A check nobody has seen fail is not known to work. Drive every new check
  against input that should fail it before keeping it.

## Layout

```text
snesst/
  __init__.py     the package, and the part chosen at construction
  models.py       the two parts, and the names each answers to
  chip.py         the interface Seta wrapped around the processor
  firmware.py     identifying a supplied image before it is run
  artifacts.manifest.json  what each image is, and the digest that decides
  errors.py       everything this package raises, in one place
  doctor.py       what is actually on this machine, printed for a bug report
  version.py      rewritten by the release job and by nothing else
conformance/
  family.test.py  the family standard, held to this repository
  hardware.json   what this package asserts, and where each assertion comes from
  divergences.json where sources part, and what would settle each
  speed.py        the throughput floor
nec-upd7725-96050-python/  the processor both parts are, as a submodule at the root
```

## Things that will bite you

- **The submodule is not optional.** Without it nothing here can run, and the
  refusal says so rather than falling back to a guess.
- **A part cannot be built without an image.** `Chip("st010")` raises
  `NoFirmware` on a machine that has none, which is most machines. `why_not()` is
  the sentence to print, and it is what the family's own checks read before
  skipping.
- **The processor scrambles at power on.** It does not arrive cleared, so the
  part resets it after loading the program, which is what a cartridge's reset
  line does. Without that the program starts from rubbish and the part never
  reaches its wait.
- **`.core` is the processor, `.part` is the model name.** Two attributes one
  letter apart in meaning, and reaching for the wrong one gets a string where a
  processor was expected.
- **The two parts wait in different places.** ST010 at words 3 to 5, ST011 at
  word 2. Measured on each rather than assumed to be the same.

## Before calling anything finished

Every gate above, green, with output shown. A claim without a run behind it is
not evidence. If a check was skipped because a file is not on this machine, say
which check and why rather than reporting a pass.

## What a change is expected to leave behind

A test that fails without the change and passes with it. An entry in
[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) if it turned a settled thing into an open
one, or removed one. Nothing in `firmware/` under version control, ever.
