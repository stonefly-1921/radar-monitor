"""Tests for DIS protocol module."""

import struct
import pytest
from src.core.dis import (
    EntityId,
    EntityType,
    Vector3Float,
    Vector3Double,
    Orientation,
    DisTimestamp,
    PduHeader,
    PduType,
    PDU_FAMILY,
)


class TestEntityId:
    def test_create_entity_id(self):
        eid = EntityId(site_id=1, application_id=2, entity_id=3)
        assert eid.site_id == 1
        assert eid.application_id == 2
        assert eid.entity_id == 3

    def test_entity_id_size(self):
        eid = EntityId(site_id=0, application_id=0, entity_id=0)
        assert len(bytes(eid)) == 6

    def test_entity_id_bytes(self):
        eid = EntityId(site_id=256, application_id=512, entity_id=1024)
        data = bytes(eid)
        assert len(data) == 6

    def test_entity_id_from_bytes(self):
        data = struct.pack(">HHH", 1, 2, 3)
        eid = EntityId.from_bytes(data)
        assert eid.site_id == 1
        assert eid.application_id == 2
        assert eid.entity_id == 3


class TestEntityType:
    def test_create_entity_type(self):
        etype = EntityType(kind=1, domain=2, country=100, category=5, subcategory=6, specific=7, extra=8)
        assert etype.kind == 1
        assert etype.domain == 2
        assert etype.country == 100
        assert etype.category == 5
        assert etype.subcategory == 6
        assert etype.specific == 7
        assert etype.extra == 8

    def test_entity_type_size(self):
        etype = EntityType(kind=0, domain=0, country=0, category=0, subcategory=0, specific=0, extra=0)
        assert len(bytes(etype)) == 8


class TestVector3Float:
    def test_create_vector3_float(self):
        v = Vector3Float(x=1.0, y=2.0, z=3.0)
        assert v.x == 1.0
        assert v.y == 2.0
        assert v.z == 3.0

    def test_vector3_float_size(self):
        v = Vector3Float(x=0.0, y=0.0, z=0.0)
        assert len(bytes(v)) == 12


class TestVector3Double:
    def test_create_vector3_double(self):
        v = Vector3Double(x=1.0, y=2.0, z=3.0)
        assert v.x == 1.0
        assert v.y == 2.0
        assert v.z == 3.0

    def test_vector3_double_size(self):
        v = Vector3Double(x=0.0, y=0.0, z=0.0)
        assert len(bytes(v)) == 24


class TestOrientation:
    def test_create_orientation(self):
        o = Orientation(pitch=0.5, yaw=1.5, roll=2.5)
        assert o.pitch == 0.5
        assert o.yaw == 1.5
        assert o.roll == 2.5

    def test_orientation_size(self):
        o = Orientation(pitch=0.0, yaw=0.0, roll=0.0)
        assert len(bytes(o)) == 12


class TestDisTimestamp:
    def test_create_timestamp(self):
        ts = DisTimestamp(hours=12, time=360000)
        assert ts.hours == 12
        assert ts.time == 360000

    def test_timestamp_to_float(self):
        ts = DisTimestamp(hours=0, time=0)
        assert ts.to_float() == 0.0

    def test_timestamp_from_float(self):
        ts = DisTimestamp.from_float(0.5)
        assert ts.hours == 0

    def test_timestamp_size(self):
        ts = DisTimestamp(hours=0, time=0)
        assert len(bytes(ts)) == 5


class TestPduHeader:
    def test_create_header(self):
        header = PduHeader(
            protocol_version=6,
            exercise_id=1,
            pdu_type=PduType.ENTITY_STATE,
            family=PDU_FAMILY,
            timestamp=DisTimestamp(hours=0, time=0),
            length=128,
        )
        assert header.protocol_version == 6
        assert header.exercise_id == 1
        assert header.pdu_type == PduType.ENTITY_STATE
        assert header.length == 128

    def test_header_size(self):
        header = PduHeader(
            protocol_version=6,
            exercise_id=0,
            pdu_type=PduType.ENTITY_STATE,
            family=PDU_FAMILY,
            timestamp=DisTimestamp(hours=0, time=0),
            length=0,
        )
        # 1 + 1 + 1 + 1 + 5 + 2 = 11
        assert len(bytes(header)) == 11


class TestPduType:
    def test_pdu_type_constants(self):
        assert PduType.ENTITY_STATE == 1
        assert PduType.FIRE == 2
        assert PduType.DETONATION == 3
        assert PduType.SIGNAL == 4
        assert PduType.START_RESUME == 10
        assert PduType.STOP_FREEZE == 11

    def test_pdu_type_values(self):
        assert PduType.ENTITY_STATE.value == 1
        assert PduType.FIRE.value == 2