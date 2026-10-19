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

| Call                                     | What it does                                                     |
| :--------------------------------------- | :--------------------------------------------------------------- |
| `read(address)`, `write(address, value)` | The two accesses a cartridge makes                               |
| `handshake()`                            | What the console does at power on to wake the part               |
| `step(count)`                            | Run the processor for a number of its own instructions           |
| `finish()`                               | Run a started command until its program clears the start bit     |
| `reset()`                                | Back to a part that has not been woken, handed back for chaining |

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

**Not settled: 7 things**, each in
[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) with the measurement that would close it.
Six are the interface rather than the behaviour: the memory map, the number of
registers, timing, and what a reset does. The seventh is how wide the recorded
cartridge accesses are where nothing settled it: every recorded width carries
its label, known, `*` for a run, `~` for a trace or `?` for an assumption
replayed as one byte, and no label is ever dropped.

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

## Test cartridges

[`conformance/testroms.json`](conformance/testroms.json) names the three program
dumps that exercise this member, each keyed by the SHA-256 of the file on disk
and never committed. They live in `snes-roms/5 Tools & Service Test Carts/CPU/`
in the local library. All three are `run`: the ST010 and ST011 dumps store each
word low byte first and are read through that reversal, and the ST018 dump is
read as it stands.

```bash
python3 -m conformance.testroms "../snes-roms/5 Tools & Service Test Carts/CPU"
python3 -m conformance.testroms --record FOLDER   # only after a deliberate model change
```

What each run reports is recorded in
[`conformance/testroms_measured.json`](conformance/testroms_measured.json): the
word each signal processor program waits at, the ST010's answer to command 1
and the instructions it took, and the byte the ST018 program answers an unknown
command with. [`conformance/testroms.test.py`](conformance/testroms.test.py)
replays those verdicts with no image present against the record and the README.
Without an image the runner exits 2 and CI annotates the skip.

No whole-console test cartridge reaches these parts: none of the factory,
service or community cartridges on disk carries a Seta coprocessor, and the SNES
catalogue names none, so nothing waits on another member.

## Every gate, in the order to run them

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 --with types-setuptools==84.0.0.20260812 mypy==1.14.1
pnpm install --frozen-lockfile && pnpm run format:check
uvx yamllint==1.38.0 --strict .
cov=(uvx --python 3.12 --from coverage==7.6.10 --with setuptools==84.0.0 coverage)
"${cov[@]}" erase
for f in $(find snesst conformance -name '*.test.py' | sort); do
  "${cov[@]}" run -a "$f" || echo "FAILED $f"
done
"${cov[@]}" report
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
- No comments in source, and a docstring counts as one. A step that would need
  a comment is a step that should be a named function.
- Tests sit beside the module they cover as `<module>.test.py`. Arrange, act
  and assert, each block opened by its bare marker.
- 100% statement and branch coverage, enforced. `mypy` at strict, with every
  optional error class on.
- Everything a caller can catch is defined once, in `snesst/errors.py`, and
  imported from there.
- A check nobody has seen fail is not known to work. Drive every new check
  against input that should fail it before keeping it.

The linter's ignores in [`pyproject.toml`](pyproject.toml) carry no comments, so
their reasons live here, beside those of the other exclusions:

- `nec-upd7725-96050-python` is excluded from `ruff`: the submodule carries its
  own gate at its own version, so this lint never depends on a commit made in a
  different repository.
- `N818`: three exceptions are control flow signals rather than failures, named
  the way CPython names `StopIteration`. Those that report a failure end in
  `Error`.
- `BLE001` and `T201` in `environment.py`: it reports what a machine is, so a
  check that throws becomes a line in the report rather than ending the run.
- `N999` in tests: a test file is named after the module it covers, with a dot,
  so a module and its tests are read together.
- `T201` in `conformance/`: these are command line tools and printing is their
  output. A logger would put a level and a timestamp in front of a report meant
  for a person.
- `BLE001` and `T201` in the doctor: it must survive whatever a check throws and
  report it, because a narrower catch would let a traceback take the rest of the
  report with it.
- Every optional `mypy` error class is on because the errors that matter in a
  model of hardware are a width, a mask or a `None` crossing a boundary.
- The `arm6.*`, `upd7725.*`, `mapper.*` and `snesdriver.*` override in `mypy`:
  the submodules are checked in their own repositories, against their own gate.
- [`snesst/microcode.test.py`](snesst/microcode.test.py) is omitted from
  coverage: it drives real microcode, a file nobody may distribute, so no single
  build can take every path. It reports as skipped instead. The submodule
  directories are omitted too.
- The `__main__` guard is excluded from coverage: it hands argv to a tested
  function, and importing the module to cover it would run the tool.
- The doctor's `sys.path` guard is excluded: a suite that imports the doctor has
  already put the repository on the path, so no test can take that branch.
- `if TYPE_CHECKING:` is excluded: it never runs, and Python 3.14 drops it before
  coverage sees it while earlier versions do not.
- A lone ellipsis and a signature ending in one are excluded: a protocol method
  has no body to run, and the same version split applies.
- `@unittest\.skipUnless\(CLOCKED,` in the coverage exclusions: this member is
  not a clocked part, so the family tests that drive a clock are skipped here
  and their bodies never run.
- `@unittest\.skipUnless\(QUOTED,` in the coverage exclusions: this record
  quotes no document, so the family tests that hold a quote checker to the
  pipeline are skipped here.
- `@unittest\.skipUnless\(SOLD_AS_A_COMPONENT,`, `^def machine_mentions\(` and
  `^def listing\(` in the coverage exclusions: this part only existed inside one
  machine, so the family sweep for machine names is skipped here.
- `@unittest\.skipUnless\(A_PART and BUILDABLE,` in the coverage exclusions:
  building a part needs a file this repository does not carry, so on a runner
  without it the family tests that build one are skipped.

The formatter's ignores in [`.prettierignore`](.prettierignore) carry no
comments either, so their reasons live here:

- `pnpm-lock.yaml` and `package-lock.json`: the package manager writes them, in
  its own layout, on every install.
- `node_modules/`, `.venv/`, `venv/`, `build/`, `dist/` and `*.egg-info/`:
  installed or built, never written by hand.
- `.coverage`, `coverage.json`, `htmlcov/` and the tool caches: the output of a
  run, never committed.
- `docs/`, `specs/`, `.work/` and `.claude/`: local working material, never
  committed.
- `nec-upd7725-96050-python/`, `snes-driver-python/` and `arm6-python/`:
  submodules. Each is a member that formats and checks itself, and the commit
  pinned here is not this repository's to change.

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
  family_*.test.py the family standard, held to this repository, one topic a file
  family_member.py what this member answers to them
  family_shared.py what more than one of them reads
  hardware.json   what this package asserts, and where each assertion comes from
  divergences.json where sources part, and what would settle each
  speed.py        the throughput floor
  testroms.py     the program dumps the record names, run and held to their verdicts
nec-upd7725-96050-python/  the processor both parts are, as a submodule at the root
```

## Things that will bite you

- **The directory variable is `SNES_ST_FIRMWARE_DIR`, and the old shared one
  still works.** `UPD7725_FIRMWARE_DIR` named this member's images and
  snes-dsp-python's at once, so a caller holding both sets could point at only
  one of them. It is now read after this member's own name rather than instead
  of it. A test pins both halves: the old name still finds a directory, and the
  new one wins when both are set.
- **The search order lives in three members and nothing holds them together.**
  `directories` in `firmware.py` is byte-identical here, in the other microcode
  member and in `sony-s-smp-python`, because no package is a dependency of all
  three. The copies are byte-identical from `def directories` to
  `return tuple(seen)`, so a diff against a sibling is the check:

  ```sh
  cut='/^def directories/,/^    return tuple(seen)/p'
  diff <(sed -n "$cut" mine/firmware.py) <(sed -n "$cut" theirs/firmware.py)
  ```

  Change one and change the other two in the same task.

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
