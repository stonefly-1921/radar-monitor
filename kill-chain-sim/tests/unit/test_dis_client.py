# DIS Client Integration Test

import unittest
import time
from src.core.dis.dis_client import DisClient
from src.core.dis.dis_protocol import PDU_TYPE_ENTITY_STATE, PDU_TYPE_FIRE
from src.core.dis.fire_control import FireControl
from src.core.dis.dis_protocol import EntityId


class TestDisClient(unittest.TestCase):
    def test_client_lifecycle(self):
        """Test client start/stop without AFSIM."""
        client = DisClient(multicast_addr="235.7.11.27", port=3002)
        self.assertFalse(client.is_running())
        client.start()
        self.assertTrue(client.is_running())
        client.stop()
        self.assertFalse(client.is_running())

    def test_client_context_manager(self):
        """Test client as context manager."""
        with DisClient() as client:
            self.assertTrue(client.is_running())
        # After exiting context, should be stopped
        self.assertFalse(client.is_running())

    def test_register_handler(self):
        """Test handler registration."""
        client = DisClient()
        calls = []
        def handler(pdu):
            calls.append(pdu)

        client.register_handler(PDU_TYPE_ENTITY_STATE, handler)
        self.assertIn(PDU_TYPE_ENTITY_STATE, client.dispatcher.handlers)

    def test_fire_control_integration(self):
        """Test that fire control is properly integrated."""
        client = DisClient()
        fc = client.fire_control
        self.assertIsNotNone(fc)

        # Create a fire mission
        mission = fc.create_fire_mission(
            launcher_id=EntityId(1, 1, 10),
            target_id=EntityId(2, 1, 20),
            Munition_id=EntityId(1, 1, 99),
        )

        # Generate PDU bytes
        pdu_bytes = fc.build_fire_pdu_bytes(mission)
        self.assertIsInstance(pdu_bytes, bytes)
        self.assertGreater(len(pdu_bytes), 30)  # Should be at least timestamp + header + fire data

    def test_entity_tracker_integration(self):
        """Test that entity tracker is properly integrated."""
        client = DisClient()
        tracker = client.tracker
        self.assertIsNotNone(tracker)
        self.assertEqual(tracker.count(), 0)

    def test_esm_client_integration(self):
        """Test that ESM client is properly integrated."""
        client = DisClient()
        esm = client.esm_client
        self.assertIsNotNone(esm)

    def test_get_stats(self):
        """Test statistics collection."""
        client = DisClient()
        stats = client.get_stats()
        self.assertIn("pdu_received", stats)
        self.assertIn("pdu_sent", stats)
        self.assertIn("pdu_by_type", stats)


if __name__ == '__main__':
    unittest.main()