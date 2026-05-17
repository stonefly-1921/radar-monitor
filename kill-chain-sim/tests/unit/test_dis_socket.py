# Tests for DIS Socket

import unittest
from src.core.dis.dis_socket import DisSocket


class TestDisSocket(unittest.TestCase):
    def test_default_addresses(self):
        socket = DisSocket()
        self.assertEqual(socket.multicast_addr, "235.7.11.27")
        self.assertEqual(socket.port, 3002)

    def test_custom_addresses(self):
        socket = DisSocket(multicast_addr="239.1.1.1", port=5000)
        self.assertEqual(socket.multicast_addr, "239.1.1.1")
        self.assertEqual(socket.port, 5000)

    def test_is_open_initially_false(self):
        socket = DisSocket()
        self.assertFalse(socket.is_open)

    def test_open_and_close(self):
        socket = DisSocket()
        socket.open()
        self.assertTrue(socket.is_open)
        socket.close()
        self.assertFalse(socket.is_open)

    def test_context_manager(self):
        with DisSocket() as socket:
            self.assertTrue(socket.is_open)
        # After context, should be closed
        self.assertFalse(socket.is_open)

    def test_reopen_after_close(self):
        socket = DisSocket()
        socket.open()
        socket.close()
        # Should not raise, just log warning
        socket.open()
        self.assertTrue(socket.is_open)
        socket.close()

    def test_double_close(self):
        socket = DisSocket()
        socket.open()
        socket.close()
        # Should not raise
        socket.close()
        self.assertFalse(socket.is_open)


if __name__ == '__main__':
    unittest.main()