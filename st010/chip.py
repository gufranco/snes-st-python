"""The ST010 as the cartridge talks to it: a memory, and two registers beside it.

There is no port. The chip and the console share a battery-backed memory, the
console writes the arguments into it, writes a command number and a start bit
into two registers just past the end of it, and the chip writes the answers back
into the same memory. Every command has its own fixed addresses for both.

Two details in the register decode look like mistakes and are what the reference
does, so they are here.

The first is that the chip ignores both registers until it has seen a write with
the high address bit clear. That write does nothing else. Until it arrives the
two registers cannot be set at all, and every write lands in memory instead.

The second is in the decode itself. The command register is written under a
condition and the start register under another, and the second condition carries
an else that belongs to it rather than to the pair: a write to the command
register with the chip already listening falls through to the else and lands in
memory as well, so that address holds a copy of the last command. The start
register does not, because its own branch was taken.
"""

from . import maths

MEMORY_BYTES = 0x1000

ENABLE_BIT = 0x80000

COMMAND_REGISTER = 0x20

START_REGISTER = 0x21

START = 0x80

NOT_ENABLED = 0x80

COMPASS = 0x01

SORT = 0x02

SCALE = 0x03

DISTANCE = 0x04

NAVIGATE = 0x05

MULTIPLY = 0x06

RASTER = 0x07

ROTATE = 0x08

RASTER_ACROSS = 0x00F0

RASTER_DOWN = 0x0250

RASTER_MIRRORED = 0x03B0

RASTER_COPY = 0x0510

DRIVERS = 32


class St010:
    """One ST010, holding a command, a start bit, and the memory it works in."""

    def __init__(self, memory=None):
        self.memory = bytearray(memory) if memory is not None else bytearray(MEMORY_BYTES)
        self.reset()

    def reset(self):
        self.enabled = False
        self.command = 0
        self.execute = 0
        return self

    def read(self, address):
        """One byte, which is a register only at two addresses and memory elsewhere."""
        if not address & ENABLE_BIT:
            return NOT_ENABLED
        if address & 0xFFF == COMMAND_REGISTER:
            return self.command
        if address & 0xFFF == START_REGISTER:
            return self.execute
        return self.memory[address & (MEMORY_BYTES - 1)]

    def write(self, address, value):
        """One byte in, which may also be the byte that starts a command."""
        value &= 0xFF
        if not address & ENABLE_BIT:
            self.enabled = True
            return

        if address & 0xFFF == COMMAND_REGISTER and self.enabled:
            self.command = value

        if address & 0xFFF == START_REGISTER and self.enabled:
            self.execute = value
        else:
            self.memory[address & (MEMORY_BYTES - 1)] = value

        if self.execute & START:
            self._run()

    def word(self, at):
        return maths.signed16(self.memory[at] | (self.memory[at + 1] << 8))

    def unsigned(self, at):
        return self.memory[at] | (self.memory[at + 1] << 8)

    def dword(self, at):
        return maths.signed32(
            self.memory[at]
            | (self.memory[at + 1] << 8)
            | (self.memory[at + 2] << 16)
            | (self.memory[at + 3] << 24)
        )

    def put_word(self, at, value):
        self.memory[at] = value & 0xFF
        self.memory[at + 1] = (value >> 8) & 0xFF

    def put_dword(self, at, value):
        self.put_word(at, value & 0xFFFF)
        self.put_word(at + 2, (value >> 16) & 0xFFFF)

    def _run(self):
        handler = self._handlers().get(self.command)
        if handler is not None:
            handler()
        self.command = 0
        self.execute = 0

    def _handlers(self):
        return {
            COMPASS: self._compass,
            SORT: self._sort,
            SCALE: self._scale,
            DISTANCE: self._distance,
            NAVIGATE: self._navigate,
            MULTIPLY: self._multiply,
            RASTER: self._raster,
            ROTATE: self._rotate,
        }

    def _compass(self):
        """Which way a point lies, and a copy of where it was before folding."""
        self.memory[0x0006] = self.memory[0x0002]
        self.memory[0x0007] = self.memory[0x0003]

        found = maths.compass(self.word(0x0000), self.word(0x0002))
        self.put_word(0x0000, found.across)
        self.put_word(0x0002, found.down)
        self.put_word(0x0004, found.quadrant)
        self.put_word(0x0010, found.theta)

    def _sort(self):
        """The race order, with the places sorted in place and the drivers with them."""
        positions = self.unsigned(0x0024)
        places = [self.unsigned(0x0040 + at * 2) for at in range(positions)]
        drivers = [self.unsigned(0x0080 + at * 2) for at in range(DRIVERS)]

        maths.sort_drivers(positions, places, drivers)

        for at, place in enumerate(places):
            self.put_word(0x0040 + at * 2, place)
        for at, driver in enumerate(drivers):
            self.put_word(0x0080 + at * 2, driver)

    def _scale(self):
        across, down = maths.scale(self.word(0x0004), self.word(0x0000), self.word(0x0002))
        self.put_dword(0x0010, across)
        self.put_dword(0x0014, down)

    def _distance(self):
        self.put_word(0x0010, maths.distance(self.word(0x0000), self.word(0x0002)))

    def _multiply(self):
        self.put_dword(0x0010, maths.multiply(self.word(0x0000), self.word(0x0002)))

    def _rotate(self):
        across, down = maths.rotate(self.word(0x0004), self.word(0x0000), self.word(0x0002))
        self.put_word(0x0010, across)
        self.put_word(0x0012, down)

    def _raster(self):
        """A screen of mode seven scale, in four places, and the angle shifted after.

        The fourth copy is the same numbers as the first, written somewhere else,
        and the angle in memory is shifted down a byte once the screen is built
        so that the caller can hand it straight back as a table index.
        """
        found = maths.raster(self.word(0x0000))
        for line in range(maths.RASTER_LINES):
            at = line * 2
            self.put_word(RASTER_ACROSS + at, found.across[line])
            self.put_word(RASTER_COPY + at, found.across[line])
            self.put_word(RASTER_DOWN + at, found.down[line])
            self.put_word(RASTER_MIRRORED + at, found.mirrored[line])

        self.memory[0x00] = self.memory[0x01]
        self.memory[0x01] = 0x00

    def _navigate(self):
        """One step of a driver towards its target, which is the only command with state."""
        state = maths.Navigation(
            max_x=self.word(0x00C0),
            max_y=self.word(0x00C2),
            x=self.dword(0x00C4),
            y=self.dword(0x00C8),
            theta=self.word(0x00CC),
            radius=self.unsigned(0x00D4),
            compass=self.word(0x00DA),
            flags=self.word(0x00DC),
        )

        maths.navigate(
            state,
            increment=self.unsigned(0x00D6),
            max_radius=self.unsigned(0x00D8),
            new_max_x=self.word(0x00DE),
            new_max_y=self.word(0x00E0),
        )

        self.put_word(0x00C0, state.max_x)
        self.put_word(0x00C2, state.max_y)
        self.put_dword(0x00C4, state.x)
        self.put_dword(0x00C8, state.y)
        self.put_word(0x00CC, state.theta)
        self.put_word(0x00CE, state.turned)
        self.put_word(0x00D0, state.away_x)
        self.put_word(0x00D2, state.away_y)
        self.put_word(0x00D4, state.radius)
        self.put_word(0x00DA, state.compass)
        self.put_word(0x00DC, state.flags)

    def __repr__(self):
        return f"<ST010 command {self.command:#04x} enabled {self.enabled}>"
