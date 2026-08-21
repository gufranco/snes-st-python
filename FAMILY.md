# The family standard

These sixteen repositories are one family and are held to one standard. Where
they differ, the difference must be something the hardware forces, not something
nobody got round to.

| Repository | What it models |
|:--|:--|
| [mos65xx-python](https://github.com/gufranco/mos65xx-python) | The 65xx family, eight parts |
| [nec-upd7725-python](https://github.com/gufranco/nec-upd7725-python) | The DSP the SNES coprocessors are built on |
| [snes-driver-python](https://github.com/gufranco/snes-driver-python) | Reading a cartridge's own coprocessor protocol |
| [snes-dsp-python](https://github.com/gufranco/snes-dsp-python) | The DSP-1 to DSP-4 family |
| [snes-graphics-python](https://github.com/gufranco/snes-graphics-python) | The Super Nintendo graphics formats |
| [snes-mapper-python](https://github.com/gufranco/snes-mapper-python) | Cartridge headers and address decoding |
| [snes-obc1-python](https://github.com/gufranco/snes-obc1-python) | The OBC1 sprite remapper |
| [snes-rom-image-python](https://github.com/gufranco/snes-rom-image-python) | A cartridge image as a file |
| [snes-rtc-python](https://github.com/gufranco/snes-rtc-python) | The two cartridge real-time clocks |
| [snes-sdd1-python](https://github.com/gufranco/snes-sdd1-python) | The S-DD1 decompressor |
| [snes-spc7110-python](https://github.com/gufranco/snes-spc7110-python) | All three modes of the SPC7110 decompressor |
| [snes-st010-python](https://github.com/gufranco/snes-st010-python) | The two Seta coprocessors |
| [sony-s-dsp-python](https://github.com/gufranco/sony-s-dsp-python) | The Sony S-DSP, on the clock schedule the hardware runs on |
| [sony-spc700-python](https://github.com/gufranco/sony-spc700-python) | The Sony SPC700, the audio unit's processor |
| [star-ocean-nochip-fix](https://github.com/gufranco/star-ocean-nochip-fix) | One header correction, end to end |
| [zilog-z80-python](https://github.com/gufranco/zilog-z80-python) | The Z80 |

## The authority ladder

Every factual question is answered by the highest rung that has an answer, and a
lower rung never overrules a higher one.

1. **Manufacturer documentation.** Anything printed decides. Read it in full
   rather than searching it, because the passages that matter are the ones
   nobody quotes.
2. **The part's own program or the artefact itself.** A cartridge, a firmware
   image, a header. What the silicon was actually asked to do.
3. **A recording from an independent implementation**, for behaviour nobody
   documented.
4. **Nothing else.** An emulator, an FPGA core, a wiki and a forum post are rung
   3 at best and rung 4 for anything printed.

A document that contradicts itself is common. When it does, the cycle table and
the pin descriptions have both times been right and the prose wrong.

**Never calibrate against an emulator where a document exists.** A recording is
evidence about behaviour nobody wrote down. It is not evidence about a register
width, a bit name, or anything else a manufacturer printed, however many
implementations agree with it. Where a recording contradicts a document, the
document wins, the disagreement is written down, and the model follows the
document.

**A recording whose answer depends on the machine it was built on is not evidence
at all.** It is a property of the recorder, and it is excluded and named rather
than allowed to decide.

## What every repository carries

| Gate | Standard |
|:--|:--|
| Format | `ruff format --check .`, clean |
| Lint | `ruff check .`, zero findings |
| Types | `mypy` at strict plus every optional error class, zero findings |
| Tests | `<module>.test.py` beside the module, run individually |
| Coverage | 100% statement and branch, enforced, on a machine holding no artefacts |
| JSON | `pnpm run format:check`, with every submodule tree exempted |
| CI | lint, types, tests on 3.12/3.13/3.14, plus the project's own conformance job |
| Schedule | a weekly run against unpinned tools and the newest runtime, starting on ground the pipeline never reaches |
| Analysis | CodeQL and Scorecard |
| Release | semantic-release from `main`, never tagged by hand |
| Docs | README, AGENTS.md plus the one-line pointer each tool reads, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT |
| Review | CODEOWNERS on every path, and templates that ask a report for the run that settles it |
| Specs | `specs/current/`, requirements with checkable scenarios |
| Hardware facts | `conformance/hardware.json`, every fact with the sentence it came from |
| Disagreements | `conformance/divergences.json`, both readings and what would settle it |

## Conventions that are not negotiable

| Thing | Rule |
|:--|:--|
| Language | Python only |
| Comments | None in source, ever. Docstrings carry the reasoning |
| Test structure | Arrange, blank line, one act, blank line, assert. No section labels |
| Nothing starts clean | Memory and registers hold what they held, from a seed |
| Artefacts | Never committed: no ROM, no firmware, no fragment of one |
| Only retail dumps | A ROM hack is somebody's edit, not what hardware ran |
| Package manager | pnpm, never npm |

## What a conformance runner must report

A runner asked about ground it has never been held to has three options and two
of them are lies. Reporting agreement lies about the part. Skipping in silence
lies about the run, because the summary then counts a comparison that never
happened. The third is to refuse: name what was compared, name what was not and
why, and count the two apart.

Report per part, never one number over parts with different evidence. One part
held to its manufacturer's manual and another held to nothing are not one figure.

## The state of this repository
## The state of this repository

**This package has no model of what the commands compute, and that is the
design.** It runs the program masked into each part's ROM on a model of the
processor underneath, so what it answers is what that program answers. A derived
model covers the commands somebody thought to look at, and the corners nobody
characterised are exactly where one is silently wrong.

**One of those corners is recorded, because it was found.** Derived models
account for a write that none of the eight commands explains, usually by treating
an address as an enable switch. On the part there is no switch: the program
raises its attention bit on its first instruction and waits for the console to
take a word off the data port, and until that happens it never reaches the loop
that watches for a command. A part spoken to without that answers nothing and
reads as broken. That is in
[`conformance/divergences.json`](conformance/divergences.json) as the case that
justifies the whole approach.

**The two parts do not wait alike.** The ST010 watches words 3, 4 and 5 and the
ST011 watches word 2, each measured by running its own program rather than
assumed from the other. Assuming would have made one of them silently wrong on a
cartridge nobody tested.

**The interface is the weak part, and it is marked.** Running the microcode
settles what the part computes and settles nothing about where the console
reaches it. The enable bit, the two register addresses and the size of the shared
window all come from a reference, and they sit underneath everything else here.
The shared window has one corroboration that is not a reference: it is 2048
sixteen bit words, which is the data RAM the uPD96050 is asserted to have, and
that figure is itself corroborated by the firmware images loading at exactly
their declared sizes.

**No image is carried here.** A manifest of lengths and four digests each, with
SHA-256 deciding, and a file that does not match is refused rather than run.

**Nothing here is a timing claim.** Counting instructions would need the
oscillator on the cartridge board, which is a figure nobody printed.
