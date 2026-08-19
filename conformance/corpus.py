"""Hold the ST010 to the chip's own reference.

The chip has no port. It shares a memory with the console, so a case is a memory
filled with arguments, a command number, and a start bit, and what comes back is
the whole memory afterwards. Comparing the whole memory rather than the addresses
a command is documented to write is deliberate: a model that writes the right
answer and also scribbles somewhere else would pass a narrower check and fail on
a console.

The arguments are generated from a seed and shaped to the ranges each command
takes, because a command handed nonsense produces nonsense and two
implementations agree about it without either being right. The navigation command
is driven for several steps in a row rather than once, since it is the only one
that carries state between calls and a single step would never show a driver
arriving anywhere.

The answers were computed by the reference, not by this model, which is what makes
agreement a cross-check rather than a restatement. Recording them needs the
reference driver; replaying them does not, so this runs anywhere.

Usage:
    python3 conformance/corpus.py [--corpus PATH]
    python3 conformance/corpus.py --record --driver PATH
"""

import base64
import json
import random
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from st010 import chip as st010

USAGE = "usage: corpus.py [--corpus PATH] [--record --driver PATH] [--cases N]"

DEFAULT_CORPUS = Path(__file__).resolve().parent / "corpus.json"

DEFAULT_DRIVER = Path(__file__).resolve().parent / "ref" / "driver"

CASES = 240

DRIVER_TIMEOUT = 300

REPORT_LIMIT = 5

MEMORY_BYTES = st010.MEMORY_BYTES

NAVIGATION_STEPS = 6

COMMANDS = (
    st010.COMPASS,
    st010.SORT,
    st010.SCALE,
    st010.DISTANCE,
    st010.NAVIGATE,
    st010.MULTIPLY,
    st010.RASTER,
    st010.ROTATE,
)

UNKNOWN = 0x7F
"""A command number the chip does not have, which must still clear its registers."""


class Usage(Exception):
    pass


class Options:
    def __init__(self, corpus=None, driver=None, record=False, cases=CASES):
        self.corpus = corpus
        self.driver = driver
        self.record = record
        self.cases = cases


def command_for(seed):
    """Which command a seed exercises, with the unrecognised one in the rotation."""
    return (*COMMANDS, UNKNOWN)[seed % (len(COMMANDS) + 1)]


def _word(value):
    return [value & 0xFF, (value >> 8) & 0xFF]


def _dword(value):
    return [(value >> shift) & 0xFF for shift in (0, 8, 16, 24)]


def _at(memory, address, values):
    memory[address : address + len(values)] = bytes(values)


def arguments_for(seed):
    """The memory a command starts from, shaped to the ranges that command takes."""
    source = random.Random(seed)
    command = command_for(seed)
    memory = bytearray(MEMORY_BYTES)

    if command in (st010.COMPASS, st010.DISTANCE, st010.MULTIPLY):
        _at(memory, 0x0000, _word(source.randrange(-0x8000, 0x8000)))
        _at(memory, 0x0002, _word(source.randrange(-0x8000, 0x8000)))
    elif command in (st010.SCALE, st010.ROTATE):
        _at(memory, 0x0000, _word(source.randrange(-0x8000, 0x8000)))
        _at(memory, 0x0002, _word(source.randrange(-0x8000, 0x8000)))
        _at(memory, 0x0004, _word(source.randrange(-0x8000, 0x8000)))
    elif command == st010.RASTER:
        _at(memory, 0x0000, _word(source.randrange(-0x8000, 0x8000)))
    elif command == st010.SORT:
        _sorting(memory, source)
    elif command == st010.NAVIGATE:
        _steering(memory, source)
    return memory


def _sorting(memory, source):
    """A field of drivers, some of them already in order and some not."""
    _at(memory, 0x0024, _word(source.randrange(0, st010.DRIVERS + 1)))
    for at in range(st010.DRIVERS):
        _at(memory, 0x0040 + at * 2, _word(source.randrange(0, 0x10000)))
        _at(memory, 0x0080 + at * 2, _word(source.randrange(0, 0x10000)))


def _steering(memory, source):
    """A driver somewhere on a track, pointed somewhere, going at some speed."""
    _at(memory, 0x00C0, _word(source.randrange(-0x4000, 0x4000)))
    _at(memory, 0x00C2, _word(source.randrange(-0x4000, 0x4000)))
    _at(memory, 0x00C4, _dword(source.randrange(0, 0x20000000)))
    _at(memory, 0x00C8, _dword(source.randrange(0, 0x20000000)))
    _at(memory, 0x00CC, _word(source.randrange(-0x8000, 0x8000)))
    _at(memory, 0x00D4, _word(source.randrange(0, 0x1000)))
    _at(memory, 0x00D6, _word(source.randrange(0, 0x100)))
    _at(memory, 0x00D8, _word(source.randrange(0x100, 0x4000)))
    _at(memory, 0x00DA, _word(source.choice((0x0000, 0xFFFF))))
    _at(memory, 0x00DC, _word(source.randrange(0, 0x10)))
    _at(memory, 0x00DE, _word(source.randrange(-0x4000, 0x4000)))
    _at(memory, 0x00E0, _word(source.randrange(-0x8000, 0x8000)))


def runs_for(seed):
    """How many times a case starts its command, which is more than once for one of them."""
    return NAVIGATION_STEPS if command_for(seed) == st010.NAVIGATE else 1


def replay(seed):
    """The case through the model, answered as the whole memory afterwards."""
    part = st010.St010(memory=arguments_for(seed))
    part.write(0x0000, 0x00)
    for _ in range(runs_for(seed)):
        part.write(st010.ENABLE_BIT | st010.COMMAND_REGISTER, command_for(seed))
        part.write(st010.ENABLE_BIT | st010.START_REGISTER, st010.START)
    return bytes(part.memory)


def script_for(seed):
    """The same case as lines the reference driver understands."""
    lines = ["reset", "w 0 0"]
    for at, value in enumerate(arguments_for(seed)):
        if value:
            lines.append(f"poke {at} {value}")
    for _ in range(runs_for(seed)):
        lines.append(f"w {st010.ENABLE_BIT | st010.COMMAND_REGISTER} {command_for(seed)}")
        lines.append(f"w {st010.ENABLE_BIT | st010.START_REGISTER} {st010.START}")
    lines.append("dump")
    return "\n".join(lines) + "\n"


def ask(seeds, driver):
    """The cases through the reference, whose answers are the ones recorded."""
    script = "".join(script_for(seed) for seed in seeds)
    done = subprocess.run(
        [str(driver)],
        input=script,
        capture_output=True,
        text=True,
        check=False,
        timeout=DRIVER_TIMEOUT,
    )
    if done.returncode:
        raise Usage(f"the reference driver failed: {done.stderr.strip()}")
    dumps = [line for line in done.stdout.split() if line]
    if len(dumps) != len(seeds):
        raise Usage(f"the reference answered {len(dumps)} of {len(seeds)} cases")
    return [bytes.fromhex(dump) for dump in dumps]


def encode(memory):
    """A memory as one string, because a byte per line is a file nobody can read."""
    return base64.b64encode(bytes(memory)).decode("ascii")


def expected_of(case):
    """The memory the reference left behind for one case."""
    return bytes(base64.b64decode(case["expected"]))


def load(path=None):
    """The corpus, from where it was asked for or from the one that ships."""
    with Path(path or DEFAULT_CORPUS).open() as handle:
        return json.load(handle)


def record(driver, wanted):
    """Ask the reference for the memory each case leaves behind."""
    seeds = list(range(wanted))
    answers = ask(seeds, driver)
    return {
        "comment": (
            "Cases generated from seeds and answered by the chip's own reference. "
            "Each answer is the whole shared memory after the command ran."
        ),
        "reference": "snes9x seta010.cpp, through conformance/ref",
        "cases": [
            {"seed": seed, "expected": encode(answer)}
            for seed, answer in zip(seeds, answers, strict=True)
        ],
    }


def disagreement(expected, actual):
    """The first byte the two memories differ on, or nothing."""
    for at in range(max(len(expected), len(actual))):
        theirs = expected[at] if at < len(expected) else None
        ours = actual[at] if at < len(actual) else None
        if theirs != ours:
            return at, theirs, ours
    return None


def options(argv):
    chosen = Options()
    rest = list(argv)
    while rest:
        item = rest.pop(0)
        if item == "--record":
            chosen.record = True
            continue
        if item not in ("--corpus", "--driver", "--cases"):
            raise Usage(USAGE)
        if not rest:
            raise Usage(USAGE)
        value = rest.pop(0)
        if item == "--corpus":
            chosen.corpus = value
        elif item == "--driver":
            chosen.driver = value
        else:
            chosen.cases = int(value)
    return chosen


def run(argv):
    chosen = options(argv)
    if chosen.record:
        found = record(chosen.driver or DEFAULT_DRIVER, chosen.cases)
        Path(chosen.corpus or DEFAULT_CORPUS).write_text(json.dumps(found, indent=2) + "\n")
        print(f"recorded {len(found['cases'])} cases")
        return 0

    corpus = load(chosen.corpus)
    failed = 0
    checked = 0
    for case in corpus["cases"]:
        expected = expected_of(case)
        checked += len(expected)
        found = disagreement(expected, replay(case["seed"]))
        if found is None:
            continue
        failed += 1
        at, theirs, ours = found
        if failed <= REPORT_LIMIT:
            print(f"FAIL seed {case['seed']} at {at:#06x}: reference {theirs}, model {ours}")

    print(f"{len(corpus['cases'])} cases, {checked:,} bytes compared, {failed} disagreed")
    return 1 if failed else 0


def main(argv):
    try:
        return run(argv)
    except Usage as error:
        print(error)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
