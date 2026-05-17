"""Unit tests for DIS socket module."""

import socket
from unittest.mock import Mock, patch
import pytest

from src.core.dis.dis_socket import DisSocket


class TestDisSocket:
    """Tests for DisSocket class."""

    def test_default_constructor(self):
        """Test default constructor values."""
        sock = DisSocket()
        assert sock.multicast_addr == "235.7.11.27"
        assert sock.port == 3002
        assert sock.bind_address == "0.0.0.0"
        assert not sock.is_open

    def test_custom_constructor(self):
        """Test custom constructor values."""
        sock = DisSocket(multicast_addr="235.8.12.30", port=4000, bind_address="127.0.0.1")
        assert sock.multicast_addr == "235.8.12.30"
        assert sock.port == 4000
        assert sock.bind_address == "127.0.0.1"

    @patch("src.core.dis.dis_socket.socket.socket")
    def test_open_creates_socket(self, mock_socket_class):
        """Test that open() creates a UDP socket."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        sock = DisSocket()
        sock.open()

        mock_socket_class.assert_called_once_with(socket.AF_INET, socket.SOCK_DGRAM)
        assert sock.is_open

    @patch("src.core.dis.dis_socket.socket.socket")
    def test_open_sets_reuseaddr(self, mock_socket_class):
        """Test that open() sets SO_REUSEADDR."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        sock = DisSocket()
        sock.open()

        mock_socket.setsockopt.assert_any_call(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    @patch("src.core.dis.dis_socket.socket.socket")
    def test_open_binds_socket(self, mock_socket_class):
        """Test that open() binds to the correct address and port."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        sock = DisSocket(multicast_addr="235.7.11.27", port=3002, bind_address="0.0.0.0")
        sock.open()

        mock_socket.bind.assert_called_once_with(("0.0.0.0", 3002))

    @patch("src.core.dis.dis_socket.socket.socket")
    def test_open_joins_multicast_group(self, mock_socket_class):
        """Test that open() joins the multicast group."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        sock = DisSocket(multicast_addr="235.7.11.27", port=3002, bind_address="0.0.0.0")
        sock.open()

        # Find the IP_ADD_MEMBERSHIP call
        calls = mock_socket.setsockopt.call_args_list
        membership_call = None
        for call in calls:
            if call[0][1] == socket.IP_ADD_MEMBERSHIP:
                membership_call = call
                break

        assert membership_call is not None, "IP_ADD_MEMBERSHIP was not called"

    @patch("src.core.dis.dis_socket.socket.socket")
    def test_open_disables_loopback(self, mock_socket_class):
        """Test that open() sets IP_MULTICAST_LOOP to 0."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        sock = DisSocket()
        sock.open()

        mock_socket.setsockopt.assert_any_call(
            socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0
        )

    @patch("src.core.dis.dis_socket.socket.socket")
    def test_open_sets_ttl(self, mock_socket_class):
        """Test that open() sets IP_MULTICAST_TTL to 8."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        sock = DisSocket()
        sock.open()

        mock_socket.setsockopt.assert_any_call(
            socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 8
        )

    @patch("src.core.dis.dis_socket.socket.socket")
    def test_open_idempotent(self, mock_socket_class):
        """Test that open() can be called twice safely."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        sock = DisSocket()
        sock.open()
        sock.open()  # Should not raise

        assert mock_socket_class.call_count == 1

    @patch("src.core.dis.dis_socket.socket.socket")
    def test_close_leaves_multicast_and_closes(self, mock_socket_class):
        """Test that close() leaves multicast group and closes socket."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        sock = DisSocket()
        sock.open()
        sock.close()

        # Verify IP_DROP_MEMBERSHIP was called
        calls = mock_socket.setsockopt.call_args_list
        drop_call = None
        for call in calls:
            if call[0][1] == socket.IP_DROP_MEMBERSHIP:
                drop_call = call
                break
        assert drop_call is not None, "IP_DROP_MEMBERSHIP was not called"
        mock_socket.close.assert_called()
        assert not sock.is_open

    @patch("src.core.dis.dis_socket.socket.socket")
    def test_close_when_not_open(self, mock_socket_class):
        """Test that close() does nothing if socket is not open."""
        sock = DisSocket()
        sock.close()  # Should not raise

        mock_socket_class.assert_not_called()

    @patch("src.core.dis.dis_socket.socket.socket")
    def test_receive_returns_data_and_address(self, mock_socket_class):
        """Test that receive() returns (data, address) tuple."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket
        mock_socket.recvfrom.return_value = (b"test data", ("192.168.1.1", 1234))

        sock = DisSocket()
        sock.open()
        data, addr = sock.receive()

        assert data == b"test data"
        assert addr == ("192.168.1.1", 1234)
        mock_socket.recvfrom.assert_called_once_with(4096)

    @patch("src.core.dis.dis_socket.socket.socket")
    def test_receive_timeout(self, mock_socket_class):
        """Test that receive() respects socket timeout."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        sock = DisSocket()
        sock.open()
        sock.receive()

        # Default timeout should be set
        mock_socket.settimeout.assert_called()

    @patch("src.core.dis.dis_socket.socket.socket")
    def test_send_to_multicast(self, mock_socket_class):
        """Test that send() sends to multicast address when no address provided."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        sock = DisSocket(multicast_addr="235.7.11.27", port=3002)
        sock.open()
        sock.send(b"test message")

        mock_socket.sendto.assert_called_once()
        call_args = mock_socket.sendto.call_args[0]
        assert call_args[0] == b"test message"
        # Address should be multicast address and port
        assert call_args[1][0] == "235.7.11.27"
        assert call_args[1][1] == 3002

    @patch("src.core.dis.dis_socket.socket.socket")
    def test_send_to_specific_address(self, mock_socket_class):
        """Test that send() sends to specific address when provided."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        sock = DisSocket(multicast_addr="235.7.11.27", port=3002)
        sock.open()
        sock.send(b"test message", address=("192.168.1.100", 5000))

        mock_socket.sendto.assert_called_once_with(b"test message", ("192.168.1.100", 5000))

    @patch("src.core.dis.dis_socket.socket.socket")
    def test_send_without_open_raises(self, mock_socket_class):
        """Test that send() raises error if socket is not open."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        sock = DisSocket()
        # Not calling open()

        with pytest.raises(RuntimeError, match="Socket is not open"):
            sock.send(b"test message")

    @patch("src.core.dis.dis_socket.socket.socket")
    def test_receive_without_open_raises(self, mock_socket_class):
        """Test that receive() raises error if socket is not open."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        sock = DisSocket()
        # Not calling open()

        with pytest.raises(RuntimeError, match="Socket is not open"):
            sock.receive()

    @patch("src.core.dis.dis_socket.socket.socket")
    def test_is_open_property(self, mock_socket_class):
        """Test is_open property reflects socket state."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        sock = DisSocket()
        assert not sock.is_open

        sock.open()
        assert sock.is_open

        sock.close()
        assert not sock.is_open