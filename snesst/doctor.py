"""Look at this machine and say what is actually here, so a report can be believed.

Most of what goes wrong with this package is not a defect in it. It is a missing
submodule, an image that is not the one the part expects, or a Python that is too
old, and every one of those looks identical from the outside: it does not work.
Somebody reporting that has no way to tell which, and somebody reading the report
has no way to ask without a round trip.

So this looks, and prints what it found in a form that can be pasted into an
issue as it stands.

Two rules shape it, and they are the whole point.

Nothing is hidden. A check that fails says what it saw, and a check that itself
throws is caught and reported as what it threw, named by its type. Swallowing
either would leave a report that says everything is fine on a machine where
something is not, which is worse than no report.

Nothing is inferred. Every line is something that was looked at on this machine
just now: the version that is installed, the digest of the file that is present,
whether the part actually started. A doctor that reports what ought to be true is
a doctor nobody can use.
"""

from __future__ import annotations

import hashlib
import platform
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, override

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from snesst import chip, models  # noqa: E402
from snesst.version import VERSION  # noqa: E402

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable, Iterable, Sequence

    Images = dict[str, tuple[Any, Path]]
    Build = Callable[[str, Images], object]

EXCHANGES = ROOT / "conformance"

OLDEST_PYTHON = (3, 12)

PROCESSOR_NAME = "nec-upd7725-96050-python"
"""What the project underneath is called, which is what its findings are filed under."""


class Finding:
    """One thing that was looked at, and what was there."""

    def __init__(self, name: str, ok: bool, detail: str, advice: str | None = None) -> None:
        self.name = name
        self.ok = ok
        self.detail = detail
        self.advice = advice

    @property
    def line(self) -> str:
        """The one-line form, which is what a reader scans."""
        return f"  {'ok  ' if self.ok else '   !'}  {self.name}: {self.detail}"

    @property
    def report(self) -> str:
        """The same, with what to do about it when there is something to do."""
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
    """The distribution, labelled so it cannot be mistaken for the part.

    The package is named for the family and the parts for themselves, which is
    the whole reason this repository stopped being called after one of its two
    chips. Labelling the distribution with a part's name would put that back.
    """
    return Finding("package", True, f"snesst {VERSION}")


def _processor() -> Finding:
    found = chip.PROCESSOR.is_dir() and any(chip.PROCESSOR.iterdir())
    return Finding(
        "processor",
        found,
        f"{chip.PROCESSOR.name} {'is checked out' if found else 'is missing'}",
        "run git submodule update --init --recursive",
    )


def _default_build(part: str, images: Images) -> chip.Chip:
    return chip.Chip(part, images=images)


def _part(name: str, images: Images, build: Build) -> Finding:
    """Whether that part is here and starts, saying exactly what stopped it."""
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
    digest = _digest_of(wanted, images)
    return Finding(name, True, f"runs the {running} image{digest}")


def _digest_of(wanted: str, images: Images | None) -> str:
    """The digest of the file that is actually here, which is what settles a report.

    Two people with the same part and different answers almost always have
    different files, and this is the line that shows it in one glance rather than
    after a round trip asking them to go and hash it.
    """
    held = images.get(wanted) if isinstance(images, dict) else None
    if not isinstance(held, tuple) or len(held) != 2:
        return ""
    try:
        raw = Path(held[1]).read_bytes()
    except OSError as trouble:
        return f", but its file could not be read: {trouble}"
    return f", sha256 {hashlib.sha256(raw).hexdigest()}"


def _waits(build: Build | None = None, images: Images | None = None) -> Finding:
    """Where each part's shipped microcode stops, which is the thing measured here.

    Not a claim from any document. It is the address the program actually reaches
    on a copy a reader supplied, so a report that names a different one is a
    report about a different image.

    `images` is passed in for the same reason it is elsewhere in this file: a
    check that reads what happens to be on the machine running it is a check
    whose result depends on the machine, and a test of the failure path passed
    here and reported success on a runner with no image at all.
    """
    made = _default_build if build is None else build
    held = chip.available() if images is None else images
    reached = []
    for name in sorted(models.MODELS):
        if name not in held:
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
    """The doctor of the project this one is built on, asked in its own terms.

    Recursive by construction: whatever that project examines, including anything
    it is built on in turn, comes back with it. A package can be entirely well
    while the thing underneath it is missing, stale, or holding a different file,
    and a doctor that looked only at its own project would report a clean machine
    in exactly that case.
    """
    _reach()
    from upd7725 import doctor as underneath

    found: list[Finding] = list(underneath.examine())
    return found


def _reach(path: list[str] | None = None) -> list[str]:
    """Put the project underneath where it can be imported from, once.

    It sits beside this package rather than inside it, so nothing has taught the
    interpreter where it is. Adding it twice would be harmless and would still be
    wrong: a path list that grows every time somebody asks for a report is a
    small leak, and this is the file that exists to notice small things.
    """
    path = sys.path if path is None else path
    where = str(chip.PROCESSOR)
    if where not in path:
        path.insert(0, where)
    return path


def _beneath(beneath: Callable[[], Iterable[Finding]]) -> list[Finding]:
    """Everything the project underneath found, filed under its name."""
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
    build: Build = _default_build,
    beneath: Callable[[], Iterable[Finding]] = _default_beneath,
) -> list[Finding]:
    """Everything worth looking at on this machine, in the order a reader wants it.

    This package first, then what it is built on. A reader scanning the output
    sees their own project's state before the state of the thing underneath it,
    and both are here because either can be the reason nothing works.
    """
    held = chip.available() if images is None else images
    found = [_python(), _package(), _processor()]
    found.extend(_part(name, held, build) for name in sorted(models.MODELS))
    found.append(_waits())
    found.extend(_beneath(beneath))
    return found


def report(found: Sequence[Finding]) -> list[str]:
    """The lines a person pastes into an issue."""
    unwell = [one for one in found if not one.ok]
    lines = [f"snesst {VERSION} on {platform.python_version()}, {platform.system()}", ""]
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
