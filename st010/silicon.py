"""Run the part's own microcode instead of modelling what its commands compute.

The model beside this was derived by working out what each of the eight commands
does and writing that down. That can be checked against a reference and it has
been, but it can never be finished: what a derived model covers is the commands
somebody thought to look at, and the corners nobody characterised are exactly
where a derived model is silently wrong.

This takes the other route. The part is a NEC uPD96050 and a mask ROM, so given
the ROM there is nothing left to derive: run the program and whatever it writes
back into memory is what the part writes back, including the commands and the
argument ranges nobody has ever measured.

What it costs is the ROM, which belongs to whoever made the part and is therefore
never carried here. This backend exists only when its owner supplies a copy. The
model is what the package can do without, and holding the model to this is what
turns its fidelity from a claim into a measurement.

Where the image is looked for belongs to the processor package, and is worth
naming here because this package is meant to be checked out inside another one:
`UPD7725_FIRMWARE_DIR` names any number of directories, then the project this
package sits inside is searched, then the package itself. A project carrying
this as a submodule keeps its images in its own tree and tells neither side.

The arrangement is not the one the model describes, and the difference is worth
stating because it is invisible from the console. The model has the part ignore
everything until a write arrives with the high address bit clear, and treats that
write as a switch that does nothing else. On the part there is no switch: the
window with that bit clear is the processor's own data port, the window with it
set is the processor's scratch memory, and the scratch memory is the four
kilobytes the console shares.

That single fact explains the write the model cannot account for. The microcode
raises its attention bit on its first instruction and then waits for the console
to answer, so a console that never touches the port never gets past the second
instruction. The model's switch is that answer, and modelling it as a flag works
only because the model does not run the program that is waiting.

There is no bit saying an answer is ready. What says it is the microcode clearing
the start byte it was started with, so that is what is waited on.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PROCESSOR = ROOT / "nec-upd7725-python"

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
"""Where each part's microcode sits while it waits to be given something to do.

The ST010 reads the word holding the command and the start byte, tests its top
bit, and goes round again while that bit is clear: the top bit of that word is
the start bit, so the loop is the part being ready rather than the part being
stuck. The ST011 waits in one word instead, because it is a different program.

Measured on each part rather than assumed, and per part rather than shared,
because the only thing the two have in common is the processor underneath.
"""

HANDSHAKE_READS = 2
"""How many byte reads the console gives back to get the part past its first word.

The microcode raises its attention bit immediately and waits for the console to
take a word off the data port. A word is two byte reads, and until both have
happened it never reaches the loop above: a part spoken to without them answers
nothing and looks broken.
"""

BOOT_STEPS = 200000
"""Instructions to run before the part is spoken to.

The image sets up its own tables before it begins watching for a command, and
speaking to it during that returns answers that are plausible and wrong rather
than obviously broken. This is generous on purpose: the cost of waiting too long
is time, and the cost of not waiting long enough is a wrong answer that looks
right.
"""

SETTLE_LIMIT = 4000000
"""How long to let a command run before giving up on it.

Larger than the equivalent for a ported part, because a command here is a whole
navigation routine rather than a handful of multiplies, and because the console
cannot interrupt one: it starts the command and reads memory afterwards.
"""

WHY_NOT_PROCESSOR = (
    "the processor is not here: this backend runs the part's own microcode on"
    " the NEC uPD96050, which sits beside this package as a submodule, so it has"
    " to be checked out with git submodule update --init --recursive"
)

WHY_NOT_FIRMWARE = (
    "no firmware image was found: this backend runs the part's own microcode, and"
    " that microcode belongs to whoever made the part, so a copy you already own"
    " goes in the firmware directory of this project or of the project this one"
    " sits inside, or in any directory named by UPD7725_FIRMWARE_DIR"
)


class NoFirmware(Exception):
    pass


class NeverFinished(Exception):
    pass


def _processor():
    """The processor package, or nothing when the submodule is absent."""
    if str(PROCESSOR) not in sys.path:
        sys.path.insert(0, str(PROCESSOR))
    try:
        from upd7725 import firmware, models, ports
    except ImportError:
        return None
    return firmware, models, ports


def available(held=None):
    """Every part there is an image for, by the name the part is known as.

    `held` is what was found on disk, passed in so the decision that follows can
    be exercised on a machine holding no image at all.
    """
    if held is None:
        found = _processor()
        if found is None:
            return {}
        held = {identity.part: (identity, path) for identity, path in found[0].search()}
    return dict(held)


def why_not(held=None):
    """Why this backend cannot run, or nothing when it can."""
    if _processor() is None:
        return WHY_NOT_PROCESSOR
    if not available(held):
        return WHY_NOT_FIRMWARE
    return None


class Silicon:
    """A part driven by running the program inside it.

    The interface is the model's, so a caller swaps backends without knowing
    which it holds: the same `read` and `write` over the same addresses, the same
    two registers past the end of memory, and the same rule that the part ignores
    both until it has seen the write that wakes it.

    An image can be supplied rather than found on disk. That is what a caller
    with the bytes already in hand wants, and it is also what lets this class be
    driven in a test by a program nobody owns, on a machine where no real
    microcode is present. `images` replaces the search instead of the image, for
    a caller that knows where the files are but wants them read the usual way.
    """

    def __init__(
        self,
        part="st010",
        memory=None,
        fill=0,
        patience=SETTLE_LIMIT,
        boot=BOOT_STEPS,
        image=None,
        identity=None,
        images=None,
    ):
        found = _processor()
        if found is None:
            raise NoFirmware(WHY_NOT_PROCESSOR)

        firmware, models, ports = found

        if image is None:
            catalogue = available(images)
            if part not in catalogue:
                raise NoFirmware(
                    f"there is no firmware image for {part}, so its microcode cannot"
                    f" be run. {WHY_NOT_FIRMWARE}"
                )
            identity, path = catalogue[part]
            image = path.read_bytes()
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
        self.chip = models.describe(identity.processor).build(fill=fill)
        firmware.load(self.chip, image, identity)
        self.console = ports.Console(self.chip)
        self.handshake(boot)

        self.reset()
        if memory is not None:
            for at, value in enumerate(bytes(memory)[:MEMORY_BYTES]):
                self.chip.stores.write_byte(at, value)

    def handshake(self, boot=None):
        """Do what a console does at power-on, which the part waits for.

        One instruction is enough to raise its attention bit; the console then
        takes a word off the data port, and only then does the microcode go on to
        the loop that watches for a command. Nothing about the part says this is
        needed, and a part that has not had it is silent rather than broken.
        """
        self.chip.step()
        for _ in range(HANDSHAKE_READS):
            self.console.read(self._ports.DATA)
        self.chip.run(self.boot if boot is None else boot)
        return self

    def reset(self):
        """Forget that the console ever woke the part, without reloading it."""
        self.enabled = False
        return self

    @property
    def memory(self):
        """The shared memory as bytes, which is the processor's own scratch."""
        return bytes(self.chip.stores.read_byte(at) for at in range(MEMORY_BYTES))

    @property
    def command(self):
        return self.chip.stores.read_byte(COMMAND_REGISTER)

    @property
    def execute(self):
        return self.chip.stores.read_byte(START_REGISTER)

    def read(self, address):
        """One byte, out of the shared memory or out of the port beside it.

        The two register addresses are ordinary memory to the microcode, so they
        are read the way everything else is. What makes them registers is that
        the program watches them, not that the decode treats them apart.
        """
        if not address & ENABLE_BIT:
            return self.console.read(self._ports.STATUS if address & 1 else self._ports.DATA)
        return self.chip.stores.read_byte(address & (MEMORY_BYTES - 1))

    def write(self, address, value):
        """One byte in, which may also be the byte that starts a command.

        The write the model treats as a switch reaches the port here, which is
        what it reaches on the part. It still records that the console has spoken,
        because the rest of the decode depends on that, but what makes the
        microcode move on is the port access rather than the flag.

        Past the decode there is no modelling left. The microcode reads what was
        written into its scratch and answers by writing back into it.
        """
        value &= 0xFF
        if not address & ENABLE_BIT:
            self.enabled = True
            if not address & 1:
                self.console.write(self._ports.DATA, value)
            return

        self.chip.stores.write_byte(address & (MEMORY_BYTES - 1), value)

        if self.enabled and self.execute & START:
            self._run()

    def _run(self):
        """Let the microcode work until it says it is done with the command.

        Done is the start byte going clear. The microcode clears it itself once
        it has written its answers back, and that is the only signal the console
        ever gets, so it is the only one worth waiting on.
        """
        for _ in range(self.patience):
            if not self.execute & START:
                return
            self.chip.step()
        raise NeverFinished(
            f"{self.part} did not finish command {self.command:#04x} within"
            f" {self.patience} instructions"
        )

    def __repr__(self):
        return f"<{self.part} on silicon, {self.processor}>"
