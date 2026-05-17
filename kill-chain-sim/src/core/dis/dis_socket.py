# DIS UDP Multicast Socket
# Kill Chain Research & Simulation Validation Platform

import socket
import struct
import logging

logger = logging.getLogger(__name__)


class DisSocket:
    """UDP Multicast socket for DIS communication.
    
    Handles joining/leaving multicast group and sending/receiving DIS PDUs.
    """

    DEFAULT_MULTICAST_ADDR = "235.7.11.27"
    DEFAULT_PORT = 3002

    def __init__(self, multicast_addr: str = None, port: int = None, bind_address: str = "0.0.0.0"):
        self.multicast_addr = multicast_addr or self.DEFAULT_MULTICAST_ADDR
        self.port = port or self.DEFAULT_PORT
        self.bind_address = bind_address

        self.sock: socket.socket = None
        self._is_open = False

    def open(self) -> None:
        """Open the UDP multicast socket and join the multicast group."""
        if self._is_open:
            logger.warning("Socket already open")
            return

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024)  # 1MB buffer

        # Bind to all interfaces on the port
        self.sock.bind(('', self.port))

        # Join multicast group
        mreq = struct.pack("4s4s",
                          socket.inet_aton(self.multicast_addr),
                          socket.inet_aton("0.0.0.0"))
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        # Don't receive our own multicast packets
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)

        # Set TTL for multicast
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 8)

        self.sock.setblocking(False)
        self._is_open = True
        logger.info(f"DIS socket opened on {self.multicast_addr}:{self.port}")

    def close(self) -> None:
        """Close the socket and leave the multicast group."""
        if not self._is_open:
            return

        try:
            # Leave multicast group
            mreq = struct.pack("4s4s",
                              socket.inet_aton(self.multicast_addr),
                              socket.inet_aton("0.0.0.0"))
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, mreq)
        except Exception as e:
            logger.warning(f"Error leaving multicast group: {e}")

        try:
            self.sock.close()
        except Exception as e:
            logger.warning(f"Error closing socket: {e}")

        self._is_open = False
        logger.info("DIS socket closed")

    def receive(self, buffer_size: int = 8192) -> tuple:
        """Receive a UDP packet.
        
        Returns:
            tuple: (data: bytes, address: tuple) or (None, None) if no data
            
        Raises:
            BlockingIOError: If no data available and socket is non-blocking
        """
        if not self._is_open:
            raise RuntimeError("Socket not open")

        try:
            data, address = self.sock.recvfrom(buffer_size)
            return data, address
        except BlockingIOError:
            # No data available
            return None, None
        except Exception as e:
            logger.error(f"Error receiving data: {e}")
            return None, None

    def send(self, data: bytes, address: tuple = None) -> int:
        """Send a UDP packet.
        
        Args:
            data: The bytes to send
            address: Optional (host, port) tuple. If None, sends to multicast address.
            
        Returns:
            int: Number of bytes sent
        """
        if not self._is_open:
            raise RuntimeError("Socket not open")

        target = address or (self.multicast_addr, self.port)

        try:
            sent = self.sock.sendto(data, target)
            return sent
        except Exception as e:
            logger.error(f"Error sending data: {e}")
            raise

    @property
    def is_open(self) -> bool:
        return self._is_open

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False