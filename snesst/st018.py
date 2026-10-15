from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from snesst import firmware
from snesst.errors import NoFirmware, UnknownPort, WrongShape

ROOT = Path(__file__).resolve().parent.parent

PROCESSOR = ROOT / "arm6-python"

MODEL = "arm60"

PART = "st018"

PROGRAM_BYTES = 0x20000
DATA_BYTES = 0x8000
IMAGE_BYTES = PROGRAM_BYTES + DATA_BYTES

PROGRAM_ROM = 0x00000000
PORTS = 0x40000000
DATA_ROM = 0xA0000000
WORK_RAM = 0xE0000000

WORK_RAM_BYTES = 0x4000

REGION_MASK = 0xE0000000

TO_PART_PORT = 0x10
FROM_PART_PORT = 0x00
STATUS_PORT = 0x20
PORT_MASK = 0x3F

FROM_PART = 0x3800
TO_PART = 0x3802
STATUS = 0x3804
CONSOLE_PORTS = (FROM_PART, TO_PART, STATUS)

WAITING = 0x01
SENT = 0x08
READY = 0x80

GUARD = 0x10
PART_GUARD = 0x20


def _processor(where: Path | str | None = None) -> Any:
    root = Path(where or PROCESSOR)
    if not (root / "arm6" / "__init__.py").is_file():
        return None
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    import arm6

    return arm6


class Stores:
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
        for identity, where in firmware.search() if images is None else images:
            if identity.part == PART:
                return Path(where).read_bytes(), identity
        raise NoFirmware(
            f"there is no image for {PART} in any of the places this package looks,"
            " so its program cannot be run"
        )

    @property
    def model(self) -> str:
        return PART

    @property
    def processor(self) -> str:
        return MODEL

    def reset(self) -> ST018:
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
        if offset == TO_PART_PORT:
            if not self.sent:
                return 0
            self.sent = False
            return self.incoming
        if offset == STATUS_PORT:
            return self.status()
        return 0

    def drive(self, offset: int, value: int) -> None:
        if offset == FROM_PART_PORT:
            self.outgoing = value
            self.waiting = True
            return
        self.timer = value if offset == STATUS_PORT else self.timer

    def status(self) -> int:
        found = 0
        if self.waiting:
            found |= WAITING
        if self.sent:
            found |= SENT
        if self.up:
            found |= READY
        return found

    def read(self, address: int) -> int:
        if address == FROM_PART:
            if not self.waiting:
                return 0
            self.waiting = False
            return self.outgoing
        if address == STATUS:
            return self.status()
        raise UnknownPort(_why(address, "read"))

    def write(self, address: int, value: int) -> None:
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
