"""What the ST010 computes, as functions of what it was given.

Eight things, and only one of them carries state. The rest take numbers out of
the chip's memory and put numbers back, which is what makes them provable rather
than merely exercised: each is a function, and a function can be settled over the
range it accepts.

The arithmetic is sixteen bit with a doubling in several places, and the
doubling is not decoration. A product is answered shifted up by one, a scale is
answered shifted up by one, and the distance is a straight line fit rather than a
square root: the longer side times a bit over nine tenths plus the shorter times
a bit under a fifth, which is the standard cheap approximation and is out by a
few percent on a diagonal.

The compass is the interesting one. It folds a point into a single octant pair by
reflecting it, halves it until both coordinates fit the lookup, reads the angle
out of a thirty two by thirty two square, and then puts the reflection back by
combining the quadrant with the angle and inverting the top bit. A point straight
down is given a quadrant it would not otherwise have, after the angle has already
been worked out from a different one.
"""

from .tables import ARCTAN_SIDE, RASTER_LINES, RASTER_SCALE, arctangent, cosine, sine

LOOKUP_LIMIT = ARCTAN_SIDE - 1

QUADRANT = 0x4000

HALF_TURN = -0x8000

LONG_SIDE = 0x3D78

SHORT_SIDE = 0x1976

HALF = 0x8000

POSITION_MASK = 0x1FFFFFFF

ARRIVED = 0x0008

TURNING = 0x8000

NEAR_ACROSS = 0x0080

NEAR_DOWN = 0x0008

STEADY = 0x0100

APPROACH = 0x0280

RETREAT = 0xFD80


def signed16(value):
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


def signed32(value):
    value &= 0xFFFFFFFF
    return value - 0x100000000 if value & 0x80000000 else value


class Bearing:
    """A point folded into one octant pair, and which fold it took to get there."""

    def __init__(self, across, down, quadrant, theta):
        self.across = across
        self.down = down
        self.quadrant = quadrant
        self.theta = theta


class Raster:
    """One screen of mode seven scale, in the three forms the chip writes."""

    def __init__(self, across, down, mirrored):
        self.across = across
        self.down = down
        self.mirrored = mirrored


class Navigation:
    """Where a driver is, where it is going, and how fast it is getting there."""

    def __init__(self, max_x, max_y, x, y, theta, radius, compass, flags):
        self.max_x = max_x
        self.max_y = max_y
        self.x = x
        self.y = y
        self.theta = theta
        self.turned = 0
        self.away_x = 0
        self.away_y = 0
        self.radius = radius
        self.compass = compass
        self.flags = flags


def compass(across, down):
    """Which way a point lies, by folding it into the one octant pair looked up."""
    folded_across, folded_down, quadrant = _fold(across, down)
    folded_across, folded_down = _shrink(folded_across, folded_down)

    theta = arctangent(folded_across, folded_down) << 8
    theta = signed16((theta | quadrant) ^ HALF)

    if across == 0 and down < 0:
        quadrant = QUADRANT

    return Bearing(folded_across, folded_down, signed16(quadrant), theta)


def _fold(across, down):
    """The point reflected into the pair of octants the lookup covers."""
    if across <= 0 and down < 0:
        return -across, -down, HALF_TURN
    if across < 0:
        return down, -across, -QUADRANT
    if down < 0:
        return -down, across, QUADRANT
    return across, down, 0x0000


def _shrink(across, down):
    """Halved until both coordinates fit the lookup, which loses the smaller one.

    Each halving stops at one rather than at zero, so a point that is far along
    one axis and barely off the other keeps a coordinate of one there rather than
    falling onto the axis.
    """
    while across > LOOKUP_LIMIT or down > LOOKUP_LIMIT:
        if across > 1:
            across >>= 1
        if down > 1:
            down >>= 1
    return across, down


def scale(multiplier, across, down):
    """A point moved further out or nearer in, answered doubled."""
    return signed32(across * multiplier << 1), signed32(down * multiplier << 1)


def multiply(multiplicand, multiplier):
    """A product, answered doubled, which is the only thing this command does."""
    return signed32(multiplicand * multiplier << 1)


def rotate(theta, across, down):
    """A point turned about the origin by an angle."""
    return (
        signed16(((down * sine(theta)) >> 15) + ((across * cosine(theta)) >> 15)),
        signed16(((down * cosine(theta)) >> 15) - ((across * sine(theta)) >> 15)),
    )


def distance(across, down):
    """How far away a point is, by a straight line fit rather than a square root.

    The longer side is taken at a bit over nine tenths and the shorter at a bit
    under a fifth. On an axis that is within a percent; on a diagonal it is out
    by about eight, which is what this approximation costs and why nothing here
    calls it a length.
    """
    across = abs(across)
    down = abs(down)
    longer, shorter = (across, down) if across >= down else (down, across)
    product = ((longer * LONG_SIDE << 1) + (shorter * SHORT_SIDE << 1)) << 1
    return signed16((product + HALF) >> 16)


def sort_drivers(positions, places, drivers):
    """The race order, sorted downwards, carrying each driver with its place.

    A bubble sort, in place, and the chip's own: the pass count comes down by one
    each time round whether or not anything moved, so a field already in order
    still costs one pass and a reversed one costs as many passes as it has
    drivers.
    """
    if positions <= 1:
        return

    while True:
        sorted_yet = True
        for at in range(positions - 1):
            if places[at] < places[at + 1]:
                places[at], places[at + 1] = places[at + 1], places[at]
                drivers[at], drivers[at + 1] = drivers[at + 1], drivers[at]
                sorted_yet = False
        positions -= 1
        if sorted_yet:
            return


def raster(theta):
    """The mode seven scale for a whole screen, at one angle.

    Three of the four things the chip writes are here. The fourth is the same as
    one of these, written somewhere else, and belongs to the chip rather than to
    the arithmetic.
    """
    across = []
    down = []
    mirrored = []
    for line in range(RASTER_LINES):
        across.append(signed16((RASTER_SCALE[line] * cosine(theta)) >> 15))
        value = signed16((RASTER_SCALE[line] * sine(theta)) >> 15)
        down.append(value)
        mirrored.append((~value if value else value) & 0xFFFF)
    return Raster(across, down, mirrored)


def navigate(state, increment, max_radius, new_max_x, new_max_y):
    """One step of a driver towards its next target, and the target after that.

    The turn is limited: a bearing that differs by less than a degree or so is
    taken as it is, and anything wider moves the heading by a fixed amount in the
    right direction rather than by the difference. Speed follows the same
    reasoning from the other side, rising towards a limit while the driver is
    pointed the right way and falling by the size of the error when it is not.
    """
    state.away_x = signed16(state.max_x - (state.x >> 16))
    state.away_y = signed16(state.max_y - (state.y >> 16))

    state.turned = signed16(compass(state.away_x, state.away_y).theta - state.theta)
    if state.turned & 0xFF00:
        state.theta = signed16(state.theta + (RETREAT if state.turned & 0x8000 else APPROACH))

    _pace(state, increment, max_radius)
    _advance(state)
    _arrive(state, new_max_x, new_max_y)


def _pace(state, increment, max_radius):
    """How fast, which rises towards a limit and falls by how far off course it is."""
    error = (-state.turned if state.turned < 0 else state.turned) >> 4
    if error < STEADY:
        state.radius = min(state.radius + increment, max_radius)
        return
    reached = state.radius - error
    state.radius = max(reached, 0)


def _advance(state):
    """The step itself, which wraps inside the range the chip carries a position in."""
    state.x = (state.x - (((sine(state.theta) >> 5) * (state.radius >> 8)) << 1)) & POSITION_MASK
    state.y = (state.y - (((cosine(state.theta) >> 5) * (state.radius >> 8)) << 1)) & POSITION_MASK


def _arrive(state, new_max_x, new_max_y):
    """Whether the driver is close enough to take the next target.

    Close enough is measured in a box rather than a circle, and the box is turned
    on its side depending on which way the track is turning here. The next
    target's own sign carries that for the target after it.
    """
    if state.compass & TURNING:
        near_across, near_down = NEAR_DOWN, NEAR_ACROSS
    else:
        near_across, near_down = NEAR_ACROSS, NEAR_DOWN

    if abs(state.away_x) >= near_across or abs(state.away_y) >= near_down:
        return

    state.max_x = new_max_x
    state.max_y = new_max_y & 0x0FFF
    state.compass = -1 if new_max_y & TURNING else 0
    state.flags |= ARRIVED
