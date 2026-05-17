# ESM Client Tests

import unittest
import struct
from src.core.dis.esm_client import EsmClient, EsmReport, EmitterType
from src.core.dis.dis_protocol import EntityId, SignalPdu


class TestEmitterType(unittest.TestCase):
    def test_names(self):
        self.assertEqual(EmitterType.name(1), "SOJ_SBAND_JAMMER")
        self.assertEqual(EmitterType.name(11), "EW_RADAR")
        self.assertEqual(EmitterType.name(99), "UNKNOWN_99")


class TestEsmClient(unittest.TestCase):
    def test_process_empty_signal_pdu(self):
        client = EsmClient()
        pdu = SignalPdu(
            entity_id=EntityId(1, 2, 1),
            radio_id=1,
            encoding_scheme=0,
            tdl_type=0,
            sample_rate=1000,
            number_of_samples=0,
            data=b'',
        )
        report = client.process_signal_pdu(pdu, sim_time=10.0)
        # Should handle empty data gracefully, returning defaults
        self.assertIsNotNone(report)
        self.assertEqual(report.entity_id, EntityId(1, 2, 1))
        self.assertEqual(report.emitter_type, 0)

    def test_process_signal_pdu_with_esm_data(self):
        client = EsmClient()

        # Build ESM data with datum records
        # Datum: ID(4) + length(4) + value
        data = b''
        data += struct.pack(">I", 0x01) + struct.pack(">I", 8) + struct.pack(">d", 3e9)    # Frequency 3 GHz
        data += struct.pack(">I", 0x02) + struct.pack(">I", 4) + struct.pack(">f", 1.5)     # PW 1.5 μs
        data += struct.pack(">I", 0x03) + struct.pack(">I", 4) + struct.pack(">f", 500.0)   # PRF 500 Hz
        data += struct.pack(">I", 0x04) + struct.pack(">I", 4) + struct.pack(">f", -60.0)  # Strength -60 dBm
        data += struct.pack(">I", 0x05) + struct.pack(">I", 4) + struct.pack(">f", 45.0)    # Bearing 45°
        data += struct.pack(">I", 0x10) + struct.pack(">I", 4) + struct.pack(">I", 11)     # Emitter type EW_RADAR

        pdu = SignalPdu(
            entity_id=EntityId(1, 2, 1),
            radio_id=1,
            encoding_scheme=0,
            tdl_type=0,
            sample_rate=1000,
            number_of_samples=10,
            data=data,
        )

        report = client.process_signal_pdu(pdu, sim_time=10.0)

        self.assertIsNotNone(report)
        self.assertIsInstance(report, EsmReport)
        self.assertEqual(report.emitter_type, 11)  # EW_RADAR
        self.assertAlmostEqual(report.frequency_hz, 3e9, delta=1e6)
        self.assertAlmostEqual(report.bearing_deg, 45.0)
        self.assertEqual(report.timestamp, 10.0)

    def test_get_emitter(self):
        client = EsmClient()

        # Add some data
        data = struct.pack(">I", 0x01) + struct.pack(">I", 8) + struct.pack(">d", 10e9)
        pdu = SignalPdu(
            entity_id=EntityId(1, 2, 1),
            radio_id=1,
            encoding_scheme=0,
            tdl_type=0,
            sample_rate=1000,
            number_of_samples=10,
            data=data,
        )
        client.process_signal_pdu(pdu)

        emitter = client.get_emitter(EntityId(1, 2, 1))
        self.assertIsNotNone(emitter)
        self.assertAlmostEqual(emitter["frequency"], 10e9, delta=1e6)

    def test_get_recent_reports(self):
        client = EsmClient()
        # Empty initially
        reports = client.get_recent_reports()
        self.assertEqual(len(reports), 0)

        # Add two reports
        for i in range(2):
            data = struct.pack(">I", 0x01) + struct.pack(">I", 8) + struct.pack(">d", 1e9)
            pdu = SignalPdu(
                entity_id=EntityId(1, 2, i),
                radio_id=1,
                encoding_scheme=0,
                tdl_type=0,
                sample_rate=1000,
                number_of_samples=10,
                data=data,
            )
            client.process_signal_pdu(pdu, sim_time=float(i))

        reports = client.get_recent_reports(count=1)
        self.assertEqual(len(reports), 1)


if __name__ == '__main__':
    unittest.main()