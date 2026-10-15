from __future__ import annotations


class UnknownModelError(Exception): ...


class NoFirmware(Exception): ...


class NeverFinished(Exception): ...


class Unrecognised(Exception): ...


class Corrupt(Exception): ...


class UnknownPort(Exception):
    __slots__ = ()


class WrongShape(Exception): ...
