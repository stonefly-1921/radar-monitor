"""DIS Socket - UDP multicast socket wrapper for DIS protocol."""

import socket
import struct


class DisSocket:
    """UDP socket wrapper for DIS multicast receive/send.
    
    Attributes:
        multicast_addr: Multicast group address (default "235.7.11.27")
        port: UDP port number (default 3002)
        bind_address: Local bind address (default "0.0.0.0")
    """

    def __init__(
        self,
        multicast_addr: str = "235.7.11.27",
        port: int = 3002,
        bind_address: str = "0.0.0.0",
    ):
        """Initialize DIS socket.
        
        Args:
            multicast_addr: Multicast group address
            port: UDP port number
            bind_address: Local address to bind to
        """
        self.multicast_addr = multicast_addr
        self.port = port
        self.bind_address = bind_address
        self._socket: socket.socket | None = None

    def open(self) -> None:
        """Create and configure UDP socket for multicast.
        
        Creates a UDP socket, sets SO_REUSEADDR, binds to the specified
        address and port, joins the multicast group, and configures
        loopback and TTL settings.
        
        Raises:
            OSError: If socket creation or configuration fails
        """
        if self._socket is not None:
            return

        # Create UDP socket
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Set SO_REUSEADDR to allow multiple processes to bind
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Bind to local address and port
        self._socket.bind((self.bind_address, self.port))

        # Join multicast group using struct.pack for the membership request
        # Format: 4s (4-byte string for multicast addr) + I (unsigned int for interface)
        mreq = struct.pack(
            "4sI",
            socket.inet_aton(self.multicast_addr),
            socket.INADDR_ANY,
        )
        self._socket.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_ADD_MEMBERSHIP,
            mreq,
        )

        # Don't receive our own multicast packets (loopback disabled)
        self._socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)

        # Set multicast TTL (time-to-live)
        self._socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 8)

        # Set a reasonable timeout for receive operations
        self._socket.settimeout(1.0)

    def close(self) -> None:
        """Close the socket and leave multicast group.
        
        If the socket is not open, this method does nothing.
        """
        if self._socket is None:
            return

        try:
            # Leave multicast group
            mreq = struct.pack(
                "4sI",
                socket.inet_aton(self.multicast_addr),
                socket.INADDR_ANY,
            )
            self._socket.setsockopt(
                socket.IPPROTO_IP,
                socket.IP_DROP_MEMBERSHIP,
                mreq,
            )
        except OSError:
            pass  # Ignore errors when leaving group

        try:
            self._socket.close()
        except OSError:
            pass  # Ignore errors when closing

        self._socket = None

    def receive(self, bufsize: int = 4096) -> tuple[bytes, tuple[str, int]]:
        """Receive a UDP packet from the multicast group.
        
        Args:
            bufsize: Maximum buffer size to receive (default 4096)
            
        Returns:
            Tuple of (data: bytes, address: tuple[str, int])
            
        Raises:
            RuntimeError: If socket is not open
            socket.timeout: If no data received within timeout period
        """
        if self._socket is None:
            raise RuntimeError("Socket is not open")

        return self._socket.recvfrom(bufsize)

    def send(self, data: bytes, address: tuple[str, int] | None = None) -> int:
        """Send a UDP packet.
        
        If address is None, sends to the multicast group address and port.
        Otherwise, sends to the specified address.
        
        Args:
            data: Data bytes to send
            address: Optional (host, port) tuple for unicast destination
            
        Returns:
            Number of bytes sent
            
        Raises:
            RuntimeError: If socket is not open
        """
        if self._socket is None:
            raise RuntimeError("Socket is not open")

        if address is None:
            address = (self.multicast_addr, self.port)

        return self._socket.sendto(data, address)

    @property
    def is_open(self) -> bool:
        """Check if the socket is open.
        
        Returns:
            True if socket is open, False otherwise
        """
        return self._socket is not None

    def __enter__(self) -> "DisSocket":
        """Context manager entry."""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()