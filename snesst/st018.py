"""The third part Seta made, which shares a prefix with the other two and no silicon.

The ST010 and ST011 are NEC uPD96050 digital signal processors and are in
`chip.py`, which is written in their terms: shared memory, a command register, a
start byte the console sets and the microcode clears. None of that exists here.
The ST018 is a 32 bit ARM on the cartridge's own crystal, and what the console
has of it is three addresses and one byte at a time.

So this is a separate class rather than a third model inside `Chip`. Putting two
unrelated processors behind one interface would mean an interface that describes
neither, and the decision is the same one this package already made when it
declined to model the ST018 at all until the ARM core existed.

Both halves of the interface were read off artifacts rather than taken from an
implementation. The console half is in the cartridge's own code, which reaches
`$3800`, `$3802` and `$3804` and nothing else in the window. The part's half is
in the firmware: at `0x000300` it waits for bit 0 of `0x40000020` to clear and
stores a byte at `0x40000000`, and at `0x00031C` it waits for bit 3 to set and
reads one from `0x40000010`. Each side writes one port and reads one port, so
the pairing is forced rather than chosen. `OPEN-QUESTIONS.md` carries the reading
in full, including the one bit nothing establishes.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from snesst import firmware
from snesst.errors import NoFirmware, UnknownPort, WrongShape

ROOT = Path(__file__).resolve().parent.parent

PROCESSOR = ROOT / "arm6-python"
"""The core, which is a member of its own and is not reimplemented here."""

MODEL = "arm60"
"""Which ARM6 the core is asked for.

Every source calls this part ARMv3 and none names the core, so this is the one
part of the arrangement that rests on an inference rather than on a reading.
`OPEN-QUESTIONS.md` carries what settling it would take, which is decapping.
"""

PART = "st018"

PROGRAM_BYTES = 0x20000
DATA_BYTES = 0x8000
IMAGE_BYTES = PROGRAM_BYTES + DATA_BYTES
"""128 KiB of program then 32 KiB of data, which the image's own length gives and
the firmware confirms: the program region ends in zero padding from `0x01FFE0`,
and at `0x0010E4` the firmware loads the literal `0xA0000000`, adds an index and
reads a byte out of it.
"""

PROGRAM_ROM = 0x00000000
PORTS = 0x40000000
DATA_ROM = 0xA0000000
WORK_RAM = 0xE0000000

WORK_RAM_BYTES = 0x4000
"""Sixteen kilobytes, which is what the stack pointer implies: the firmware loads
it with `0xE0004000`, and a stack that starts at the top of its region starts one
past the end.
"""

REGION_MASK = 0xE0000000

TO_PART_PORT = 0x10
FROM_PART_PORT = 0x00
STATUS_PORT = 0x20
PORT_MASK = 0x3F
"""Where the part reaches its side of the mailbox, as offsets from `0x40000000`.

`0x20` answers the status on a read. On a write it is the first byte of
something the firmware loads three bytes into and then commits at `0x2C`, once,
at boot. This package records those writes and models nothing behind them,
because what they are is a reading of somebody else's rather than anything
either artifact states.
"""

FROM_PART = 0x3800
TO_PART = 0x3802
STATUS = 0x3804
CONSOLE_PORTS = (FROM_PART, TO_PART, STATUS)
"""The three the cartridge reaches. It touches no other address in the window, so
what the rest of it does is a question neither artifact answers and this package
refuses rather than invents.
"""

WAITING = 0x01
SENT = 0x08
READY = 0x80
"""The three status bits either side is seen to rely on.

Bit 0 the console polls before every read of `$3800`, and the part polls before
every store to `0x40000000`. Bit 3 the part polls before every read of
`0x40000010`. Bit 7 the console polls after the reset pulse, and nothing in
either artifact sets it: see `up`.
"""

GUARD = 0x10
PART_GUARD = 0x20
"""What each side abandons a transfer on, and neither side ever sets.

The cartridge gives up when bit 4 of `$3804` is set and the firmware gives up
when bit 5 of `0x40000020` is set. Both are read by code that has never seen
them set, so what they mean is established nowhere. They are named here so a
reader can find them and never set, because setting them would be a claim.
"""


def _processor(where: Path | str | None = None) -> Any:
    """The ARM core, looked for before it is imported.

    Looked for rather than imported inside a try, because the failure this has to
    diagnose is an empty directory left by a clone without --recurse-submodules,
    and an ImportError does not say that. A directory with no package in it is
    the thing to name.
    """
    root = Path(where or PROCESSOR)
    if not (root / "arm6" / "__init__.py").is_file():
        return None
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    import arm6

    return arm6


class Stores:
    """The four regions the firmware reaches, and the mailbox among them.

    A region is chosen on the top three bits, which is how the firmware's own
    addresses separate: the program at zero, the ports at `0x4`, the data ROM at
    `0xA` and the work RAM at `0xE`. Anything else answers zero and swallows a
    write, because the part has nothing there and a model that raised would stop
    a run the silicon would not.
    """

    __slots__ = ("data", "part", "program", "ram")

    def __init__(self, part: ST018, program: bytes, data: bytes) -> None:
        self.part = part
        self.program = program
        self.data = data
        self.ram = bytearray(WORK_RAM_BYTES)

    def read_byte(self, address: int) -> int:
        region = address & REGION_MASK
        if region == PROGRAM_ROM:
            return self.program[address % PROGRAM_BYTES]
        if region == DATA_ROM:
            return self.data[(address - DATA_ROM) % DATA_BYTES]
        if region == WORK_RAM:
            return self.ram[(address - WORK_RAM) % WORK_RAM_BYTES]
        if region == PORTS:
            return self.part.port(address & PORT_MASK)
        return 0

    def write_byte(self, address: int, value: int) -> None:
        region = address & REGION_MASK
        if region == WORK_RAM:
            self.ram[(address - WORK_RAM) % WORK_RAM_BYTES] = value & 0xFF
            return
        if region == PORTS:
            self.part.drive(address & PORT_MASK, value & 0xFF)

    def read_word(self, address: int) -> int:
        at = address & ~3
        return int.from_bytes(bytes(self.read_byte(at + i) for i in range(4)), "little")

    def write_word(self, address: int, value: int) -> None:
        at = address & ~3
        for i in range(4):
            self.write_byte(at + i, (value >> (8 * i)) & 0xFF)


class ST018:
    """The part, driven by running the program inside it.

    An image can be handed in rather than found, which is what a caller with the
    bytes already has and what lets this be driven by a program nobody owns on a
    machine where no real firmware is present.
    """

    __slots__ = (
        "core",
        "identity",
        "incoming",
        "outgoing",
        "part",
        "sent",
        "steps",
        "stores",
        "timer",
        "up",
        "waiting",
    )

    def __init__(
        self,
        image: bytes | None = None,
        images: Iterator[tuple[Any, Path | str]] | None = None,
        fill: int = 0,
        processor: Path | str | None = None,
    ) -> None:
        arm6 = _processor(processor)
        if arm6 is None:
            raise NoFirmware(
                f"the ARM core is not here. {PROCESSOR.name} is a submodule of this"
                " repository and an empty directory is what a clone without"
                " --recurse-submodules leaves"
            )

        self.identity: Any = None
        if image is None:
            image, self.identity = self._search(images)
        if len(image) != IMAGE_BYTES:
            raise WrongShape(
                f"an ST018 image is {IMAGE_BYTES} bytes, {PROGRAM_BYTES} of program"
                f" and {DATA_BYTES} of data, and this one is {len(image)}"
            )

        self.part = PART
        self.steps = 0
        self.timer = 0
        self.stores = Stores(self, image[:PROGRAM_BYTES], image[PROGRAM_BYTES:])
        self.core = arm6.Cpu(MODEL, self.stores, fill=fill)
        self.reset()

    @staticmethod
    def _search(images: Iterator[tuple[Any, Path | str]] | None) -> tuple[bytes, Any]:
        """The first ST018 image any of the places this package looks holds.

        One path whether the caller named the places or not, so the search a test
        drives is the search a reader gets.
        """
        for identity, where in firmware.search() if images is None else images:
            if identity.part == PART:
                return Path(where).read_bytes(), identity
        raise NoFirmware(
            f"there is no image for {PART} in any of the places this package looks,"
            " so its program cannot be run"
        )

    @property
    def model(self) -> str:
        """The name this part answers to, which every member of the family offers."""
        return PART

    @property
    def processor(self) -> str:
        return MODEL

    def reset(self) -> ST018:
        """Start the part over, which is what the console's pulse on `$3804` does."""
        self.incoming = 0
        self.outgoing = 0
        self.sent = False
        self.waiting = False
        self.up = True
        self.core.reset()
        return self

    def step(self, steps: int = 1) -> ST018:
        for _ in range(steps):
            self.core.step()
            self.steps += 1
        return self

    def port(self, offset: int) -> int:
        """The part's own side, read from inside the program."""
        if offset == TO_PART_PORT:
            if not self.sent:
                return 0
            self.sent = False
            return self.incoming
        if offset == STATUS_PORT:
            return self.status()
        return 0

    def drive(self, offset: int, value: int) -> None:
        """The part's own side, written from inside the program."""
        if offset == FROM_PART_PORT:
            self.outgoing = value
            self.waiting = True
            return
        self.timer = value if offset == STATUS_PORT else self.timer

    def status(self) -> int:
        """What both sides read, each of them for different bits of it.

        Bit 7 is the one nothing establishes. The cartridge waits on it after the
        reset pulse and no instruction in the firmware sets it, so it is the
        interface hardware answering rather than the program, and what this
        package answers there is its own rather than the part's. It is recorded
        as a divergence rather than left to look derived.
        """
        found = 0
        if self.waiting:
            found |= WAITING
        if self.sent:
            found |= SENT
        if self.up:
            found |= READY
        return found

    def read(self, address: int) -> int:
        """One byte, from the console's side of the window."""
        if address == FROM_PART:
            if not self.waiting:
                return 0
            self.waiting = False
            return self.outgoing
        if address == STATUS:
            return self.status()
        raise UnknownPort(_why(address, "read"))

    def write(self, address: int, value: int) -> None:
        """One byte in, or the pulse that starts the part over.

        The cartridge drives `$3804` low, then high, then low again with a full
        countdown between each. What this treats as the reset is the rising edge,
        because a level that is already low cannot be an event.
        """
        if address == TO_PART:
            self.incoming = value & 0xFF
            self.sent = True
            return
        if address == STATUS:
            if value & 1:
                self.reset()
            return
        raise UnknownPort(_why(address, "write"))


def _why(address: int, doing: str) -> str:
    return (
        f"nothing establishes what a {doing} of ${address:04X} does. The cartridge"
        f" reaches {', '.join(f'${one:04X}' for one in CONSOLE_PORTS)} and no other"
        " address in the window, so this package refuses rather than inventing a"
        " register neither artifact describes"
    )
