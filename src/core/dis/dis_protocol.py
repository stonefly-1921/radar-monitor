"""DIS Protocol - PDU definitions per IEEE 1278.1."""

import struct
from enum import IntEnum
from dataclasses import dataclass, field


# =============================================================================
# PDU Type Constants
# =============================================================================

class PduType(IntEnum):
    """DIS PDU Types (Protocol Version 6)."""
    ENTITY_STATE = 1
    FIRE = 2
    DETONATION = 3
    SIGNAL = 4
    START_RESUME = 10
    STOP_FREEZE = 11


# PDU Family - Entity Management
PDU_FAMILY = 1

# Default Exercise ID
EXERCISE_ID = 0


# =============================================================================
# Utility Functions
# =============================================================================

def _pack_byte(value: int) -> bytes:
    """Pack a single unsigned byte."""
    return struct.pack("B", value & 0xFF)


def _unpack_byte(data: bytes, offset: int) -> tuple[int, int]:
    """Unpack a single unsigned byte."""
    return struct.unpack_from("B", data, offset)[0], offset + 1


# =============================================================================
# Basic Data Types
# =============================================================================

@dataclass
class EntityId:
    """Entity Identifier (6 bytes).
    
    DIS Entity ID consists of site ID, application ID, and entity ID.
    Each field is a 16-bit unsigned integer (big-endian).
    
    DIS uses big-endian (network byte order) for all multi-byte integers.
    """
    site_id: int
    application_id: int
    entity_id: int

    def __bytes__(self) -> bytes:
        return struct.pack(">HHH", self.site_id, self.application_id, self.entity_id)

    @classmethod
    def from_bytes(cls, data: bytes) -> "EntityId":
        site_id, application_id, entity_id = struct.unpack_from(">HHH", data, 0)
        return cls(site_id=site_id, application_id=application_id, entity_id=entity_id)

    def __len__(self) -> int:
        return 6  # 3 x uint16

    @classmethod
    def size(cls) -> int:
        return 6


@dataclass
class EntityType:
    """Entity Type (8 bytes).
    
    Defines the kind, domain, country, and category of an entity.
    - kind, domain, category, subcategory, specific, extra: 8-bit unsigned
    - country: 16-bit unsigned
    """
    kind: int
    domain: int
    country: int
    category: int
    subcategory: int
    specific: int
    extra: int

    def __bytes__(self) -> bytes:
        return struct.pack(">BBHBBBB",
                          self.kind, self.domain, self.country,
                          self.category, self.subcategory,
                          self.specific, self.extra)

    @classmethod
    def from_bytes(cls, data: bytes) -> "EntityType":
        values = struct.unpack_from(">BBHBBBB", data, 0)
        return cls(
            kind=values[0], domain=values[1], country=values[2],
            category=values[3], subcategory=values[4],
            specific=values[5], extra=values[6]
        )

    def __len__(self) -> int:
        return 8

    @classmethod
    def size(cls) -> int:
        return 8


@dataclass
class Vector3Float:
    """Three-component floating-point vector (12 bytes).
    
    IEEE 32-bit floating point values in big-endian format.
    Used for orientation, angular velocity, etc.
    """
    x: float
    y: float
    z: float

    def __bytes__(self) -> bytes:
        return struct.pack(">fff", self.x, self.y, self.z)

    @classmethod
    def from_bytes(cls, data: bytes) -> "Vector3Float":
        x, y, z = struct.unpack_from(">fff", data, 0)
        return cls(x=x, y=y, z=z)

    def __len__(self) -> int:
        return 12

    @classmethod
    def size(cls) -> int:
        return 12

    @classmethod
    def zero(cls) -> "Vector3Float":
        return cls(x=0.0, y=0.0, z=0.0)


@dataclass
class Vector3Double:
    """Three-component double-precision vector (24 bytes).
    
    IEEE 64-bit floating point values in big-endian format.
    Used for world coordinates, linear velocity, etc.
    """
    x: float
    y: float
    z: float

    def __bytes__(self) -> bytes:
        return struct.pack(">ddd", self.x, self.y, self.z)

    @classmethod
    def from_bytes(cls, data: bytes) -> "Vector3Double":
        x, y, z = struct.unpack_from(">ddd", data, 0)
        return cls(x=x, y=y, z=z)

    def __len__(self) -> int:
        return 24

    @classmethod
    def size(cls) -> int:
        return 24

    @classmethod
    def zero(cls) -> "Vector3Double":
        return cls(x=0.0, y=0.0, z=0.0)


@dataclass
class Orientation:
    """Entity orientation (12 bytes).
    
    Pitch, Yaw, Roll in radians as IEEE 32-bit floats.
    """
    pitch: float
    yaw: float
    roll: float

    def __bytes__(self) -> bytes:
        return struct.pack(">fff", self.pitch, self.yaw, self.roll)

    @classmethod
    def from_bytes(cls, data: bytes) -> "Orientation":
        pitch, yaw, roll = struct.unpack_from(">fff", data, 0)
        return cls(pitch=pitch, yaw=yaw, roll=roll)

    def __len__(self) -> int:
        return 12

    @classmethod
    def size(cls) -> int:
        return 12

    @classmethod
    def identity(cls) -> "Orientation":
        return cls(pitch=0.0, yaw=0.0, roll=0.0)


@dataclass
class DisTimestamp:
    """DIS Timestamp (5 bytes).
    
    48-bit clock in microseconds, split as:
    - 8-bit hours (0-255)
    - 32-bit time in centiseconds (0-4294967295)
    
    DIS 1278.1 uses a 48-bit clock where the upper 8 bits are hours
    and the lower 40 bits represent time in centiseconds.
    """
    hours: int
    time: int  # centiseconds

    def __bytes__(self) -> bytes:
        # Pack as big-endian: 1 byte hours + 4 bytes time
        return struct.pack(">BI", self.hours & 0xFF, self.time & 0xFFFFFFFF)

    @classmethod
    def from_bytes(cls, data: bytes) -> "DisTimestamp":
        hours, time = struct.unpack_from(">BI", data, 0)
        return cls(hours=hours, time=time)

    def __len__(self) -> int:
        return 5

    @classmethod
    def size(cls) -> int:
        return 5

    def to_float(self) -> float:
        """Convert to floating-point seconds since midnight."""
        return self.hours * 3600.0 + self.time * 0.01

    @classmethod
    def from_float(cls, seconds: float) -> "DisTimestamp":
        """Create timestamp from floating-point seconds since midnight."""
        total_centiseconds = int(seconds * 100)
        hours = total_centiseconds // 360000
        time = total_centiseconds % 360000
        return cls(hours=hours, time=time)

    @classmethod
    def now(cls) -> "DisTimestamp":
        """Create timestamp for current time."""
        import datetime
        now = datetime.datetime.now()
        total_seconds = now.hour * 3600 + now.minute * 60 + now.second + now.microsecond / 1_000_000
        return cls.from_float(total_seconds)


# =============================================================================
# PDU Header
# =============================================================================

@dataclass
class PduHeader:
    """PDU Header (11 bytes).
    
    Standard DIS PDU header per IEEE 1278.1:
    - Protocol Version: 1 byte (6 for current standard)
    - Exercise ID: 1 byte
    - PDU Type: 1 byte
    - Family: 1 byte
    - Timestamp: 5 bytes (48-bit clock)
    - Length: 2 bytes (total PDU length)
    """
    protocol_version: int
    exercise_id: int
    pdu_type: PduType
    family: int
    timestamp: DisTimestamp
    length: int

    def __bytes__(self) -> bytes:
        return (
            struct.pack(">BBBB", self.protocol_version, self.exercise_id,
                       int(self.pdu_type), self.family) +
            bytes(self.timestamp) +
            struct.pack(">H", self.length)
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "PduHeader":
        protocol_version, exercise_id, pdu_type, family = struct.unpack_from(">BBBB", data, 0)
        ts_bytes = data[4:9]
        timestamp = DisTimestamp.from_bytes(ts_bytes)
        length, = struct.unpack_from(">H", data, 9)
        return cls(
            protocol_version=protocol_version,
            exercise_id=exercise_id,
            pdu_type=PduType(pdu_type),
            family=family,
            timestamp=timestamp,
            length=length
        )

    def __len__(self) -> int:
        return 11

    @classmethod
    def size(cls) -> int:
        return 11


# =============================================================================
# Location Records
# =============================================================================

class LocationRecordType(IntEnum):
    """Location record type enumeration."""
    WORLD_COORDINATES = 0
    ENTITY_ORIENTATION = 1
    ENTITY_AUXILIARY = 2


@dataclass
class WorldCoordinates:
    """World coordinates record using Vector3Double (24 bytes).
    
    Represents an entity's position in world coordinates (meters).
    """
    coordinates: Vector3Double = field(default_factory=lambda: Vector3Double.zero())

    def __bytes__(self) -> bytes:
        return bytes(self.coordinates)

    @classmethod
    def from_bytes(cls, data: bytes) -> "WorldCoordinates":
        coords = Vector3Double.from_bytes(data)
        return cls(coordinates=coords)

    def __len__(self) -> int:
        return 24

    @classmethod
    def size(cls) -> int:
        return 24