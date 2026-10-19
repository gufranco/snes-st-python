from __future__ import annotations

import hashlib
import platform
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, override

ROOT = Path(__file__).resolve().parent.parent


def reachable(root: Path = ROOT, path: list[str] | None = None) -> bool:
    where = sys.path if path is None else path
    if str(root) in where:
        return False
    where.insert(0, str(root))
    return True


reachable()

from snesst import chip, environment, firmware, models, st018  # noqa: E402
from snesst.version import VERSION  # noqa: E402


class Restartable(Protocol):
    def reset(self) -> object: ...


if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable, Iterable, Sequence

    Images = dict[str, tuple[Any, Path]]
    Build = Callable[[str, Images], Restartable]

EXCHANGES = ROOT / "conformance"

OLDEST_PYTHON = (3, 12)

PROCESSOR_NAME = "nec-upd7725-96050-python"

HALTING_PROCESSOR = "upd96050"


class Finding:
    def __init__(self, name: str, ok: bool, detail: str, advice: str | None = None) -> None:
        self.name = name
        self.ok = ok
        self.detail = detail
        self.advice = advice

    @property
    def line(self) -> str:
        return f"  {'ok  ' if self.ok else '   !'}  {self.name}: {self.detail}"

    @property
    def report(self) -> str:
        if self.ok or not self.advice:
            return self.line
        return f"{self.line}\n         {self.advice}"

    @override
    def __repr__(self) -> str:
        return f"<Finding {self.name} {'ok' if self.ok else 'not ok'}>"


def _python() -> Finding:
    where = sys.version_info
    return Finding(
        "python",
        where[:2] >= OLDEST_PYTHON,
        f"{platform.python_version()} on {platform.system()} {platform.machine()}",
        f"this package needs {OLDEST_PYTHON[0]}.{OLDEST_PYTHON[1]} or newer",
    )


def _package() -> Finding:
    return Finding("package", True, f"snesst {VERSION}")


def _processor() -> Finding:
    found = chip.PROCESSOR.is_dir() and any(chip.PROCESSOR.iterdir())
    return Finding(
        "processor",
        found,
        f"{chip.PROCESSOR.name} {'is checked out' if found else 'is missing'}",
        "run git submodule update --init --recursive",
    )


def _arm() -> Finding:
    found = st018.PROCESSOR.is_dir() and any(st018.PROCESSOR.iterdir())
    return Finding(
        "arm",
        found,
        f"{st018.PROCESSOR.name} {'is checked out' if found else 'is missing'}",
        "run git submodule update --init --recursive",
    )


def build_part(part: str, images: Images) -> Any:
    if part == st018.PART:
        return st018.ST018(images=iter(images.values()))
    return chip.Chip(part, images=images)


def _part(name: str, images: Images, build: Build) -> Finding:
    wanted = name
    if wanted not in images:
        return Finding(
            name,
            False,
            f"no image for {wanted}",
            f"put a copy you own in {ROOT.name}/firmware, in the firmware directory"
            " of the project this one sits inside, or anywhere SNES_ST_FIRMWARE_DIR"
            " or UPD7725_FIRMWARE_DIR names",
        )
    try:
        part = build(name, images)
        part.reset()
    except Exception as trouble:
        return Finding(
            name,
            False,
            f"{type(trouble).__name__}: {trouble}",
            "this is the part failing to start rather than a missing file; the line"
            " above is what it said",
        )
    identity = getattr(part, "identity", None)
    running = identity.part if identity is not None else wanted
    digest = digest_of(wanted, images)
    return Finding(name, True, f"runs and resets the {running} image{digest}")


def digest_of(wanted: str, images: Images | None) -> str:
    held = images.get(wanted) if isinstance(images, dict) else None
    if not isinstance(held, tuple) or len(held) != 2:
        return ""
    identity, where = held
    try:
        raw = Path(where).read_bytes()
    except OSError as trouble:
        return f", but its file could not be read: {trouble}"
    if not getattr(identity, "low_byte_first", False):
        return f", sha256 {hashlib.sha256(raw).hexdigest()}"
    run = firmware.reordered(raw, identity.program_words)
    return (
        f", sha256 {hashlib.sha256(run).hexdigest()},"
        " read from a file that stores each word low byte first"
    )


def check_waits(build: Build | None = None, images: Images | None = None) -> Finding:
    made = build_part if build is None else build
    held = chip.available() if images is None else images
    reached = []
    for name in sorted(models.MODELS):
        if name not in held:
            continue
        if getattr(held[name][0], "processor", HALTING_PROCESSOR) != HALTING_PROCESSOR:
            continue
        try:
            part = made(name, held)
            core = getattr(part, "core")  # noqa: B009
            reached.append(f"{name} waits at {core.registers.pc}")
        except Exception as trouble:
            return Finding("waits", False, f"{type(trouble).__name__}: {trouble}")
    if not reached:
        return Finding("waits", True, "no image is here, so nothing was run")
    return Finding("waits", True, ", ".join(reached))


def _default_beneath() -> list[Finding]:
    reach_processor()
    from upd7725 import doctor as underneath

    found: list[Finding] = list(underneath.examine())
    return found


def reach_processor(path: list[str] | None = None) -> list[str]:
    path = sys.path if path is None else path
    where = str(chip.PROCESSOR)
    if where not in path:
        path.insert(0, where)
    return path


def _beneath(beneath: Callable[[], Iterable[Finding]]) -> list[Finding]:
    try:
        found = list(beneath())
    except Exception as trouble:
        return [
            Finding(
                PROCESSOR_NAME,
                False,
                f"{type(trouble).__name__}: {trouble}",
                "the project underneath could not be examined. It is either not"
                " checked out or it is older than this package expects, and both"
                " are fixed the same way: run"
                " git submodule update --init --recursive",
            )
        ]
    return [
        Finding(f"{PROCESSOR_NAME} / {one.name}", one.ok, one.detail, one.advice) for one in found
    ]


def examine(
    images: Images | None = None,
    build: Build = build_part,
    beneath: Callable[[], Iterable[Finding]] = _default_beneath,
) -> list[Finding]:
    held = chip.available() if images is None else images
    found = [_python(), _package(), _processor(), _arm()]
    found.extend(_part(name, held, build) for name in sorted(models.MODELS))
    found.append(check_waits())
    found.extend(_beneath(beneath))
    return found


def report(found: Sequence[Finding]) -> list[str]:
    unwell = [one for one in found if not one.ok]
    lines = [f"snesst {VERSION} on {platform.python_version()}, {platform.system()}", ""]
    lines.append("  the machine")
    lines.extend(environment.lines(ROOT))
    lines.append("")
    lines.append("  this package")
    lines.extend(one.report for one in found)
    lines.append("")
    if unwell:
        lines.append(f"  {len(unwell)} of {len(found)} checks did not pass")
    else:
        lines.append(f"  {len(found)} checks, nothing to report")
    return lines


def main(
    argv: Sequence[str] = (),
    examine: Callable[..., Sequence[Finding]] = examine,
    say: Callable[[str], object] = print,
) -> int:
    found = examine()
    for line in report(found):
        say(line)
    return 1 if any(not one.ok for one in found) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
