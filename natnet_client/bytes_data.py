import struct
from dataclasses import dataclass
from typing import Any


class BytesData:
    @classmethod
    def unpack(cls, data: bytes) -> Any:
        raise NotImplementedError("Subclasses must implement the unpack method")


@dataclass(frozen=True)
class Position(BytesData):
    x: float
    y: float
    z: float

    @classmethod
    def unpack(cls, data: bytes):
        return cls(*(struct.unpack("<fff", data)))


@dataclass(frozen=True)
class Quaternion(BytesData):
    x: float
    y: float
    z: float
    w: float

    @classmethod
    def unpack(cls, data: bytes):
        return cls(*(struct.unpack("<ffff", data)))
