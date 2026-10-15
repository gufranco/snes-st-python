import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, override

from snesst import firmware
from snesst.errors import NeverFinished, NoFirmware

ROOT = Path(__file__).resolve().parent.parent

PROCESSOR = ROOT / "nec-upd7725-96050-python"

MEMORY_BYTES = 0x1000

ENABLE_BIT = 0x80000

COMMAND_REGISTER = 0x20

START_REGISTER = 0x21

START = 0x80

NOT_ENABLED = 0x80

COMMAND_LOOP = {
    "st010": (3, 4, 5),
    "st011": (2,),
}

HANDSHAKE_READS = 2

BOOT_STEPS = 200000

SETTLE_LIMIT = 4000000

WHY_NOT_PROCESSOR = (
    "the processor is not here: this backend runs the part's own microcode on"
    " the NEC uPD96050, which sits beside this package as a submodule, so it has"
    " to be checked out with git submodule update --init --recursive"
)

WHY_NOT_FIRMWARE = (
    "no firmware image was found: this backend runs the part's own microcode, and"
    " that microcode belongs to whoever made the part, so a copy you already own"
    " goes in the firmware directory of this project or of the project this one"
    " sits inside, or in any directory named by SNES_ST_FIRMWARE_DIR"
)


def _processor() -> Any:
    if str(PROCESSOR) not in sys.path:
        sys.path.append(str(PROCESSOR))
    try:
        from upd7725 import models, ports
    except ImportError:
        return None
    return models, ports


def available(held: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if held is None:
        found = _processor()
        if found is None:
            return {}
        held = {identity.part: (identity, path) for identity, path in firmware.search()}
    return dict(held)


def why_not(held: Mapping[str, Any] | None = None) -> str | None:
    if _processor() is None:
        return WHY_NOT_PROCESSOR
    if not available(held):
        return WHY_NOT_FIRMWARE
    return None


class Chip:
    __slots__ = (
        "_ports",
        "boot",
        "console",
        "core",
        "enabled",
        "identity",
        "model",
        "part",
        "patience",
        "processor",
    )

    def __init__(
        self,
        part: str = "st010",
        memory: bytearray | None = None,
        fill: int = 0,
        patience: int = SETTLE_LIMIT,
        boot: int = BOOT_STEPS,
        image: bytes | None = None,
        identity: Any = None,
        images: Any = None,
    ) -> None:
        found = _processor()
        if found is None:
            raise NoFirmware(WHY_NOT_PROCESSOR)

        models, ports = found

        if image is None:
            catalogue = available(images)
            if part not in catalogue:
                raise NoFirmware(
                    f"there is no firmware image for {part}, so its microcode cannot"
                    f" be run. {WHY_NOT_FIRMWARE}"
                )
            identity, where = catalogue[part]
            image = Path(where).read_bytes()
        elif identity is None:
            raise NoFirmware(
                "an image was supplied without saying what it is, and the processor"
                " has to be told how much of it is program and how much is table"
            )

        self.part = part
        self.model = part
        self.processor = identity.processor
        self.identity = identity
        self.patience = patience
        self.boot = boot

        self._ports = ports
        self.core = models.lookup(identity.processor).build(fill=fill)
        firmware.load(self.core, image, identity)
        self.core.reset()
        self.console = ports.Host(self.core)
        self.handshake(boot)

        self.reset()
        if memory is not None:
            for at, value in enumerate(bytes(memory)[:MEMORY_BYTES]):
                self.core.stores.write_byte(at, value)

    def handshake(self, boot: int | None = None) -> "Chip":
        self.core.step()
        for _ in range(HANDSHAKE_READS):
            self.console.read(self._ports.DATA)
        self.step(self.boot if boot is None else boot)
        return self

    def step(self, steps: int) -> None:
        for _ in range(steps):
            self.core.step()

    def reset(self) -> "Chip":
        self.enabled = False
        return self

    @property
    def memory(self) -> bytes:
        return bytes(self.core.stores.read_byte(at) for at in range(MEMORY_BYTES))

    @property
    def command(self) -> int:
        return int(self.core.stores.read_byte(COMMAND_REGISTER))

    @property
    def execute(self) -> int:
        return int(self.core.stores.read_byte(START_REGISTER))

    def read(self, address: int) -> int:
        if not address & ENABLE_BIT:
            found = self.console.read(self._ports.STATUS if address & 1 else self._ports.DATA)
            return int(found)
        return int(self.core.stores.read_byte(address & (MEMORY_BYTES - 1)))

    def write(self, address: int, value: int) -> None:
        value &= 0xFF
        if not address & ENABLE_BIT:
            self.enabled = True
            if not address & 1:
                self.console.write(self._ports.DATA, value)
            return

        self.core.stores.write_byte(address & (MEMORY_BYTES - 1), value)

        if self.enabled and self.execute & START:
            self._run()

    def _run(self) -> None:
        for _ in range(self.patience):
            if not self.execute & START:
                return
            self.core.step()
        raise NeverFinished(
            f"{self.part} did not finish command {self.command:#04x} within"
            f" {self.patience} instructions"
        )

    @override
    def __repr__(self) -> str:
        return f"<Chip {self.part} on {self.processor}>"
