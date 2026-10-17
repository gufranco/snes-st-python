# Seta ST010, ST011 and ST018

The three coprocessors Seta made for Super Nintendo cartridges in Python, each running the microcode a reader supplies and held to the place that microcode stops to wait for a command.

English | [日本語](README.ja.md) | [简体中文](README.zh-Hans.md) | [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/snes-st-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-st-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/snes-st-python)](https://github.com/gufranco/snes-st-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**3** parts, **0** commands described by hand, both waits measured on the shipped microcode, **0** disagreements between those waits and the record, **705** tests, **100%** statement and branch coverage, no dependencies

```python
from snesst import Chip

part = Chip("st010")

part.write(0x000000, 0x00)
for at, value in enumerate((0x00, 0x01, 0x00, 0x02)):
    part.write(0x680000 + at, value)
part.write(0x680020, 0x01)
part.write(0x680021, 0x80)

print(hex(part.read(0x680010) | part.read(0x680011) << 8))
```

```
0x9300
```

The write to `0x000000` lands below the shared window, on the processor's data port, and lets the part act on a start byte. The next four bytes put the point `0x0100, 0x0200` at the bottom of the shared memory. Command `0x01` goes in the register byte at `0x20` and the start bit in the one at `0x21`, and the ST010's own program runs until it clears that bit. The answer comes back out of the same memory at `0x10`. The example needs an ST010 image; without one, `Chip("st010")` raises `NoFirmware`.

## Install

| Requirement | Version |
|:--|:--|
| Python | 3.12 or newer |
| git | Any, to fetch the submodules |
| A firmware image | One per part you build, dumped from hardware you own |

```bash
git clone --recurse-submodules https://github.com/gufranco/snes-st-python.git
cd snes-st-python
python3 snesst/doctor.py
```

The package imports nothing outside the standard library. Three submodules sit at the repository root: `nec-upd7725-96050-python` is the processor inside the ST010 and ST011, `arm6-python` is the processor inside the ST018, and `snes-driver-python` is read only by the tool that records cartridge exchanges. A source archive from the download-zip link has no submodules, and every part then refuses to build.

The doctor checks the machine, the submodules and each part's image, and ends with one line. Paste its whole output into any bug report. A fresh checkout holds no image, so its three part lines fail:

```
  3 of 12 checks did not pass
```

Releases follow [Semantic Versioning](https://semver.org/) and are cut from the commit history by semantic-release. Every release is tagged and listed on the [releases page](https://github.com/gufranco/snes-st-python/releases).

## The interface

`snesst.Chip(model, **options)` builds one part. `model` is required and is matched without regard to case, hyphens or underscores. The ST010 and ST011 come back as `snesst.chip.Chip`, which runs a NEC uPD96050. The ST018 comes back as `snesst.ST018`, which runs an ARM60.

| Model | Aliases | Processor | Image bytes | What the program does |
|:--|:--|:--|--:|:--|
| `st010` | `st-010`, `seta010`, `setast010` | uPD96050 | 53,248 | Eight commands for a racing cartridge |
| `st011` | `st-011`, `seta011`, `setast011` | uPD96050 | 53,248 | Plays shogi |
| `st018` | `st-018`, `seta018`, `setast018` | ARM60 | 163,840 | Plays shogi, through a one byte mailbox |

### The catalogue and the errors

| Name | Content |
|:--|:--|
| `snesst.MODELS` | The three `Model` records, keyed by canonical name |
| `snesst.Model` | `name`, `aliases`, `summary`, and `image`, the name of the image it runs |
| `snesst.available()` | A dict of every part whose image is on this machine, each an identity and a path. Empty when the uPD96050 submodule is missing |
| `snesst.why_not()` | The sentence saying why no part can be built here, because the uPD96050 submodule or every image is missing. `None` otherwise |
| `snesst.ST018` | The ARM part's class, for a caller who builds it directly |
| `snesst.__version__` | The installed version |

| Error | Raised when |
|:--|:--|
| `UnknownModelError` | The model is missing or no part goes by that name. The message lists the names accepted |
| `NoFirmware` | A processor submodule is not checked out, no image for the part is found, or an image is passed to a uPD96050 part without an `identity` |
| `NeverFinished` | A started command has not cleared the start bit within `patience` instructions |
| `WrongShape` | An image is not the length its processor takes |
| `Unrecognised` | `snesst.firmware.identify` meets bytes whose SHA-256 the manifest does not hold. The directory search skips such a file instead |
| `Corrupt` | An image matches a manifest entry on SHA-256 and disagrees with it on another digest |
| `UnknownPort` | An ST018 read or write lands on an address other than its three ports |

```python
import snesst
from snesst import Chip, UnknownModelError

for name, model in snesst.MODELS.items():
    print(name, model.aliases)

print(repr(snesst.MODELS["st018"]))

for asked in ("st012", None):
    try:
        Chip(asked)
    except UnknownModelError as refused:
        print(refused)
```

```
st010 ('st-010', 'seta010', 'setast010')
st011 ('st-011', 'seta011', 'setast011')
st018 ('st-018', 'seta018', 'setast018')
<Model st018, running the st018 image>
st012 is not a model this package covers; it has st010, st011, st018
no model was named, and this package will not choose one for you. Name one of: st010, st011, st018
```

### The ST010 and ST011

`Chip("st011", memory=None, fill=0, patience=4000000, boot=200000, image=None, identity=None, images=None)` shows every option with its default.

| Option | Effect |
|:--|:--|
| `memory` | Bytes copied into the shared memory after the handshake, up to 4,096 of them |
| `fill` | The value the processor's registers and memories hold at power-on |
| `patience` | Instructions a started command may run before `NeverFinished` |
| `boot` | Instructions run after the handshake's two reads, before the part is handed back |
| `image` | The image bytes. No directory is searched and no variable is read |
| `identity` | What `image` is, as a `snesst.firmware.Identity`. Required with `image` |
| `images` | A catalogue shaped like `available()`, searched in place of this machine's |

| Call | Effect |
|:--|:--|
| `read(address)` | With bit `0x80000` set, the shared memory byte at `address & 0xFFF`. Otherwise the data port, or the status port at an odd address |
| `write(address, value)` | With bit `0x80000` set, a shared memory byte, then the program runs if the part is enabled and the byte at `0x21` has bit `0x80`. Otherwise a write that enables the part, passed to the data port at an even address |
| `handshake(boot=None)` | One instruction, two reads of the data port, then `boot` instructions. Returns the part |
| `step(count)` | `count` processor instructions |
| `reset()` | Clears `enabled`. The program and the shared memory are untouched. Returns the part |

| Attribute | Meaning |
|:--|:--|
| `model`, `part` | The canonical model name |
| `processor` | `upd96050` |
| `identity` | The `Identity` of the image that runs |
| `core` | The processor from `nec-upd7725-96050-python` |
| `console` | The host side of the processor's ports |
| `enabled` | True once a write below the shared window has arrived since the last reset |
| `memory` | The 4,096 bytes of shared memory, read without side effects |
| `command`, `execute` | The register bytes at `0x20` and `0x21` |
| `patience`, `boot` | The values passed in |

```python
from snesst import Chip, NeverFinished
from snesst.firmware import Identity

blank = Identity("st010", "upd96050", "blank", program_words=16384, data_words=2048)
part = Chip("st010", image=bytes(53248), identity=blank, boot=0, patience=1000)

part.write(0x680005, 0x7F)
part.write(0x680020, 0x02)
print(hex(part.read(0x680005)), part.memory[5], part.command, part.enabled)

part.write(0x600000, 0x00)
try:
    part.write(0x680021, 0x80)
except NeverFinished as refused:
    print(refused)

print(part.reset().enabled, repr(part))
```

```
0x7f 127 2 False
st010 did not finish command 0x02 within 1000 instructions
False <Chip st010 on upd96050>
```

A program of zeroes needs no image, so this runs on any checkout with its submodules. The shared memory and the registers take writes before the part is enabled. Once the write to `0x600000` enables it, the start bit runs the program, which never clears the bit, and the part gives up after 1,000 instructions.

### The ST018

`Chip("st018", image=None, images=None, fill=0, processor=None)` shows every option with its default. `image` is 163,840 bytes, 131,072 of program and 32,768 of data, and is not identified first. `images` is an iterable of identity and path pairs searched in place of this machine's directories. `processor` names a checkout of `arm6-python` other than the submodule.

| Call | Effect |
|:--|:--|
| `read(0x3800)` | The byte the ARM sent, once. Clears the waiting flag, and reads 0 when nothing is waiting |
| `write(0x3802, value)` | A byte for the ARM. Sets the sent flag |
| `read(0x3804)` | The status byte: `0x01` a byte waits for the console, `0x08` a byte waits for the ARM, `0x80` the part is up |
| `write(0x3804, value)` | Resets the part when bit 0 is set |
| `status()` | The status byte, read the same way |
| `port(offset)`, `drive(offset, value)` | The ARM's side of the mailbox: reading offset `0x10` takes the console's byte, reading `0x20` gives the status, driving `0x00` sends a byte to the console and driving `0x20` sets `timer` |
| `step(count=1)` | `count` ARM instructions. Returns the part |
| `reset()` | Empties the mailbox, sets the part up and resets the ARM. Returns the part |

| Attribute | Meaning |
|:--|:--|
| `model`, `part` | `st018` |
| `processor` | `arm60` |
| `identity` | The `Identity` of the image found, or `None` when `image` was passed |
| `core` | The `arm6.Cpu` running the program |
| `stores` | The ARM's address space: program at `0x00000000`, ports at `0x40000000`, data at `0xA0000000`, 16 KB of work RAM at `0xE0000000` |
| `incoming`, `outgoing`, `sent`, `waiting`, `up`, `timer` | The mailbox state behind the status byte |
| `steps` | ARM instructions run since the part was built. A reset leaves it alone |

```python
from snesst import Chip, UnknownPort

part = Chip("setast018", image=bytes(163840))
print(type(part).__name__, part.model, part.processor, hex(part.status()))

part.write(0x3802, 0x2A)
print(hex(part.read(0x3804)), hex(part.port(0x10)), hex(part.read(0x3804)))

part.drive(0x00, 0x99)
print(hex(part.read(0x3804)), hex(part.read(0x3800)), hex(part.read(0x3804)))
print(part.step(100).steps)

try:
    part.read(0x3806)
except UnknownPort as refused:
    print(str(refused).split(".")[0])
```

```
ST018 st018 arm60 0x80
0x88 0x2a 0x80
0x81 0x99 0x80
100
nothing establishes what a read of $3806 does
```

A zeroed image builds an ARM that runs zeroes, so the mailbox can be driven without the real program. The console's byte raises bit `0x08` until the ARM takes it, and the ARM's byte raises bit `0x01` until the console takes it.

### Command-line tools

Each runs from the repository root.

| Command | Arguments | Exit codes |
|:--|:--|:--|
| `python3 snesst/doctor.py` | None | 0 when every check passes, 1 when any fails |
| `python3 -m conformance.speed` | None | 0 at or above 150,000 uPD96050 instructions a second, or when no part can be built here. 1 below that |
| `python3 -m conformance.against_cartridges` | A part, `st010` by default | 0 when at least one recorded exchange got a byte back, 1 when none did, 2 when no part can be built here |
| `python3 -m conformance.record` | A directory of cartridges, then an output directory | 0 when every part found yields shapes, 1 when one yields none, 2 for a missing argument, a missing directory, or no cartridge carrying a part |
| `python3 -m conformance.links` | None | 0 unless an address in this README answers 404 or 410 |
| `python3 -m conformance.package` | A built wheel | 0 when every module is in it and no test is, 1 otherwise or when the file is absent, 2 without an argument |

`conformance.against_cartridges` plays the exchanges in [`conformance/st010shapes.json`](conformance/st010shapes.json) and [`conformance/st011shapes.json`](conformance/st011shapes.json) at the part. `conformance.record` writes those files: it reads each cartridge's own code through `snes-driver-python` and keeps the shape of every exchange, never a byte of the cartridge. It accepts only cartridges named in that submodule's manifest and checks all four of their digests.

## The problem

The ST010 and ST011 have no port of their own. Each shares four kilobytes of memory with the console. A command reads its arguments from fixed addresses in that memory and writes its answers to other fixed addresses in it.

Inside, both are a NEC uPD96050 with a program masked into its ROM. What a command computes is that program. The tables it works from agree with the textbook formulas to within a unit or two and match none of them exactly, so restating them as formulas leaves an error in every entry, and carrying them means carrying the chip's content.

## The solution

The package runs the program. Nothing is derived and none of the chip's content is in the repository. The ST011 and ST018 play shogi, and running the program covers them the same way it covers the ST010's eight commands.

Without an image a part refuses to build. It never falls back to an answer that did not come from the part.

## The microcode you supply

Every image is identified before a byte of it runs. SHA-256 decides. The CRC32 is there to cross-check against a catalogue that keys on it.

| Part | Bytes | CRC32 | SHA-256 |
|:--|--:|:--|:--|
| `st010` | 53,248 | `8d136190` | `55c697e864562445621cdf8a7bf6e84ae91361e393d382a3704e9aa55559041e` |
| `st011` | 53,248 | `750c6012` | `651b82a1e26c4fa8dd549e91e7f923012ed2ca54c1d9fd858655ab30679c2f0e` |
| `st018` | 163,840 | `5c403cc5` | `6df209ab5d2524d1839c038be400ae5eb20dafc14a3771a3239cd9e8acd53806` |

[`snesst/artifacts.manifest.json`](snesst/artifacts.manifest.json) holds these with the MD5 and SHA-1 beside them. The search reads files ending in `.bin` or `.rom`, in this order, and the first image found for a part wins:

1. Every directory named by `SNES_ST_FIRMWARE_DIR`, separated the way the operating system separates a path.
2. Every directory named by `UPD7725_FIRMWARE_DIR`.
3. `firmware/` in the project this one is checked out inside.
4. `firmware/` in this repository.

Nothing is downloaded. Confirm a copy you hold on macOS, Linux or Windows:

```bash
shasum -a 256 firmware/st0010.bin
sha256sum firmware/st0010.bin
certutil -hashfile firmware\st0010.bin SHA256
```

A file whose digest is not in the manifest is skipped by the search. Passed to `snesst.firmware.identify`, it is refused, and the refusal says whether removing a 512 byte header, dropping the last 512 bytes or swapping byte pairs turns it into a known image.

## The handshake nothing documents

The window below the shared memory is the processor's data port, and the shared memory is the processor's own data RAM. The microcode raises its attention bit on its first instruction and waits for the console to take a word off the data port. Until that happens it never reaches the loop that watches for a command, and a part spoken to without it answers nothing.

`Chip` performs that handshake while building the part: one instruction, two reads of the data port, then 200,000 instructions. Each program then waits in a place of its own.

| Part | Where its program waits |
|:--|:--|
| ST010 | Words 3, 4 and 5, testing the top bit of the word holding the command and the start byte |
| ST011 | Word 2 |

```python
from snesst import Chip

for name in ("st010", "st011"):
    part = Chip(name)
    print(part.model, part.processor, part.core.registers.pc)
```

```
st010 upd96050 3
st011 upd96050 2
```

This example needs both images.

## Is it right

[`conformance/hardware.json`](conformance/hardware.json) records every value the package asserts about the interface, each marked unverified, with its evidence and the measurement that would settle it: the 4,096 byte shared window, enable bit `0x80000`, the register bytes at `0x20` and `0x21`, the two handshake reads, both wait places, and what a reset does. [`conformance/hardware.test.py`](conformance/hardware.test.py) drives a part built on a program of zeroes to hold the window, the enable bit, the registers and the handshake, and [`snesst/microcode.test.py`](snesst/microcode.test.py) holds both wait places on the real images.

| Layer | What is checked | Needs an image |
|:--|:--|:--:|
| The processors | Every instruction, in [nec-upd7725-96050-python](https://github.com/gufranco/nec-upd7725-96050-python) and [arm6-python](https://github.com/gufranco/arm6-python) | No |
| The decode | The enabling write, the two register bytes, the shared window, on a program of zeroes | No |
| The ST018 mailbox | Its three ports, its status bits and its refusals, on short ARM programs written in the tests | No |
| Identity | Each image named by a deciding digest, and every refusal a wrong file gets | No |
| The catalogue | All three parts and every name they answer to | No |
| The parts | The ST010 and ST011 each reach their own wait and stay there for 4,096 instructions, and the ST010 answers a command | Yes |

[`snesst/microcode.test.py`](snesst/microcode.test.py) carries the last row and reports as skipped when no image is present. A separate CI job starts every part, runs `conformance.against_cartridges` for the ST010 and ST011, and says on the run page whether a part was driven at all.

[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) lists what is not known with the measurement that would close each item. [`conformance/divergences.json`](conformance/divergences.json) records where sources part, and which one this package follows.

## Working on it

| Need | Where |
|:--|:--|
| Every gate and the order to run them | [CONTRIBUTING.md](CONTRIBUTING.md) |
| The same material for a coding agent | [AGENTS.md](AGENTS.md) |
| The standard this repository shares with the rest of the family | [FAMILY.md](FAMILY.md) |
| Bug reports | [GitHub Issues](https://github.com/gufranco/snes-st-python/issues) |
| Security reports | [SECURITY.md](SECURITY.md) |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 --with types-setuptools==84.0.0.20260812 mypy==1.14.1
pnpm install --frozen-lockfile && pnpm run format:check
cov=(uvx --python 3.12 --from coverage==7.6.10 --with setuptools==84.0.0 coverage)
"${cov[@]}" erase
for file in $(find snesst conformance -name '*.test.py' | sort); do "${cov[@]}" run -a "$file"; done
"${cov[@]}" report
python3 -m conformance.speed
```

Each module has a test file beside it, named after it, and each runs on its own, as in `python3 snesst/chip.test.py`. Coverage is a hard gate at 100% statement and branch, set in [pyproject.toml](pyproject.toml). The throughput floor runs outside the coverage step.

## References

- Seta published nothing about these parts. The top rung of the authority ladder in [`conformance/hardware.json`](conformance/hardware.json) is empty and the record says so.
- The microcode a reader supplies, for every answer the package gives. It is confirmed by digest before it runs and is not in this repository.
- [nec-upd7725-96050-python](https://github.com/gufranco/nec-upd7725-96050-python), for the uPD96050 and every fact NEC printed about it.
- [arm6-python](https://github.com/gufranco/arm6-python), for the ARM60 inside the ST018.
- [snes-driver-python](https://github.com/gufranco/snes-driver-python), for reading a cartridge's own code to find what it says to its coprocessor.
- The behavioural models in emulators, for the interface constants: where the shared memory sits and which addresses are registers.

## Citing this

[CITATION.cff](CITATION.cff) is updated with each release by the script that stamps the package version.

## License

MIT. See [LICENSE](LICENSE).
