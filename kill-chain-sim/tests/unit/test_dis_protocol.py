# Tests for DIS Protocol Definitions

import unittest
import struct
from src.core.dis.dis_protocol import (
    PDU_TYPE_ENTITY_STATE, PDU_TYPE_FIRE, PDU_TYPE_DETONATION, PDU_TYPE_SIGNAL,
    EntityId, EntityType, Vector3Float, Vector3Double, Orientation,
    DisTimestamp, PduHeader, EntityStatePdu, FirePdu, DetonationPdu, SignalPdu,
    ENTITY_ID_SIZE, ENTITY_TYPE_SIZE, VECTOR3_FLOAT_SIZE, VECTOR3_DOUBLE_SIZE,
    ORIENTATION_SIZE, DIS_TIMESTAMP_SIZE, PDU_HEADER_SIZE,
)


class TestPduTypeConstants(unittest.TestCase):
    def test_entity_state_type(self):
        self.assertEqual(PDU_TYPE_ENTITY_STATE, 1)

    def test_fire_type(self):
        self.assertEqual(PDU_TYPE_FIRE, 2)

    def test_detonation_type(self):
        self.assertEqual(PDU_TYPE_DETONATION, 3)

    def test_signal_type(self):
        self.assertEqual(PDU_TYPE_SIGNAL, 4)


class TestEntityId(unittest.TestCase):
    def test_encode_decode_roundtrip(self):
        entity_id = EntityId(site_id=1, application_id=2, entity_id=100)
        encoded = entity_id.encode()
        self.assertEqual(len(encoded), ENTITY_ID_SIZE)
        decoded = EntityId.decode(encoded)
        self.assertEqual(decoded.site_id, 1)
        self.assertEqual(decoded.application_id, 2)
        self.assertEqual(decoded.entity_id, 100)

    def test_str_representation(self):
        entity_id = EntityId(site_id=1, application_id=2, entity_id=100)
        self.assertEqual(str(entity_id), "1:2:100")

    def test_equality(self):
        id1 = EntityId(1, 2, 3)
        id2 = EntityId(1, 2, 3)
        id3 = EntityId(1, 2, 4)
        self.assertEqual(id1, id2)
        self.assertNotEqual(id1, id3)


class TestEntityType(unittest.TestCase):
    def test_encode_decode_roundtrip(self):
        et = EntityType(kind=1, domain=2, country=222, category=1,
                       subcategory=1, specific=1, extra=0)
        encoded = et.encode()
        self.assertEqual(len(encoded), ENTITY_TYPE_SIZE)
        decoded = EntityType.decode(encoded)
        self.assertEqual(decoded.kind, 1)
        self.assertEqual(decoded.domain, 2)
        self.assertEqual(decoded.country, 222)
        self.assertEqual(decoded.category, 1)


class TestVector3Float(unittest.TestCase):
    def test_encode_decode_roundtrip(self):
        vec = Vector3Float(x=100.0, y=200.0, z=-50.0)
        encoded = vec.encode()
        self.assertEqual(len(encoded), VECTOR3_FLOAT_SIZE)
        decoded = Vector3Float.decode(encoded)
        self.assertAlmostEqual(decoded.x, 100.0)
        self.assertAlmostEqual(decoded.y, 200.0)
        self.assertAlmostEqual(decoded.z, -50.0)


class TestVector3Double(unittest.TestCase):
    def test_encode_decode_roundtrip(self):
        vec = Vector3Double(x=1e6, y=-2e6, z=5000.5)
        encoded = vec.encode()
        self.assertEqual(len(encoded), VECTOR3_DOUBLE_SIZE)
        decoded = Vector3Double.decode(encoded)
        self.assertAlmostEqual(decoded.x, 1e6)
        self.assertAlmostEqual(decoded.y, -2e6)
        self.assertAlmostEqual(decoded.z, 5000.5)


class TestOrientation(unittest.TestCase):
    def test_encode_decode_roundtrip(self):
        ori = Orientation(pitch=0.1, yaw=1.57, roll=0.0)
        encoded = ori.encode()
        self.assertEqual(len(encoded), ORIENTATION_SIZE)
        decoded = Orientation.decode(encoded)
        self.assertAlmostEqual(decoded.pitch, 0.1)
        self.assertAlmostEqual(decoded.yaw, 1.57, places=5)


class TestDisTimestamp(unittest.TestCase):
    def test_from_seconds(self):
        ts = DisTimestamp.from_seconds(3723.45)  # 1:02:03.45
        # 3723 seconds = 1 hour + 123 seconds
        self.assertEqual(ts.seconds % 3600, 123)

    def test_to_seconds(self):
        ts = DisTimestamp(seconds=3603)  # 1 hour + 3 seconds
        self.assertAlmostEqual(ts.to_seconds(), 3603.0)

    def test_encode_decode_roundtrip(self):
        ts = DisTimestamp(seconds=43212)  # 12 hours * 3600 + 12 seconds
        encoded = ts.encode()
        self.assertEqual(len(encoded), 4)  # DIS timestamp is 4 bytes (uint32 big-endian)
        decoded = DisTimestamp.decode(encoded)
        self.assertEqual(decoded.seconds, ts.seconds % 3600)

    def test_now(self):
        ts = DisTimestamp.now()
        self.assertGreaterEqual(ts.seconds, 0)
        self.assertLess(ts.seconds, 86400)


class TestEntityStatePdu(unittest.TestCase):
    def test_pdu_type(self):
        self.assertEqual(EntityStatePdu.PDU_TYPE, PDU_TYPE_ENTITY_STATE)

    def test_encode_decode(self):
        pdu = EntityStatePdu(
            entity_id=EntityId(1, 1, 100),
            entity_type=EntityType(2, 1, 222, 2, 1, 1, 0),
            location=Vector3Double(1000.0, 2000.0, 500.0),
            orientation=Orientation(0.1, 1.57, 0.0),
            velocity=Vector3Float(100.0, 50.0, 0.0),
        )
        encoded = pdu.encode()
        decoded = EntityStatePdu.decode(encoded)
        self.assertEqual(decoded.entity_id.entity_id, 100)
        self.assertAlmostEqual(decoded.location.x, 1000.0)


class TestFirePdu(unittest.TestCase):
    def test_pdu_type(self):
        self.assertEqual(FirePdu.PDU_TYPE, PDU_TYPE_FIRE)

    def test_encode_decode(self):
        pdu = FirePdu(
            fire_mission_index=42,
            emitting_entity_id=EntityId(1, 1, 1),
            target_entity_id=EntityId(2, 1, 1),
            Munition_id=EntityId(1, 1, 99),
            warhead=100,
            fuse=2,
        )
        encoded = pdu.encode()
        decoded = FirePdu.decode(encoded)
        self.assertEqual(decoded.fire_mission_index, 42)
        self.assertEqual(decoded.emitting_entity_id.site_id, 1)


class TestDetonationPdu(unittest.TestCase):
    def test_pdu_type(self):
        self.assertEqual(DetonationPdu.PDU_TYPE, PDU_TYPE_DETONATION)

    def test_encode_decode(self):
        pdu = DetonationPdu(
            issuing_entity_id=EntityId(1, 1, 1),
            target_entity_id=EntityId(2, 1, 1),
            Munition_id=EntityId(1, 1, 99),
            event_id=EntityId(1, 1, 1),
            location=Vector3Double(1000.0, 2000.0, 0.0),
            detonation_result=0,
        )
        encoded = pdu.encode()
        decoded = DetonationPdu.decode(encoded)
        self.assertEqual(decoded.detonation_result, 0)


class TestSignalPdu(unittest.TestCase):
    def test_pdu_type(self):
        self.assertEqual(SignalPdu.PDU_TYPE, PDU_TYPE_SIGNAL)

    def test_encode_decode(self):
        pdu = SignalPdu(
            entity_id=EntityId(1, 2, 1),
            radio_id=1,
            encoding_scheme=0,
            tdl_type=0,
            sample_rate=1000,
            number_of_samples=10,
            data=b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09',
        )
        encoded = pdu.encode()
        decoded = SignalPdu.decode(encoded)
        self.assertEqual(decoded.number_of_samples, 10)
        self.assertEqual(decoded.data, pdu.data)


if __name__ == '__main__':
    unittest.main()