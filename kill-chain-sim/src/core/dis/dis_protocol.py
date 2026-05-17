# DIS Protocol - IEEE 1278.1 PDU Definitions
# Based on IEEE Std 1278.1-1995

import struct
from dataclasses import dataclass
from typing import Optional

# =============================================================================
# PDU Type Constants
# =============================================================================
PDU_TYPE_ENTITY_STATE = 1
PDU_TYPE_FIRE = 2
PDU_TYPE_DETONATION = 3
PDU_TYPE_SIGNAL = 4
PDU_TYPE_START_RESUME = 10
PDU_TYPE_STOP_FREEZE = 11

EXERCISE_ID_DEFAULT = 1

# =============================================================================
# Struct Formats (DIS uses big-endian/network byte order)
# =============================================================================
# Entity ID: site_id (2 bytes) + application_id (2 bytes) + entity_id (2 bytes)
ENTITY_ID_FORMAT = ">HHH"  # 6 bytes total
ENTITY_ID_SIZE = 6

# Entity Type: kind(1) + domain(1) + country(2) + category(1) + subcategory(1) + specific(1) + extra(1)
ENTITY_TYPE_FORMAT = ">BBHBBBB"  # 8 bytes total
ENTITY_TYPE_SIZE = 8

# Vector3Float: x(4) + y(4) + z(4)
VECTOR3_FLOAT_FORMAT = ">fff"  # 12 bytes
VECTOR3_FLOAT_SIZE = 12

# Vector3Double: x(8) + y(8) + z(8)
VECTOR3_DOUBLE_FORMAT = ">ddd"  # 24 bytes
VECTOR3_DOUBLE_SIZE = 24

# Orientation: pitch(4) + yaw(4) + roll(4)
ORIENTATION_FORMAT = ">fff"  # 12 bytes
ORIENTATION_SIZE = 12

# DIS Timestamp: hours(1) + time(4) — time is centiseconds since hour
DIS_TIMESTAMP_FORMAT = ">BI"  # 5 bytes
DIS_TIMESTAMP_SIZE = 5

# PDU Header: version(1) + exercise_id(1) + pdu_type(1) + family(1) + timestamp(5) + length(2) + padding(2)
PDU_HEADER_FORMAT = ">BBBBIHH"  # 14 bytes total (includes 2-byte padding after length)
PDU_HEADER_SIZE = 14


# =============================================================================
# Data Classes
# =============================================================================
@dataclass
class EntityId:
    """Entity ID (6 bytes): site, application, entity identifiers."""
    site_id: int          # uint16
    application_id: int   # uint16
    entity_id: int        # uint16

    def encode(self) -> bytes:
        return struct.pack(ENTITY_ID_FORMAT, self.site_id, self.application_id, self.entity_id)

    @classmethod
    def decode(cls, data: bytes) -> 'EntityId':
        site_id, application_id, entity_id = struct.unpack(ENTITY_ID_FORMAT, data[:ENTITY_ID_SIZE])
        return cls(site_id=site_id, application_id=application_id, entity_id=entity_id)

    def __str__(self):
        return f"{self.site_id}:{self.application_id}:{self.entity_id}"

    def __eq__(self, other):
        if not isinstance(other, EntityId):
            return False
        return (self.site_id == other.site_id and
                self.application_id == other.application_id and
                self.entity_id == other.entity_id)

    def __hash__(self):
        return hash((self.site_id, self.application_id, self.entity_id))


@dataclass
class EntityType:
    """Entity Type (8 bytes): kind, domain, country, category, subcategory, specific, extra."""
    kind: int          # uint8
    domain: int        # uint8
    country: int       # uint16
    category: int      # uint8
    subcategory: int   # uint8
    specific: int      # uint8
    extra: int         # uint8

    def encode(self) -> bytes:
        return struct.pack(ENTITY_TYPE_FORMAT,
                          self.kind, self.domain, self.country,
                          self.category, self.subcategory, self.specific, self.extra)

    @classmethod
    def decode(cls, data: bytes) -> 'EntityType':
        kind, domain, country, category, subcategory, specific, extra = \
            struct.unpack(ENTITY_TYPE_FORMAT, data[:ENTITY_TYPE_SIZE])
        return cls(kind=kind, domain=domain, country=country,
                   category=category, subcategory=subcategory,
                   specific=specific, extra=extra)

    def __str__(self):
        return f"{self.kind}:{self.domain}:{self.country}:{self.category}:{self.subcategory}:{self.specific}:{self.extra}"


@dataclass
class Vector3Float:
    """3D vector with float components (12 bytes)."""
    x: float
    y: float
    z: float

    def encode(self) -> bytes:
        return struct.pack(VECTOR3_FLOAT_FORMAT, self.x, self.y, self.z)

    @classmethod
    def decode(cls, data: bytes) -> 'Vector3Float':
        x, y, z = struct.unpack(VECTOR3_FLOAT_FORMAT, data[:VECTOR3_FLOAT_SIZE])
        return cls(x=x, y=y, z=z)


@dataclass
class Vector3Double:
    """3D vector with double components (24 bytes)."""
    x: float
    y: float
    z: float

    def encode(self) -> bytes:
        return struct.pack(VECTOR3_DOUBLE_FORMAT, self.x, self.y, self.z)

    @classmethod
    def decode(cls, data: bytes) -> 'Vector3Double':
        x, y, z = struct.unpack(VECTOR3_DOUBLE_FORMAT, data[:VECTOR3_DOUBLE_SIZE])
        return cls(x=x, y=y, z=z)


@dataclass
class Orientation:
    """Orientation (12 bytes): pitch, yaw, roll in radians."""
    pitch: float  # rotation around Y-axis
    yaw: float    # rotation around Z-axis
    roll: float   # rotation around X-axis

    def encode(self) -> bytes:
        return struct.pack(ORIENTATION_FORMAT, self.pitch, self.yaw, self.roll)

    @classmethod
    def decode(cls, data: bytes) -> 'Orientation':
        pitch, yaw, roll = struct.unpack(ORIENTATION_FORMAT, data[:ORIENTATION_SIZE])
        return cls(pitch=pitch, yaw=yaw, roll=roll)


@dataclass
class DisTimestamp:
    """DIS Timestamp (5 bytes): hours (0-23) + time (centiseconds since hour)."""
    hours: int       # uint8 (0-23)
    time: int        # uint32 (centiseconds since top of hour)

    def encode(self) -> bytes:
        return struct.pack(DIS_TIMESTAMP_FORMAT, self.hours, self.time)

    @classmethod
    def decode(cls, data: bytes) -> 'DisTimestamp':
        hours, time_val = struct.unpack(DIS_TIMESTAMP_FORMAT, data[:DIS_TIMESTAMP_SIZE])
        return cls(hours=hours, time=time_val)

    @classmethod
    def from_seconds(cls, seconds_since_hour: float) -> 'DisTimestamp':
        """Create timestamp from seconds since top of hour."""
        hours = int(seconds_since_hour) // 3600
        hours = hours % 24
        centis = int((seconds_since_hour % 3600) * 100)
        return cls(hours=hours, time=centis)

    def to_seconds(self) -> float:
        """Convert to seconds since top of hour."""
        return self.hours * 3600.0 + self.time * 0.01

    @classmethod
    def now(cls) -> 'DisTimestamp':
        """Create timestamp for current time."""
        import time
        t = time.time()
        hour_sec = (int(t) % 86400)  # seconds since midnight
        cs = int((t % 1.0) * 100)
        return cls(hours=hour_sec // 3600, time=cs)


@dataclass
class PduHeader:
    """PDU Header (14 bytes)."""
    protocol_version: int      # uint8 (should be 6 for DIS 1278.1)
    exercise_id: int           # uint8
    pdu_type: int             # uint8
    family: int               # uint8 (1 = entity_management)
    timestamp: DisTimestamp   # DisTimestamp (5 bytes)
    length: int               # uint16 (total PDU length including header)
    padding: int              # uint16

    # Struct format for header fields (not including timestamp which is handled separately)
    HEADER_FIELDS_FORMAT = ">BBBBHH"  # 12 bytes for fields + 5 bytes timestamp = 17... but we use packed version

    def encode(self) -> bytes:
        ts_bytes = self.timestamp.encode()
        header_bytes = struct.pack(">BBBBHH",
                                   self.protocol_version,
                                   self.exercise_id,
                                   self.pdu_type,
                                   self.family,
                                   self.length,
                                   self.padding)
        return ts_bytes + header_bytes

    @classmethod
    def decode(cls, data: bytes) -> 'PduHeader':
        # First 5 bytes are timestamp
        ts = DisTimestamp.decode(data[:DIS_TIMESTAMP_SIZE])
        # Next 8 bytes are fields
        (protocol_version, exercise_id, pdu_type, family, length, padding) = \
            struct.unpack(">BBBBHH", data[DIS_TIMESTAMP_SIZE:DIS_TIMESTAMP_SIZE + 8])
        return cls(
            protocol_version=protocol_version,
            exercise_id=exercise_id,
            pdu_type=pdu_type,
            family=family,
            timestamp=ts,
            length=length,
            padding=padding
        )

    @property
    def total_size(self) -> int:
        """Total header size including timestamp."""
        return DIS_TIMESTAMP_SIZE + 8  # 5 + 8 = 13... but spec says 14?
        # Actually timestamp (5) + version(1) + exercise(1) + type(1) + family(1) + length(2) + padding(2) = 13
        # But DIS often pads to 14. Let's use 14.


# =============================================================================
# PDU Classes
# =============================================================================

@dataclass
class EntityStatePdu:
    """Entity State PDU (Type 1) — Transmitted by AFSIM to report entity location/state."""
    PDU_TYPE = PDU_TYPE_ENTITY_STATE

    entity_id: EntityId
    entity_type: EntityType
    location: Vector3Double  # world coordinates (meters)
    orientation: Orientation  # radians
    velocity: Vector3Float   # m/s

    # Dead reckoning parameters
    dead_reckoning_type: int = 0  # uint8
    entity_parameters: bytes = b''  # variable length

    # Variable datum records (optional)
    number_of_datum: int = 0
    datum_records: bytes = b''

    def encode(self) -> bytes:
        """Encode Entity State PDU to bytes."""
        result = self.entity_id.encode()
        result += self.entity_type.encode()
        result += self.location.encode()
        result += self.orientation.encode()
        result += self.velocity.encode()
        result += struct.pack(">B", self.dead_reckoning_type)
        # Entity parameters must be exactly 8 bytes (dead reckoning params)
        params = self.entity_parameters[:8].ljust(8, b'\x00')
        result += params
        result += struct.pack(">I", self.number_of_datum)
        result += self.datum_records
        return result

    @classmethod
    def decode(cls, data: bytes) -> 'EntityStatePdu':
        """Decode bytes to EntityStatePdu."""
        offset = 0

        entity_id = EntityId.decode(data[offset:offset + ENTITY_ID_SIZE])
        offset += ENTITY_ID_SIZE

        entity_type = EntityType.decode(data[offset:offset + ENTITY_TYPE_SIZE])
        offset += ENTITY_TYPE_SIZE

        location = Vector3Double.decode(data[offset:offset + VECTOR3_DOUBLE_SIZE])
        offset += VECTOR3_DOUBLE_SIZE

        orientation = Orientation.decode(data[offset:offset + ORIENTATION_SIZE])
        offset += ORIENTATION_SIZE

        velocity = Vector3Float.decode(data[offset:offset + VECTOR3_FLOAT_SIZE])
        offset += VECTOR3_FLOAT_SIZE

        dead_reckoning_type = struct.unpack(">B", data[offset:offset + 1])[0]
        offset += 1

        # Variable params (8 bytes for dead reckoning parameters)
        entity_parameters = data[offset:offset + 8]
        offset += 8

        # Number of variable datum records (4 bytes)
        number_of_datum = struct.unpack(">I", data[offset:offset + 4])[0]
        offset += 4

        # Datum records (variable) - only parse if data is long enough
        datum_records = b''
        if offset + 4 <= len(data):
            datum_records = data[offset:]

        return cls(
            entity_id=entity_id,
            entity_type=entity_type,
            location=location,
            orientation=orientation,
            velocity=velocity,
            dead_reckoning_type=dead_reckoning_type,
            entity_parameters=entity_parameters,
            number_of_datum=number_of_datum,
            datum_records=datum_records
        )


@dataclass
class FirePdu:
    """Fire PDU (Type 2) — Weapon launch event."""
    PDU_TYPE = PDU_TYPE_FIRE

    fire_mission_index: int     # uint32
    emitting_entity_id: EntityId  # who fired
    target_entity_id: EntityId    # what was targeted
    Munition_id: EntityId        # what fired
    warhead: int = 0              # uint16
    fuse: int = 0                 # uint16
    quantity: int = 1             # uint16
    rate: int = 0                 # uint16

    def encode(self) -> bytes:
        result = self.emitting_entity_id.encode()
        result += self.target_entity_id.encode()
        result += self.Munition_id.encode()
        result += struct.pack(">IHHHH", self.fire_mission_index, self.warhead, self.fuse, self.quantity, self.rate)
        return result

    @classmethod
    def decode(cls, data: bytes) -> 'FirePdu':
        offset = 0
        emitting_entity_id = EntityId.decode(data[offset:offset + ENTITY_ID_SIZE])
        offset += ENTITY_ID_SIZE

        target_entity_id = EntityId.decode(data[offset:offset + ENTITY_ID_SIZE])
        offset += ENTITY_ID_SIZE

        Munition_id = EntityId.decode(data[offset:offset + ENTITY_ID_SIZE])
        offset += ENTITY_ID_SIZE

        # fire_mission_index(4) + warhead(2) + fuse(2) + quantity(2) + rate(2) = 12 bytes
        fire_mission_index, warhead, fuse, quantity, rate = struct.unpack(">IHHHH", data[offset:offset + 12])

        return cls(
            fire_mission_index=fire_mission_index,
            emitting_entity_id=emitting_entity_id,
            target_entity_id=target_entity_id,
            Munition_id=Munition_id,
            warhead=warhead,
            fuse=fuse,
            quantity=quantity,
            rate=rate
        )


@dataclass
class DetonationPdu:
    """Detonation PDU (Type 3) — Impact/detonation event."""
    PDU_TYPE = PDU_TYPE_DETONATION

    issuing_entity_id: EntityId
    target_entity_id: EntityId
    Munition_id: EntityId
    event_id: EntityId
    location: Vector3Double
    detonation_result: int  # 0=other, 1=detonation, 2=hit, 3=miss, 4=none

    warhead: int = 0
    fuse: int = 0

    def encode(self) -> bytes:
        result = self.issuing_entity_id.encode()
        result += self.target_entity_id.encode()
        result += self.Munition_id.encode()
        result += self.event_id.encode()
        result += self.location.encode()
        result += struct.pack(">B", self.detonation_result)
        result += struct.pack(">HH", self.warhead, self.fuse)
        return result

    @classmethod
    def decode(cls, data: bytes) -> 'DetonationPdu':
        offset = 0
        issuing_entity_id = EntityId.decode(data[offset:offset + ENTITY_ID_SIZE])
        offset += ENTITY_ID_SIZE

        target_entity_id = EntityId.decode(data[offset:offset + ENTITY_ID_SIZE])
        offset += ENTITY_ID_SIZE

        Munition_id = EntityId.decode(data[offset:offset + ENTITY_ID_SIZE])
        offset += ENTITY_ID_SIZE

        event_id = EntityId.decode(data[offset:offset + ENTITY_ID_SIZE])
        offset += ENTITY_ID_SIZE

        location = Vector3Double.decode(data[offset:offset + VECTOR3_DOUBLE_SIZE])
        offset += VECTOR3_DOUBLE_SIZE

        detonation_result = struct.unpack(">B", data[offset:offset + 1])[0]
        offset += 1

        warhead, fuse = struct.unpack(">HH", data[offset:offset + 4])

        return cls(
            issuing_entity_id=issuing_entity_id,
            target_entity_id=target_entity_id,
            Munition_id=Munition_id,
            event_id=event_id,
            location=location,
            detonation_result=detonation_result,
            warhead=warhead,
            fuse=fuse
        )


@dataclass
class SignalPdu:
    """Signal PDU (Type 4) — ESM/electronic warfare data."""
    PDU_TYPE = PDU_TYPE_SIGNAL

    entity_id: EntityId
    radio_id: int              # uint8
    encoding_scheme: int       # uint16
    tdl_type: int             # uint16
    sample_rate: int          # uint32
    number_of_samples: int    # uint16
    data: bytes               # variable length

    def encode(self) -> bytes:
        result = self.entity_id.encode()
        result += struct.pack(">BHHIH", self.radio_id, self.encoding_scheme,
                             self.tdl_type, self.sample_rate, self.number_of_samples)
        result += self.data
        return result

    @classmethod
    def decode(cls, data: bytes) -> 'SignalPdu':
        offset = 0
        entity_id = EntityId.decode(data[offset:offset + ENTITY_ID_SIZE])
        offset += ENTITY_ID_SIZE

        radio_id, encoding_scheme, tdl_type, sample_rate, number_of_samples = \
            struct.unpack(">BHHIH", data[offset:offset + 11])
        offset += 11

        signal_data = data[offset:]

        return cls(
            entity_id=entity_id,
            radio_id=radio_id,
            encoding_scheme=encoding_scheme,
            tdl_type=tdl_type,
            sample_rate=sample_rate,
            number_of_samples=number_of_samples,
            data=signal_data
        )