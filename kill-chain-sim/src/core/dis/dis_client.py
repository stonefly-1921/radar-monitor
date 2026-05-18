# DIS Client - Full async multi-threaded DIS interface
# Task 9: DIS Client Integration

import socket
import struct
import threading
import logging
import queue
import time
from typing import Optional, Callable, Dict, List

from src.core.dis.dis_protocol import (
    EntityId, EntityType, EntityStatePdu, FirePdu, DetonationPdu, SignalPdu,
    PDU_TYPE_ENTITY_STATE, PDU_TYPE_FIRE, PDU_TYPE_DETONATION, PDU_TYPE_SIGNAL,
    PDU_HEADER_SIZE, DisTimestamp,
)
from src.core.dis.dis_socket import DisSocket
from src.core.dis.dis_dispatcher import DisDispatcher
from src.core.dis.entity_tracker import EntityTracker, Location
from src.core.dis.fire_control import FireControl
from src.core.dis.esm_client import EsmClient
from src.core.dis.esm_trajectory_tracker import EsmTrajectoryTracker

logger = logging.getLogger(__name__)


class DisClient:
    """Async multi-threaded DIS Client.

    Architecture:
    - Receive thread: listens for DIS PDUs on UDP multicast
    - Main thread: processes received PDUs through dispatcher
    - Send thread: sends queued Fire/Signal commands

    Usage:
        client = DisClient()
        client.register_handler(PDU_TYPE_ENTITY_STATE, my_handler)
        client.start()
        # ... use client ...
        client.stop()
    """

    def __init__(
        self,
        multicast_addr: str = "235.7.11.27",
        port: int = 3002,
        exercise_id: int = 0,
    ):
        self.multicast_addr = multicast_addr
        self.port = port
        self.exercise_id = exercise_id

        # Components
        self.socket: Optional[DisSocket] = None
        self.dispatcher = DisDispatcher()
        self.tracker = EntityTracker()
        self.fire_control = FireControl(exercise_id=exercise_id)
        self.esm_client = EsmClient()
        self.esm_trajectory_tracker = EsmTrajectoryTracker()

        # ESM fallback tracking: detect when we only receive Signal PDUs
        self._last_entity_state_time = 0.0
        self._esm_fallback_threshold_sec = 5.0  # Activate ESM tracker after 5s with no Entity State
        self._esm_fallback_active = False

        # Receive queue (from socket thread to main processing)
        self._recv_queue: queue.Queue = queue.Queue(maxsize=1000)

        # Send queue (from main thread to socket thread)
        self._send_queue: queue.Queue = queue.Queue(maxsize=100)

        # Threads
        self._recv_thread: Optional[threading.Thread] = None
        self._send_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

        # Statistics
        self._stats = {
            "pdu_received": 0,
            "pdu_sent": 0,
            "pdu_by_type": {1: 0, 2: 0, 3: 0, 4: 0},
            "errors": 0,
        }

        # Auto-track entities
        self._auto_track = True
        if self._auto_track:
            self.dispatcher.register(PDU_TYPE_ENTITY_STATE, self._track_entity_handler)
            self.dispatcher.register(PDU_TYPE_SIGNAL, self._esm_handler)

    def register_handler(self, pdu_type: int, handler: Callable) -> None:
        """Register a PDU handler.

        Args:
            pdu_type: PDU type (1=Entity State, 2=Fire, 3=Detonation, 4=Signal)
            handler: Callable that takes parsed PDU dict
        """
        self.dispatcher.register(pdu_type, handler)

    def start(self) -> None:
        """Start the DIS client (starts receive and send threads)."""
        with self._lock:
            if self._running:
                logger.warning("Client already running")
                return

            self.socket = DisSocket(
                multicast_addr=self.multicast_addr,
                port=self.port,
            )
            self.socket.open()

            self._running = True

            self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
            self._send_thread = threading.Thread(target=self._send_loop, daemon=True)

            self._recv_thread.start()
            self._send_thread.start()

            logger.info(f"DIS Client started on {self.multicast_addr}:{self.port}")

    def stop(self) -> None:
        """Stop the DIS client (stops threads and closes socket)."""
        with self._lock:
            if not self._running:
                return

            self._running = False

            if self.socket:
                try:
                    self.socket.close()
                except Exception as e:
                    logger.warning(f"Error closing socket: {e}")

            if self._recv_thread:
                self._recv_thread.join(timeout=2.0)
            if self._send_thread:
                self._send_thread.join(timeout=2.0)

            self.socket = None
            logger.info("DIS Client stopped")

    def is_running(self) -> bool:
        return self._running

    def _recv_loop(self) -> None:
        """Receive thread: read from socket, parse PDUs, put in queue."""
        logger.info("Receive thread started")
        while self._running:
            try:
                data, addr = self.socket.receive()
                if data:
                    # Log raw PDU info
                    if len(data) >= 4:
                        pdu_type = data[3]
                        logger.debug(f"RX PDU type={pdu_type} size={len(data)} from {addr}")
                    self._recv_queue.put((data, addr))
                else:
                    time.sleep(0.001)  # Small sleep when no data
            except Exception as e:
                logger.error(f"Receive error: {e}")
                self._stats["errors"] += 1
                time.sleep(0.1)

    def _send_loop(self) -> None:
        """Send thread: take items from send queue and transmit."""
        logger.info("Send thread started")
        while self._running:
            try:
                data, addr = self._send_queue.get(timeout=0.1)
                if addr:
                    self.socket.send(data, addr)
                else:
                    self.socket.send(data)
                self._stats["pdu_sent"] += 1
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Send error: {e}")
                self._stats["errors"] += 1

    def process_next(self, timeout: float = 0.1) -> Optional[dict]:
        """Process one PDU from the receive queue (call from main loop).

        Args:
            timeout: How long to wait for a PDU.

        Returns:
            Parsed PDU dict or None if queue empty.
        """
        try:
            data, addr = self._recv_queue.get(timeout=timeout)
            return self._parse_and_dispatch(data)
        except queue.Empty:
            return None

    def _parse_and_dispatch(self, data: bytes) -> Optional[dict]:
        """Parse raw DIS PDU bytes and dispatch to handlers."""
        try:
            if len(data) < 6:
                logger.warning(f"PDU too short: {len(data)} bytes")
                return None

            # Parse PDU header
            pdu_type = data[3]  # byte offset in DIS PDU (after timestamp + version + exercise)
            exercise_id = data[2]

            # Update stats
            self._stats["pdu_received"] += 1
            if pdu_type in self._stats["pdu_by_type"]:
                self._stats["pdu_by_type"][pdu_type] += 1

            # Parse based on type
            pdu_dict = None
            if pdu_type == PDU_TYPE_ENTITY_STATE:
                try:
                    pdu = EntityStatePdu.decode(data[5:])  # skip header
                    # Normalize entity ID before dispatching so all handlers see consistent IDs
                    normalized_eid = self.tracker.normalize_entity_id(pdu.entity_id)
                    pdu = EntityStatePdu(
                        entity_id=normalized_eid,
                        entity_type=pdu.entity_type,
                        location=pdu.location,
                        orientation=pdu.orientation,
                        velocity=pdu.velocity,
                        dead_reckoning_type=pdu.dead_reckoning_type,
                        entity_parameters=pdu.entity_parameters,
                        number_of_datum=pdu.number_of_datum,
                        datum_records=pdu.datum_records,
                    )
                    pdu_dict = {
                        "pdu_type": pdu_type,
                        "entity_id": normalized_eid,  # Already normalized
                        "entity_type": pdu.entity_type,
                        "location": pdu.location,
                        "orientation": pdu.orientation,
                        "velocity": pdu.velocity,
                    }
                except Exception as e:
                    logger.warning(f"Failed to parse Entity State PDU: {e}")

            elif pdu_type == PDU_TYPE_FIRE:
                try:
                    pdu = FirePdu.decode(data[5:])
                    pdu_dict = {
                        "pdu_type": pdu_type,
                        "fire_mission_index": pdu.fire_mission_index,
                        "emitting_entity_id": pdu.emitting_entity_id,
                        "target_entity_id": pdu.target_entity_id,
                        "Munition_id": pdu.Munition_id,
                    }
                except Exception as e:
                    logger.warning(f"Failed to parse Fire PDU: {e}")

            elif pdu_type == PDU_TYPE_DETONATION:
                try:
                    pdu = DetonationPdu.decode(data[5:])
                    pdu_dict = {
                        "pdu_type": pdu_type,
                        "target_entity_id": pdu.target_entity_id,
                        "Munition_id": pdu.Munition_id,
                        "location": pdu.location,
                        "detonation_result": pdu.detonation_result,
                    }
                except Exception as e:
                    logger.warning(f"Failed to parse Detonation PDU: {e}")

            elif pdu_type == PDU_TYPE_SIGNAL:
                try:
                    pdu = SignalPdu.decode(data[5:])
                    pdu_dict = {
                        "pdu_type": pdu_type,
                        "entity_id": pdu.entity_id,
                        "radio_id": pdu.radio_id,
                        "data": pdu.data,
                    }
                except Exception as e:
                    logger.warning(f"Failed to parse Signal PDU: {e}")

            # Dispatch to registered handlers
            if pdu_dict:
                self.dispatcher.dispatch(pdu_dict)

            return pdu_dict

        except Exception as e:
            logger.error(f"PDU parse error: {e}")
            self._stats["errors"] += 1
            return None

    def _track_entity_handler(self, pdu: dict) -> None:
        """Auto-handler: track entity from Entity State PDU."""
        try:
            # Reset ESM fallback timer when we receive Entity State PDUs
            self._last_entity_state_time = time.time()
            if self._esm_fallback_active:
                logger.info("Entity State PDU received - deactivating ESM fallback")
                self._esm_fallback_active = False

            entity_id = pdu["entity_id"]
            entity_type = pdu["entity_type"]
            location = pdu["location"]
            velocity = pdu["velocity"]
            orientation = pdu["orientation"]
            logger.debug(f"_track_entity_handler: entity_id={entity_id}, entity_type={entity_type}")
            # Convert location (ECEF to lat/lon/alt approximation)
            loc = self._ecef_to_geodetic(location)

            logger.debug(f"_track_entity_handler: about to call tracker.update with entity_id={entity_id}")
            self.tracker.update(
                entity_id=entity_id,
                entity_type=entity_type,
                location=loc,
                velocity=velocity,
                orientation=orientation,
                timestamp=time.time(),
            )
            logger.debug(f"_track_entity_handler: tracker now has {self.tracker.count()} entities")
        except Exception as e:
            logger.warning(f"Entity tracking error: {e}", exc_info=True)

    def _esm_handler(self, pdu: dict) -> None:
        """Auto-handler: process ESM report from Signal PDU."""
        try:
            signal_pdu = SignalPdu(
                entity_id=pdu["entity_id"],
                radio_id=pdu["radio_id"],
                encoding_scheme=0,
                tdl_type=0,
                sample_rate=0,
                number_of_samples=0,
                data=pdu["data"],
            )
            self.esm_client.process_signal_pdu(signal_pdu, sim_time=time.time())

            # Also feed to ESM trajectory tracker for virtual track generation
            current_time = time.time()
            self.esm_trajectory_tracker.process_signal_pdu(signal_pdu, sim_time=current_time)

            # Check if we should activate ESM fallback mode
            # If no Entity State PDUs received for threshold seconds, activate
            if not self._esm_fallback_active:
                if current_time - self._last_entity_state_time > self._esm_fallback_threshold_sec:
                    logger.info(f"No Entity State PDUs for {self._esm_fallback_threshold_sec}s - activating ESM trajectory fallback")
                    self._esm_fallback_active = True
        except Exception as e:
            logger.warning(f"ESM processing error: {e}")

    def run_trajectory_estimation(self) -> None:
        """Update EntityTracker with virtual tracks from ESM fallback.
        
        Called periodically (e.g., from main loop) to merge virtual tracks
        into the EntityTracker when ESM fallback mode is active.
        """
        if not self._esm_fallback_active:
            return

        virtual_tracks = self.esm_trajectory_tracker.get_virtual_tracks()
        for track in virtual_tracks:
            # Check if this virtual track already exists in EntityTracker
            existing = self.tracker.get(track.entity_id)
            if existing is None:
                # Add new virtual track
                self.tracker.add(track)
                logger.debug(f"Added virtual track: {track.entity_id} at {track.location}")
            else:
                # Update existing track
                self.tracker.update(
                    entity_id=track.entity_id,
                    entity_type=track.entity_type,
                    location=track.location,
                    velocity=track.velocity,
                    orientation=track.orientation,
                    timestamp=track.timestamp,
                )

    def add_virtual_track(self, track) -> None:
        """Add a virtual track to the EntityTracker.
        
        Args:
            track: TrackedEntity to add
        """
        self.tracker.add(track)

    def _ecef_to_geodetic(self, ecef: 'Vector3Double') -> Location:
        """Convert ECEF (meters) to geodetic (lat/lon/alt).

        Simplified conversion assuming WGS84.
        """
        import math

        a = 6378137.0  # semi-major axis
        b = 6356752.314245  # semi-minor axis
        e2 = 1 - (b * b) / (a * a)

        x, y, z = ecef.x, ecef.y, ecef.z

        lon = math.atan2(y, x)
        p = math.sqrt(x * x + y * y)
        lat = math.atan2(z, p * (1 - e2))

        # Iterative refine
        for _ in range(5):
            N = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
            lat = math.atan2(z + e2 * N * math.sin(lat), p)

        lat_deg = math.degrees(lat)
        lon_deg = math.degrees(lon)
        N = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
        alt = p / math.cos(lat) - N

        return Location(lat=lat_deg, lon=lon_deg, alt=alt)

    def send_fire(self, mission) -> bool:
        """Queue a Fire PDU to send.

        Args:
            mission: FireMission object.

        Returns:
            True if queued successfully.
        """
        try:
            pdu_bytes = self.fire_control.build_fire_pdu_bytes(mission)
            self._send_queue.put((pdu_bytes, None), timeout=1.0)
            return True
        except queue.Full:
            logger.warning("Send queue full, dropping Fire PDU")
            return False

    def get_stats(self) -> dict:
        """Get client statistics."""
        return dict(self._stats)

    def get_tracked_entities(self) -> List:
        """Get all tracked entities."""
        return self.tracker.get_all()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
        return False


def _ecef_to_geodetic_example():
    """Example showing ECEF to geodetic conversion."""
    import math
    # Example: A point at lat=30, lon=120, alt=0
    a = 6378137.0
    b = 6356752.314245
    e2 = 1 - (b * b) / (a * a)

    lat_rad = math.radians(30)
    lon_rad = math.radians(120)
    N = a / math.sqrt(1 - e2 * math.sin(lat_rad) ** 2)

    x = (N + 0) * math.cos(lat_rad) * math.cos(lon_rad)
    y = (N + 0) * math.cos(lat_rad) * math.sin(lon_rad)
    z = (N * (1 - e2) + 0) * math.sin(lat_rad)

    print(f"ECEF: ({x:.1f}, {y:.1f}, {z:.1f})")
    return x, y, z


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("DIS Client module - run integration test for full functionality")