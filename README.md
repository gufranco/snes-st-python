# Seta ST010 and ST011

The two coprocessors Seta made for the Super Nintendo, running the microcode you supply rather than a description of it.

[![CI](https://github.com/gufranco/snes-st-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-st-python/actions/workflows/ci.yml)

**2** parts, **1** processor underneath both, **4 KB** of memory shared with the console, **0** commands described by hand, both waits measured on the shipped microcode, **0** disagreements, **494** tests, **100%** statement and branch coverage, every image confirmed by **SHA-256** before a byte of it runs, no dependencies

```python
from snesst import Chip

chip = Chip()

chip.write(0x000000, 0x00)
for at, value in enumerate((0x00, 0x01, 0x00, 0x02)):
    chip.write(0x680000 + at, value)
chip.write(0x680020, 0x01)
chip.write(0x680021, 0x80)

chip.read(0x680010) | (chip.read(0x680011) << 8)

# 0x9300
```

The first write wakes the part. The four after it are a point at `(0x0100,
0x0200)` in the shared memory, then a command number and a start bit in the two
registers just past the end of it. The answer comes back out of the same memory.


## Install
```bash
git clone --recurse-submodules https://github.com/gufranco/snes-st-python.git
cd snes-st-python
```

Python 3.12 or newer, and the submodule. Nothing else.

The submodule sits at the repository root as
[`nec-upd7725-96050-python/`](https://github.com/gufranco/nec-upd7725-96050-python),
named after itself rather than buried under a generic folder, because it is the
processor both of these parts are built on. Without it nothing here can run.

The microcode is a separate matter and is not carried here. Where to put a copy
you already own is under [the microcode you supply](#the-microcode-you-supply).

## The interface
Everything a caller touches. Nothing else is public.

| Name | What it is |
|:--|:--|
| `Chip(model, **options)` | A part of that model, running its own microcode |
| `describe(model)`, `MODELS`, `DEFAULT_MODEL` | The catalogue, without building anything |
| `available()` | Every part there is an image for on this machine |
| `why_not()` | Why the backend cannot run, or nothing when it can |
| `read(address)`, `write(address, value)` | The two accesses a cartridge makes |
| `handshake()` | What the console does to wake the part |
| `reset()` | Back to a part that has not been woken, handed back for chaining |
| `step(count)` | Run the processor for a number of its own instructions |
| `UnknownModelError`, `NoFirmware`, `NeverFinished` | What a caller can catch |
| `Unrecognised`, `Corrupt`, `WrongShape` | What a supplied image can be refused for |

`Chip` takes the model first, which is the argument every member of the family
takes first. The name is the kind rather than the chip, so a traceback says what
sort of thing it was rather than which of two parts happened to raise.

```python
from snesst import Chip, describe

describe("seta011").name

# 'st011'
```

Either part is reached the same way, by the name it is known as:

```python
from snesst import Chip

print(Chip("st010").part, Chip("st011").part)

# st010 st011
```

A name no part answers to is refused rather than quietly building the default:

```python
from snesst import Chip, UnknownModelError

try:
    Chip("st012")
except UnknownModelError as refused:
    print(str(refused).split(";")[0])

# st012 is not a part this package covers
```

### The two parts

| Name | Also answers to | What it does |
|:--|:--|:--|
| `st010` | `st-010`, `seta010`, `setast010` | Eight commands for a racing cartridge |
| `st011` | `st-011`, `seta011`, `setast011` | A shogi opponent |

## The problem
This chip has no port. It shares four kilobytes of battery-backed memory with the
console: every command reads its arguments out of fixed addresses in that memory
and writes its answers back into other fixed addresses in the same memory.

Underneath, both ST parts are a NEC uPD96050 with a program masked into it. What
a command computes is that program. Working out what each one does and writing it
down produces something that can be checked and can never be finished, and for
these two it produces something worse: the tables this chip works from cannot be
restated as the formulas that made them. Each agrees with school mathematics to
within a unit or two and none agrees exactly, which is what a table computed by
an iterative routine on the machine that would use it looks like.

So carrying them means carrying the chip's content, and deriving them means being
slightly wrong everywhere.

## The solution
Run the program. Neither problem survives it: nothing needs deriving, and nothing
of the chip's content is carried.

The ST011 arrives with that change. It plays shogi, so its behaviour was never a
set of commands anybody could write down; it is the player masked into it. A part
that plays shogi and a part that computes a bearing are the same arrangement once
the program is run, so both are here.

The cost is stated plainly: without an image this package refuses. It does not
fall back to a guess, because an answer that did not come from the part is worse
than no answer.

## Why there is no model here
This used to carry a hand-written implementation of the ST010's eight commands
and fifteen hundred lines of the tables they worked from. Its own opening said
none of those tables could be restated as a formula. All of it is gone, along
with the corpus recorded from another implementation that existed to check it.

## The microcode you supply
Every image is identified before a byte of it is executed. SHA-256 decides; the
other values are there so you can cross-check against a database that keys on
them.

| Part | Bytes | CRC32 | SHA-256 |
|:--|--:|:--|:--|
| `st010` | 53,248 | `8d136190` | `55c697e864562445621cdf8a7bf6e84ae91361e393d382a3704e9aa55559041e` |
| `st011` | 53,248 | `750c6012` | `651b82a1e26c4fa8dd549e91e7f923012ed2ca54c1d9fd858655ab30679c2f0e` |

Confirm one you hold:

```bash
shasum -a 256 firmware/st0010.bin      # macOS
sha256sum firmware/st0010.bin          # Linux
certutil -hashfile firmware\st0010.bin SHA256   # Windows
```

A file that does not match is refused rather than run.

## The handshake nothing documents
The model this replaced treated one write as a switch. A write below the shared
window made the chip start listening, and until it arrived the two registers past
the end of memory could not be set at all.

On the part there is no switch. The window below the shared memory is the
processor's own data port, and the window above it is the processor's scratch
memory, which is the four kilobytes the console shares. That single fact explains
the write the model could not account for: the microcode raises its attention bit
on its very first instruction and waits for the console to take a word off the
data port. Until that happens it never reaches the loop that watches for a
command, so a part spoken to without it answers nothing and reads as broken.

A console does that at power-on without being told, and so does this. Past it,
each part sits in a wait of its own, measured on each rather than assumed.

| Part | Where its program waits |
|:--|:--|
| ST010 | words 3, 4 and 5, testing the top bit of the word holding the command and the start byte |
| ST011 | word 2 |

Measured rather than asserted, on whichever images are on this machine:

```python
from snesst import Chip, available

for name in sorted(available()):
    print(name, Chip(name).core.registers.pc)
```


## Is it right
A machine holding no microcode still checks everything this package can get
wrong, because the part-specific knowledge is no longer in the code.

| Layer | What is checked | Needs an image |
|:--|:--|:--:|
| The processor | Every instruction, in [`nec-upd7725-96050-python`](https://github.com/gufranco/nec-upd7725-96050-python) | No |
| The decode | The wake write, the two registers past memory, the shared window, driven by a program of zeroes | No |
| Identity | That both parts name an image with a deciding digest, so a supplied file is confirmed rather than trusted | No |
| The catalogue | Both parts, every name they answer to, and which image each runs | No |
| The parts | That each reaches its own wait, stays there, and answers a command | Yes |

That last one is the only check that needs an image, and it reports as skipped
rather than as passed when there is none.

**Open questions** are listed with the measurement that would close each one:
[`OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md). Where two sources part, both are kept
in [`conformance/divergences.json`](conformance/divergences.json) with what would
settle it.

## Working on it
```bash
python -m coverage erase
for file in $(find st010 conformance -name '*.test.py' | sort); do
  python -m coverage run -a "$file"
done
python -m coverage report
```

`python3 snesst/doctor.py` says what is actually on this machine: both parts, which image each wants, where each one's program stops waiting, and the state of the processor underneath. It is run as a file rather than with `-m` so that it still runs when the package itself will not import, which is the case it exists for.

[`AGENTS.md`](AGENTS.md) is the document for an agent working here. [`FAMILY.md`](FAMILY.md) is the standard this repository shares with the rest of the family, kept identical in every member.

### Project structure

```text
snesst/
  __init__.py       the package, and the part chosen at construction
  models.py         which parts exist, what they answer to, which image each runs
  chip.py        loading an image, the handshake, and driving the part
  microcode.test.py the checks that need a real image, kept out of the gate
  version.py        rewritten by the release job and by nothing else
nec-upd7725-96050-python/ the processor both of these are, as a submodule at the root
```

Each module has its tests beside it as `<module>.test.py`, so a module and the
cases that pin its behaviour are read together.

### Tests

```bash
for f in snesst/*.test.py; do python3 "$f"; done
```

| Area | File | What it pins |
|:--|:--|:--|
| The catalogue | [`snesst/models.test.py`](snesst/models.test.py) | Both parts, their names, their images, and that each image is declared with a digest |
| The part | [`snesst/chip.test.py`](snesst/chip.test.py) | Loading, the handshake, the decode, the shared memory, refusing |
| The microcode | [`snesst/microcode.test.py`](snesst/microcode.test.py) | That each part reaches its own wait and answers a command. Needs an image |

Coverage is enforced at 100% of statements and branches by
[`pyproject.toml`](pyproject.toml), so a new branch without a test fails the
build rather than quietly lowering the number.

### Development

| Command | Description |
|:--|:--|
| `ruff format .` | Format |
| `ruff check .` | Lint |
| `python3 -m coverage run -a <file>` | Run one test file under coverage |
| `python3 -m coverage report` | Coverage, which fails below 100% |
| `python3 snesst/microcode.test.py -v` | Run the checks that need an image |
| `pnpm run format:check` | Check that every JSON file is formatted, which CI also does |

### Project conventions

| Convention | Source |
|:--|:--|
| Commit format | [Conventional Commits](https://www.conventionalcommits.org/) |
| Formatting and lint | [ruff](https://docs.astral.sh/ruff/), pinned in [`.github/workflows/ci.yml`](.github/workflows/ci.yml) |
| Versioning | [semantic-release](https://semantic-release.gitbook.io/), from the commit history |
| Tests | Beside the module, named `<module>.test.py` |

### Versioning

This project follows [Semantic Versioning](https://semver.org/). Every release is
tagged. See [releases](https://github.com/gufranco/snes-st-python/releases) for
the changelog and upgrade notes.

### FAQ

<details>
<summary><strong>Why will it not work without a firmware image?</strong></summary>
<br>

Because what these parts do is the program masked into them, and that program
belongs to whoever made the part. A package that answered without one would be
answering from a description somebody wrote.

</details>

<details>
<summary><strong>Where do I get the microcode?</strong></summary>
<br>

Not from here, and this will not tell you. Dump it from hardware you own. The
digests above let you confirm that what you have is what the part expects.

</details>

<details>
<summary><strong>Why is the ST011 here now when it was refused before?</strong></summary>
<br>

It plays shogi. Its behaviour was never a set of commands that could be written
down, which is exactly why it was refused by name while this package described
things rather than running them. Running the program removes the distinction:
both parts are a processor and a mask ROM, and both are reached the same way.

</details>

## References
This repository carries no documents and no microcode. Every claim is traced to
something published elsewhere, listed here so a reader can fetch the same file
and check the same page.

Seta published nothing about either part. The top rung of the authority ladder is
empty here and [`conformance/hardware.json`](conformance/hardware.json) says so
rather than promoting the rung below it.

| Source | Used for |
|:-------|:---------|
| [nec-upd7725-96050-python](https://github.com/gufranco/nec-upd7725-96050-python) | The processor itself: its data sheet, its record, its divergences and its corpus |
| [snes-driver-python](https://github.com/gufranco/snes-driver-python) | Reading a cartridge's own code to find what it says to its coprocessor |
| The microcode a reader supplies | Every answer this package gives. Confirmed by digest before a byte of it runs |

## Citing this
[CITATION.cff](CITATION.cff) is kept in step with the released version by the same script that stamps the package, so the version it names is the version that shipped. GitHub renders it as a Cite this repository button.

## License
[MIT](LICENSE)
