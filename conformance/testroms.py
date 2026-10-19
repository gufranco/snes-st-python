from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from snesst import ST018, Chip, firmware

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable, Sequence

    type Measure = Callable[[firmware.Identity, bytes], dict[str, Any]]

HERE = Path(__file__).resolve().parent

RECORD = HERE / "testroms.json"

MEASURED = HERE / "testroms_measured.json"

RECORDING = "--record"

USAGE = "usage: python3 -m conformance.testroms [--record] FOLDER"

ARM = "arm60"

RACING = "st010"

POINT = (0x00, 0x01, 0x00, 0x02)

WINDOW = 0x680000

COMMAND = WINDOW + 0x20

START = WINDOW + 0x21

ANSWER = WINDOW + 0x10

FIRST_COMMAND = 0x01

START_BIT = 0x80

ENABLE = 0x000000

MAILBOX_IN = 0x3802

MAILBOX_OUT = 0x3800

MAILBOX_STATUS = 0x3804

WAITING = 0x01

UNKNOWN_COMMAND = 0x00

SETTLE = 20000

STEP = 100

PATIENCE = 400

Measures = dict[str, dict[str, Any]]


def first_command(part: Any) -> dict[str, int]:
    part.write(ENABLE, 0x00)
    for at, value in enumerate(POINT):
        part.write(WINDOW + at, value)
    part.write(COMMAND, FIRST_COMMAND)
    part.write(START, START_BIT)
    spent = part.finish()
    answer = part.read(ANSWER) | part.read(ANSWER + 1) << 8
    return {"command1Instructions": spent, "command1Answer": answer}


def signal(identity: firmware.Identity, image: bytes) -> dict[str, Any]:
    part = Chip(identity.part, image=image, identity=identity)
    found: dict[str, Any] = {"part": identity.part, "waitsAt": part.core.registers.pc}
    if identity.part == RACING:
        found.update(first_command(part))
    return found


def arm(identity: firmware.Identity, image: bytes) -> dict[str, Any]:
    part = ST018(image=image)
    part.step(SETTLE)
    part.write(MAILBOX_IN, UNKNOWN_COMMAND)
    answer = None
    for _ in range(PATIENCE):
        part.step(STEP)
        if part.read(MAILBOX_STATUS) & WAITING:
            answer = part.read(MAILBOX_OUT)
            break
    return {"part": identity.part, "unknownCommandAnswer": answer}


def measure(identity: firmware.Identity, image: bytes) -> dict[str, Any]:
    return arm(identity, image) if identity.processor == ARM else signal(identity, image)


def recorded(path: Path = RECORD) -> list[dict[str, Any]]:
    held: list[dict[str, Any]] = json.loads(path.read_text())["cartridges"]
    return held


def measured(path: Path = MEASURED) -> Measures:
    held: Measures = json.loads(path.read_text())
    return held


def examine(
    folder: Path,
    entries: Sequence[dict[str, Any]],
    catalogue: dict[str, Any] | None,
    measure: Measure,
) -> Measures:
    by_digest = {str(entry["sha256"]): str(entry["id"]) for entry in entries}
    found: Measures = {}
    for path in sorted(folder.iterdir()) if folder.is_dir() else ():
        raw = path.read_bytes() if path.is_file() else b""
        name = by_digest.get(hashlib.sha256(raw).hexdigest())
        if name is None:
            continue
        identity = firmware.identify(raw, catalogue)
        ran = measure(identity, firmware.read(path, identity))
        found[name] = {**ran, "storedLowByteFirst": identity.low_byte_first}
    return found


def compared(found: Measures, held: Measures) -> list[str]:
    lines = []
    for name, ran in sorted(found.items()):
        expected = held.get(name)
        ran_here = {key: value for key, value in ran.items() if key != "storedLowByteFirst"}
        kept = {key: value for key, value in (expected or {}).items() if key in ran_here}
        if kept == ran_here:
            lines.append(f"  {name}: agrees with the record")
        else:
            lines.append(f"  {name}: ran {ran_here}, the record holds {kept}")
    return lines


def main(
    argv: Sequence[str],
    say: Callable[[str], object] = print,
    measure: Measure = measure,
    entries: Sequence[dict[str, Any]] | None = None,
    catalogue: dict[str, Any] | None = None,
    measured_path: Path = MEASURED,
) -> int:
    told = [one for one in argv if one != RECORDING]
    if not told:
        say(USAGE)
        return 2
    named = recorded() if entries is None else entries
    found = examine(Path(told[0]), named, catalogue, measure)
    if not found:
        say(f"  0 of {len(named)} recorded images were found, so nothing was run")
        return 2
    if RECORDING in argv:
        measured_path.write_text(json.dumps(found, indent=2, sort_keys=True) + "\n")
        return 0
    lines = compared(found, measured(measured_path))
    for line in lines:
        say(line)
    return 0 if all(line.endswith("agrees with the record") for line in lines) else 1


def entry(say: Callable[[str], object] = print) -> int:
    raise SystemExit(main(sys.argv[1:], say=say))


if __name__ == "__main__":
    entry()
