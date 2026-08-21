# Working in this repository

This file is for a coding agent. A person reading it will not be harmed, but
[README.md](README.md) is the document written for them.

## What this project is, in one paragraph

The ST010 and ST011, run rather than described. Each is a NEC uPD96050 and a mask
ROM, so given the ROM there is nothing left to derive: this runs the program and
reports whatever it writes. It does not model what the eight commands compute.

## Why running it rather than describing it

A derived model covers the commands somebody thought to look at. The corners
nobody characterised are exactly where a derived model is silently wrong, and
this package exists because one of those corners was found.

**Derived models account for a write that none of the eight commands explains**,
usually by treating an address as an enable switch. On the part there is no
switch. Running the program shows what happens: it raises its attention bit on
its very first instruction and waits for the console to take a word off the data
port, and until that happens it never reaches the loop that watches for a
command. A part spoken to without that answers nothing and reads as broken.

That is in `conformance/divergences.json` as the case that justifies the whole
approach. **A change that replaces a piece of this with a derivation will be sent
back**, however correct the derivation looks.

## The authority ladder

1. **The microcode**, which is the part.
2. **NEC's data sheet**, by way of `nec-upd7725-python`, for anything NEC printed
   about the processor underneath.
3. **The reference implementation**, for the interface around the ROM.

## What running the program cannot settle

Where the console reaches the part. The enable bit, the two register addresses
and the size of the shared window all come from a reference, and they sit
underneath everything else here. `conformance/hardware.json` marks them and
`conformance/divergences.json` says outright that they are the weakest evidence
in the package.

The window has one corroboration that is not a reference: it is 2048 sixteen bit
words, which is the data RAM the uPD96050 is asserted to have, and that figure is
itself corroborated by the firmware images loading at exactly their declared
sizes.

## The two parts do not wait alike

The ST010 watches words 3, 4 and 5 while it waits; the ST011 watches word 2. Each
was measured by running its own program. **Assuming one from the other would make
one of them silently wrong on a cartridge nobody tested**, which is the same
failure this package exists to avoid.

## Every gate, in the order to run them

```bash
ruff format --check .                     # formatting
ruff check .                              # lint, zero warnings
mypy                                      # types, strict
pnpm run format:check                     # every JSON file
for f in st010/*.test.py conformance/*.test.py; do python3 "$f"; done
python3 -m coverage report                # fails below 100%
```

Checks that need an image skip rather than pass when it is absent, so a run that
proved nothing never reads as a run that proved something.

## Things that will bite you

**The submodule is required.** The processor lives in `nec-upd7725-python`, on the
path rather than installed. Without `git submodule update --init --recursive`
nothing here runs, and the doctor says so rather than failing obscurely.

**No image is carried here.** A manifest of lengths and four digests each, with
SHA-256 deciding. A file that does not match is refused rather than run, because
running the wrong image reports behaviour no hardware has.

**The two register addresses are ordinary memory to the microcode.** What makes
them registers is that the program watches them, not that the decode treats them
apart.

## Conventions

| Thing | Rule |
|:------|:-----|
| Language | Python only |
| Comments | None in source. Docstrings carry the reasoning, and say why rather than what |
| Test layout | `<module>.test.py` beside the module it covers |
| Test structure | Arrange, blank line, one act, blank line, assert. No section labels |
| Package manager for tooling | pnpm, never npm |
| Commits | Conventional Commits |
| Replacing a run with a derivation | Sent back. That is the failure mode this package was built against |
