<div align="center">

<h1>Seta ST010</h1>

<strong>The navigation coprocessor one Super Nintendo racing cartridge carried, settled against its own reference.</strong>

<br>
<br>

[![CI](https://github.com/gufranco/snes-st010-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-st010-python/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-100%25%20statement%20%2B%20branch-brightgreen)](#tests)
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

</div>

<p align="center">
  <a href="#quick-start">Quick start</a> &nbsp;|&nbsp;
  <a href="#the-commands">Commands</a> &nbsp;|&nbsp;
  <a href="#how-this-is-proved">How this is proved</a> &nbsp;|&nbsp;
  <a href="#the-three-tables">The three tables</a> &nbsp;|&nbsp;
  <a href="#the-register-that-is-also-memory">The register that is also memory</a> &nbsp;|&nbsp;
  <a href="https://github.com/gufranco/snes-st010-python/issues">Issues</a>
</p>

**8** commands · **4 KB** of shared memory · **240** cases against the chip's own reference · **983,040** bytes compared, whole memories rather than answers · **151** tests · **100%** statement and branch coverage

```python
from st010 import St010

chip = St010()
chip.write(0x000000, 0x00)  # the write that makes it listen

for at, value in enumerate((0x00, 0x01, 0x00, 0x02)):
    chip.write(0x680000 + at, value)  # a point at (0x0100, 0x0200)

chip.write(0x680020, 0x01)  # which way does it lie
chip.write(0x680021, 0x80)  # go

chip.read(0x680010) | (chip.read(0x680011) << 8)
# 0x9300
```

---

## The problem

This chip has no port. It shares four kilobytes of battery-backed memory with the
console, and every command reads its arguments out of fixed addresses in that
memory and writes its answers back into other fixed addresses in the same memory.
There is no framing, no length, and no acknowledgement. A model that gets an
answer right and also disturbs a byte it should not have touched is wrong in a
way that no interface check would notice, because the interface is the memory.

It is also a chip nobody has a test suite for. It shipped in one cartridge.

## The solution

Compare whole memories.

Every case here fills the shared memory, names a command, sets the start bit, and
then compares all four thousand and ninety six bytes afterwards against what the
chip's own reference implementation left there. Nothing is spot-checked and
nothing is read from only the addresses the command is documented to write. Two
hundred and forty cases, **983,040 bytes**, every command, and zero
disagreements.

<table>
<tr>
<td width="50%" valign="top">

### Whole memories, not answers

A command that scribbles outside its own addresses fails here. Comparing only the
answer would let it through.

</td>
<td width="50%" valign="top">

### Every command, and one that is not

The rotation includes a command number the chip does not have, because clearing
its registers afterwards is behaviour too.

</td>
</tr>
<tr>
<td width="50%" valign="top">

### The steering runs for six steps

It is the only command that carries state between calls, and one step would never
show a driver arriving anywhere.

</td>
<td width="50%" valign="top">

### The tables say what they fit

Not one of the three can be restated as a formula, so each is carried as a
measurement with the function it fits and how far it strays.

</td>
</tr>
</table>

## Quick start

### Prerequisites

| Tool | Version | Install |
|:-----|:--------|:--------|
| Python | >= 3.12 | [python.org](https://www.python.org/downloads/) |

### Setup

```bash
git clone https://github.com/gufranco/snes-st010-python.git
cd snes-st010-python
```

### Verify

```bash
python3 conformance/corpus.py
#   240 cases, 983,040 bytes compared, 0 disagreed
```

## The commands

Everything happens in the shared memory. A command number goes to `$xx20`, a
start bit to `$xx21`, and the chip reads and writes the addresses below.

| Command | Byte | Reads | Writes |
|:--------|:----:|:------|:-------|
| Compass | `$01` | a point at `$00` | the folded point, its quadrant, and the angle at `$10` |
| Sort | `$02` | a count at `$24`, places from `$40`, drivers from `$80` | both lists, in order |
| Scale | `$03` | a point at `$00` and a multiplier at `$04` | two long words at `$10` |
| Distance | `$04` | a point at `$00` | one word at `$10` |
| Navigate | `$05` | a driver's whole state from `$C0` | the same state, one step on |
| Multiply | `$06` | two words at `$00` | one long word at `$10` |
| Raster | `$07` | an angle at `$00` | a screen of scale in four places, and the angle shifted |
| Rotate | `$08` | a point at `$00` and an angle at `$04` | the turned point at `$10` |

A command number the chip does not have does nothing and still clears both
registers.

## The register that is also memory

The register decode has an `else` that belongs to one branch rather than to the
pair, and the consequence is visible from outside: writing a command number also
leaves a copy of it in memory at the same address, while writing the start bit
does not.

```python
chip = St010()
chip.write(0x000000, 0x00)
chip.write(0x680020, 0x04)

chip.read(0x680020)  # 0x04, the register
chip.memory[0x20]  # 0x04, a copy nobody asked for

chip.write(0x680021, 0x01)
chip.memory[0x21]  # 0x00, because that branch was taken
```

The other thing worth knowing is that the chip is not listening when it arrives.
Until a write lands below the shared window, neither register can be set at all
and every write goes to memory instead. That write does nothing else.

## How this is proved

| Part | Oracle | Strength |
|:-----|:-------|:---------|
| All eight commands | 240 whole-memory comparisons against snes9x's own `seta010.cpp` | Differential, and over the whole memory rather than the answer |
| The steering | Six consecutive steps per case, so its state carries | Differential across a sequence |
| The unrecognised command | In the rotation with the rest | Differential |
| The compass folding | Every quadrant, the origin, and a point on each axis | Behavioural |
| The sort | Ordered, reversed, and a field of none | Behavioural |
| The three tables | Each against the function it fits | Measured, with the deviation stated |

The reference is fetched rather than carried, pinned by commit, and only the
driver in [`conformance/ref/`](conformance/ref/) belongs to this repository:

```bash
python3 conformance/build.py
#   built conformance/ref/driver against 2971061cf07f
python3 conformance/corpus.py --record
#   recorded 240 cases
```

## The three tables

Three tables are masked into this chip. Unlike the DSP family it sits beside, not
one of them can be restated as the formula that made it: each agrees with a
function of school mathematics to within a unit or two and none agrees exactly,
which is what a table computed by an iterative routine on the machine that
carries it looks like rather than one rounded from an ideal.

| Table | Entries | Fits | Strays by at most |
|:------|--------:|:-----|------------------:|
| Sine | 256 | a word times the sine of the angle | 1.5 |
| Arctangent | 32 x 32 | the angle of a point, from the vertical | 2.1 |
| Raster scale | 176 | falls away like one over a distance | not any particular one |

So they are carried as measurements, and each is stated with the function it fits
and how far it strays. That is the honest description: these are the values of a
known function, taken from the part, and nothing about their shape is a choice
anyone made.

## The distance is not a distance

The chip does not take a square root. It takes the longer side at a bit over nine
tenths and the shorter at a bit under a fifth, which is the standard cheap
approximation:

```python
from st010 import maths

maths.distance(0x400, 0)  # 0x3D8, four percent under the true 0x400
maths.distance(0x400, 0x400)  # 0x56F, four percent under the true 0x5A8
```

Nothing here calls that a length, and a model that used a real square root would
disagree with the chip on every diagonal.

## Models

Seta made two coprocessors for this console under the ST name and they have
nothing in common beyond the maker.

| Model | State | Shared memory | Notes |
|:------|:------|:-------------:|:------|
| `st010` | modelled | 4 KB | Eight commands. Aliases: `st-010`, `seta010`, `setast010` |
| `st011` | elsewhere | n/a | Plays shogi. Reached by running its own firmware on the processor underneath |

Asking for the second says where it went rather than building something:

```python
from st010 import Seta

Seta(model="st011")
# UnknownModelError: st011 is not modelled here: the ST011 plays shogi, so its
# behaviour is the player masked into it rather than a set of commands that
# could be written down; it is reached instead by running its own firmware on
# the processor underneath, which lives in nec-upd7725-python
```

The line between the two is worth stating, because both parts sit in the same
socket and answer through the same shared memory. The ST010's eight commands are
each a function of their arguments, so they can be written down and held to a
corpus. The ST011's one job is to choose a move, and no list of commands produces
that; the program masked into it does. A model of it written here would be a shogi
engine written here, which is a different thing wearing the same name.

## Project structure

```
st010/
  __init__.py     the package, and the model chosen at construction
  chip.py         the two registers and the memory the answers land in
  maths.py        the eight things it computes, as functions of their input
  tables.py       the three tables, each with the function it fits
  models.py       what each part is, and which one is not here
  version.py      rewritten by the release job and by nothing else
conformance/
  build.py        fetches the pinned reference and builds the driver
  corpus.py       replays 240 whole-memory cases
  ref/            the driver around the reference, which is all this side compiles
```

Each module has its tests beside it as `<module>.test.py`, so a module and the cases that pin its behaviour are read together.

## Tests

```bash
for f in st010/*.test.py conformance/*.test.py; do python3 "$f"; done
```

| Suite | File | Covers |
|:------|:-----|:-------|
| Arithmetic | [`st010/maths.test.py`](st010/maths.test.py) | The compass folding, the scalings, the rotation, the distance fit, the sort, the raster, the steering |
| Registers | [`st010/chip.test.py`](st010/chip.test.py) | The enable write, the decode, the copy in memory, every command's addresses |
| Models | [`st010/models.test.py`](st010/models.test.py) | The catalogue, alias matching, the part that is not here |
| Corpus harness | [`conformance/corpus.test.py`](conformance/corpus.test.py) | Case generation, the script the driver reads, replay against 240 recorded memories |
| Build harness | [`conformance/build.test.py`](conformance/build.test.py) | The pin, the fetch, the extraction, the compile |

Coverage is enforced at 100% of statements and branches by [`pyproject.toml`](pyproject.toml), so a new branch without a test fails the build rather than quietly lowering the number.

## Development

| Command | Description |
|:--------|:------------|
| `ruff format .` | Format |
| `ruff check .` | Lint |
| `python3 -m coverage run -a <file>` | Run one test file under coverage |
| `python3 -m coverage report` | Coverage, which fails below 100% |
| `python3 conformance/build.py` | Fetch the pinned reference and build the driver |
| `python3 conformance/corpus.py` | Replay the 240 recorded cases |
| `pnpm run format` | Format every JSON file |

## Project conventions

| Convention | Source |
|:-----------|:-------|
| Commit format | [Conventional Commits](https://www.conventionalcommits.org/) |
| Releases | [semantic-release](https://semantic-release.gitbook.io/), driven by [`.releaserc.json`](.releaserc.json) |
| Lint and format | [Ruff](https://docs.astral.sh/ruff/), configured in [`pyproject.toml`](pyproject.toml) |
| JSON formatting | [Prettier](https://prettier.io/), configured in [`.prettierrc.json`](.prettierrc.json) |
| Test layout | `<module>.test.py` beside the module it covers |

## Versioning

This project follows [Semantic Versioning](https://semver.org/), and every release is tagged from `main` by semantic-release. See [releases](https://github.com/gufranco/snes-st010-python/releases).

## FAQ

<details>
<summary><strong>Why compare whole memories instead of the answers?</strong></summary>
<br>

Because the interface is the memory. A command that writes the right answer and
also disturbs a byte belonging to something else would pass a check that looked
only at the answer, and would then corrupt whatever the console had left there.
The whole-memory comparison is not thoroughness for its own sake; it is the only
comparison that matches how the chip is actually used.

</details>

<details>
<summary><strong>Why are the tables carried as data when the DSP family's are formulas?</strong></summary>
<br>

Because these ones are not formulas. Every table the DSP-1 reads turned out to be
exactly reproducible from an expression, so that package ships the expressions.
These three agree with a sine, an arctangent and a falling curve to within a unit
or two and disagree with every rounding rule tried against them, which is what a
table computed on the machine that carries it looks like. Carrying them as
measurements and saying what they fit is the honest description.

</details>

<details>
<summary><strong>Why is the ST011 not here?</strong></summary>
<br>

Because it is a different kind of part wearing the same package. Every command here
is a function of its arguments, which is why each one can be written down and held
to a corpus. The ST011 chooses a shogi move, and that is not a function anyone can
write down; it is a program, masked into the part. Reproducing it means running that
program, which means the processor underneath and a firmware image its owner
supplies. That work lives in `nec-upd7725-python`, where it belongs, rather than
here where it would have to be invented.

</details>

## License

[MIT](LICENSE)
