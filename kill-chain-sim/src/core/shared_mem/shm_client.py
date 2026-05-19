"""
Shared Memory Client for AFSIM Kill Chain Integration
======================================================

Reads tracks/state from AFSIM shared memory and sends commands back.
Uses memory-mapped files (mmap) on Windows for inter-process communication.

File format (64 MB total):
  [Header 128B][Tracks 64KB][Sensors 16KB][Weapons 16KB][Cmds 32KB][CmdAck 16KB][Fence 8B]
"""

import ctypes
import mmap
import os
import struct
import time
from pathlib import Path
from typing import List, Optional


# =============================================================================
# Enums (mirror C enums in shm_types.h)
# =============================================================================

class TargetType(ctypes.c_uint8):
    AIRCRAFT = 0
    MISSILE = 1
    UCAV = 2
    JAMMER = 3
    UNKNOWN = 255


class SensorMode(ctypes.c_uint8):
    OFF = 0
    STANDBY = 1
    SEARCH = 2
    TRACK = 3
    JAMMING = 4


class WeaponStatus(ctypes.c_uint8):
    READY = 0
    LAUNCHED = 1
    INTERCEPTING = 2
    DEPLETED = 3


class CmdType(ctypes.c_uint8):
    NONE = 0
    SENSOR_CONTROL = 1
    WEAPON_ASSIGN = 2
    TARGET_PRIORITY = 3
    PLATFORM_MOVE = 4


# =============================================================================
# C Structs (mirror C structs in shm_types.h)
# =============================================================================

class ShmHeader(ctypes.Structure):
    _fields_ = [
        ("magic",           ctypes.c_uint32),
        ("version",         ctypes.c_uint16),
        ("track_count",     ctypes.c_uint16),
        ("timestamp_ms",    ctypes.c_uint32),
        ("cmd_in",          ctypes.c_uint32),
        ("cmd_out",         ctypes.c_uint32),
        ("afsim_ready",     ctypes.c_uint8),
        ("padding",         ctypes.c_uint8 * 7),
        ("fence",           ctypes.c_uint64),
    ]


class TrackEntry(ctypes.Structure):
    _fields_ = [
        ("track_id",        ctypes.c_uint32),
        ("lat",             ctypes.c_double),
        ("lon",             ctypes.c_double),
        ("altitude",        ctypes.c_double),
        ("velocity",        ctypes.c_double),
        ("heading",         ctypes.c_double),
        ("timestamp_ms",    ctypes.c_double),
        ("type",            ctypes.c_uint8),
        ("force",           ctypes.c_uint8),
        ("track_quality",   ctypes.c_uint8),
        ("padding",         ctypes.c_uint16),
    ]


class SensorEntry(ctypes.Structure):
    _fields_ = [
        ("sensor_id",       ctypes.c_uint32),
        ("name",            ctypes.c_char * 24),
        ("lat",             ctypes.c_double),
        ("lon",             ctypes.c_double),
        ("altitude",        ctypes.c_double),
        ("mode",            ctypes.c_uint8),
        ("side",            ctypes.c_uint8),
        ("padding",         ctypes.c_uint8 * 6),
        ("timestamp_ms",    ctypes.c_double),
    ]


class WeaponEntry(ctypes.Structure):
    _fields_ = [
        ("weapon_id",       ctypes.c_uint32),
        ("name",            ctypes.c_char * 24),
        ("platform_id",     ctypes.c_uint32),
        ("lat",             ctypes.c_double),
        ("lon",             ctypes.c_double),
        ("altitude",        ctypes.c_double),
        ("status",          ctypes.c_uint8),
        ("side",            ctypes.c_uint8),
        ("padding",         ctypes.c_uint8 * 6),
        ("timestamp_ms",    ctypes.c_double),
    ]


class CmdEntry(ctypes.Structure):
    _fields_ = [
        ("cmd_id",          ctypes.c_uint32),
        ("type",            ctypes.c_uint8),
        ("sender_id",       ctypes.c_uint32),
        ("target_id",       ctypes.c_uint32),
        ("param1",          ctypes.c_uint32),
        ("param2",          ctypes.c_uint32),
        ("param3",          ctypes.c_double),
        ("acknowledged",    ctypes.c_uint8),
        ("padding",         ctypes.c_uint8 * 7),
        ("timestamp_ms",    ctypes.c_uint32),
    ]


# =============================================================================
# Constants
# =============================================================================

MAGIC = 0x4B494C4C          # "KILL"
FENCE_VALUE = 0xDEADBEEFDEADBEEF
MAX_TRACKS = 512
MAX_SENSORS = 256
MAX_WEAPONS = 256
MAX_CMDS = 256
HEADER_SIZE = 128
TRACK_SIZE = ctypes.sizeof(TrackEntry)       # 72 bytes
SENSOR_SIZE = ctypes.sizeof(SensorEntry)     # 64 bytes
WEAPON_SIZE = ctypes.sizeof(WeaponEntry)     # 64 bytes
CMD_SIZE = ctypes.sizeof(CmdEntry)            # 44 bytes


# =============================================================================
# Layout
# =============================================================================
# 0x00000  [Header 128B]
# 0x00080  [Tracks: 512 * 72 = 36864B]
# 0x09000  [Sensors: 256 * 64 = 16384B]
# 0x0D000  [Weapons: 256 * 64 = 16384B]
# 0x11000  [Cmds: 256 * 44 = 11264B]
# 0x13C00  [CmdAck: 256 * 44 = 11264B]
# 0x16800  [Fence 8B]

TRACKS_OFFSET = HEADER_SIZE
SENSORS_OFFSET = TRACKS_OFFSET + MAX_TRACKS * TRACK_SIZE
WEAPONS_OFFSET = SENSORS_OFFSET + MAX_SENSORS * SENSOR_SIZE
CMDS_OFFSET = WEAPONS_OFFSET + MAX_WEAPONS * WEAPON_SIZE
CMDACK_OFFSET = CMDS_OFFSET + MAX_CMDS * CMD_SIZE
SHM_SIZE = 64 * 1024 * 1024  # 64 MB


# =============================================================================
# ShmClient
# =============================================================================

class ShmClient:
    """Client for reading/writing AFSIM kill chain shared memory."""

    def __init__(self, shm_name: str = "kill_chain_shm"):
        self.shm_name = shm_name
        self.shm_path = Path(f"C:/Users/15041/.openclaw/workspace/kill-chain-sim/{shm_name}.dat")
        self.fd: Optional[int] = None
        self.mm: Optional[mmap.mmap] = None
        self._next_cmd_id = 1

    def connect(self) -> bool:
        """Connect to or create the shared memory file."""
        try:
            os.makedirs(self.shm_path.parent, exist_ok=True)
            # Try to open existing file without O_TRUNC first.
            # This avoids EINVAL when another process (e.g. TrackFileMonitor)
            # already has the file mmapped — O_TRUNC destroys the size while
            # a mmap of that same file still exists.
            try:
                self.fd = os.open(str(self.shm_path), os.O_RDWR, 0o666)
            except FileNotFoundError:
                self.fd = os.open(str(self.shm_path), os.O_RDWR | os.O_CREAT | os.O_TRUNC, 0o666)
                os.ftruncate(self.fd, SHM_SIZE)
            self.mm = mmap.mmap(self.fd, SHM_SIZE, access=mmap.ACCESS_WRITE)

            # Only write header + fence for a brand-new file.
            # For existing files, preserve whatever tracks have been written
            # (e.g. by TrackFileMonitor or a previous monitor instance).
            header = self._read_header()
            if header is None or header.magic != MAGIC:
                # Write fence marker at end
                self.mm.seek(CMDACK_OFFSET + MAX_CMDS * CMD_SIZE)
                self.mm.write(struct.pack("<Q", FENCE_VALUE))
                # Initialize header
                header = ShmHeader()
                header.magic = MAGIC
                header.version = 1
                header.track_count = 0
                header.timestamp_ms = 0
                header.cmd_in = 0
                header.cmd_out = 0
                header.afsim_ready = 0
                header.padding = (0,) * 7
                header.fence = FENCE_VALUE
                self._write_header(header)

            return True
        except Exception as e:
            print(f"ShmClient.connect failed: {e}")
            return False

    def is_valid(self) -> bool:
        """Check if shared memory has valid magic."""
        try:
            header = self._read_header()
            return header is not None and header.magic == MAGIC
        except Exception:
            return False

    def is_afsim_ready(self) -> bool:
        """Check if AFSIM has written valid data."""
        try:
            header = self._read_header()
            return header is not None and header.afsim_ready == 1
        except Exception:
            return False

    # -------------------------------------------------------------------------
    # Low-level read/write
    # -------------------------------------------------------------------------

    def _read_header(self) -> Optional[ShmHeader]:
        if not self.mm:
            return None
        try:
            self.mm.seek(0)
            data = self.mm.read(ctypes.sizeof(ShmHeader))
            return ShmHeader.from_buffer_copy(data)
        except Exception as e:
            print(f"_read_header failed: {e}")
            return None

    def _write_header(self, header: ShmHeader) -> bool:
        if not self.mm:
            return False
        try:
            self.mm.seek(0)
            self.mm.write(bytes(header))
            return True
        except Exception:
            return False

    def _read_track(self, offset: int) -> Optional[TrackEntry]:
        if not self.mm:
            return None
        try:
            self.mm.seek(offset)
            data = self.mm.read(TRACK_SIZE)
            return TrackEntry.from_buffer_copy(data)
        except Exception:
            return None

    def _write_track(self, offset: int, track: TrackEntry) -> bool:
        if not self.mm:
            return False
        try:
            self.mm.seek(offset)
            self.mm.write(bytes(track))
            return True
        except Exception:
            return False

    def _read_sensor(self, offset: int) -> Optional[SensorEntry]:
        if not self.mm:
            return None
        try:
            self.mm.seek(offset)
            data = self.mm.read(SENSOR_SIZE)
            return SensorEntry.from_buffer_copy(data)
        except Exception:
            return None

    def _read_weapon(self, offset: int) -> Optional[WeaponEntry]:
        if not self.mm:
            return None
        try:
            self.mm.seek(offset)
            data = self.mm.read(WEAPON_SIZE)
            return WeaponEntry.from_buffer_copy(data)
        except Exception:
            return None

    def _read_cmd(self, offset: int) -> Optional[CmdEntry]:
        if not self.mm:
            return None
        try:
            self.mm.seek(offset)
            data = self.mm.read(CMD_SIZE)
            return CmdEntry.from_buffer_copy(data)
        except Exception:
            return None

    def _write_cmd(self, offset: int, cmd: CmdEntry) -> bool:
        if not self.mm:
            return False
        try:
            self.mm.seek(offset)
            self.mm.write(bytes(cmd))
            return True
        except Exception:
            return False

    # -------------------------------------------------------------------------
    # High-level API
    # -------------------------------------------------------------------------

    def get_tracks(self) -> List[TrackEntry]:
        """Read all active tracks from shared memory."""
        tracks = []
        try:
            header = self._read_header()
            if not header or header.magic != MAGIC:
                return []
            count = min(header.track_count, MAX_TRACKS)
            for i in range(count):
                track = self._read_track(TRACKS_OFFSET + i * TRACK_SIZE)
                if track and track.track_id != 0:
                    tracks.append(track)
            return tracks
        except Exception as e:
            print(f"get_tracks failed: {e}")
            return []

    def get_sensors(self) -> List[SensorEntry]:
        """Read all sensor states."""
        sensors = []
        try:
            header = self._read_header()
            if not header or header.magic != MAGIC:
                return []
            count = min(header.track_count, MAX_SENSORS)
            for i in range(count):
                sensor = self._read_sensor(SENSORS_OFFSET + i * SENSOR_SIZE)
                if sensor and sensor.sensor_id != 0:
                    sensors.append(sensor)
            return sensors
        except Exception as e:
            print(f"get_sensors failed: {e}")
            return []

    def get_weapons(self) -> List[WeaponEntry]:
        """Read all weapon states."""
        weapons = []
        try:
            header = self._read_header()
            if not header or header.magic != MAGIC:
                return []
            count = min(header.track_count, MAX_WEAPONS)
            for i in range(count):
                weapon = self._read_weapon(WEAPONS_OFFSET + i * WEAPON_SIZE)
                if weapon and weapon.weapon_id != 0:
                    weapons.append(weapon)
            return weapons
        except Exception as e:
            print(f"get_weapons failed: {e}")
            return []

    def send_sensor_control(self, sensor_id: int, mode: SensorMode) -> bool:
        """Send SENSOR_CONTROL command to AFSIM."""
        cmd = CmdEntry()
        cmd.cmd_id = self._next_cmd_id
        self._next_cmd_id += 1
        cmd.type = CmdType.SENSOR_CONTROL
        cmd.sender_id = 0  # Python
        cmd.target_id = 0
        cmd.param1 = sensor_id
        cmd.param2 = int(mode)
        cmd.param3 = 0.0
        cmd.acknowledged = 0
        cmd.padding = (0,) * 7
        cmd.timestamp_ms = int(time.time() * 1000) & 0xFFFFFFFF
        return self._queue_command(cmd)

    def send_weapon_assign(self, weapon_id: int, track_id: int, priority: float) -> bool:
        """Send WEAPON_ASSIGN command to AFSIM."""
        cmd = CmdEntry()
        cmd.cmd_id = self._next_cmd_id
        self._next_cmd_id += 1
        cmd.type = CmdType.WEAPON_ASSIGN
        cmd.sender_id = 0
        cmd.target_id = track_id
        cmd.param1 = weapon_id
        cmd.param2 = 0
        cmd.param3 = priority
        cmd.acknowledged = 0
        cmd.padding = (0,) * 7
        cmd.timestamp_ms = int(time.time() * 1000) & 0xFFFFFFFF
        return self._queue_command(cmd)

    def send_target_priority(self, track_id: int, priority: float) -> bool:
        """Send TARGET_PRIORITY command to AFSIM."""
        cmd = CmdEntry()
        cmd.cmd_id = self._next_cmd_id
        self._next_cmd_id += 1
        cmd.type = CmdType.TARGET_PRIORITY
        cmd.sender_id = 0
        cmd.target_id = track_id
        cmd.param1 = 0
        cmd.param2 = 0
        cmd.param3 = priority
        cmd.acknowledged = 0
        cmd.padding = (0,) * 7
        cmd.timestamp_ms = int(time.time() * 1000) & 0xFFFFFFFF
        return self._queue_command(cmd)

    def _queue_command(self, cmd: CmdEntry) -> bool:
        """Write command to shared memory command queue."""
        try:
            header = self._read_header()
            if not header:
                return False
            idx = header.cmd_in % MAX_CMDS
            offset = CMDS_OFFSET + idx * CMD_SIZE
            if not self._write_cmd(offset, cmd):
                return False
            header.cmd_in += 1
            self._write_header(header)
            return True
        except Exception as e:
            print(f"_queue_command failed: {e}")
            return False

    def poll_command_ack(self, cmd_id: int, timeout_ms: int = 5000) -> bool:
        """Poll for command acknowledgment."""
        start = time.time() * 1000
        while (time.time() * 1000 - start) < timeout_ms:
            try:
                header = self._read_header()
                if not header:
                    break
                # Check all pending acks
                for i in range(MAX_CMDS):
                    offset = CMDS_OFFSET + i * CMD_SIZE
                    cmd = self._read_cmd(offset)
                    if cmd and cmd.cmd_id == cmd_id and cmd.acknowledged == 1:
                        return True
                time.sleep(0.01)
            except Exception:
                break
        return False

    def close(self) -> None:
        """Close shared memory connection."""
        if self.mm:
            try:
                self.mm.close()
            except Exception:
                pass
            self.mm = None
        if self.fd is not None:
            try:
                os.close(self.fd)
            except Exception:
                pass
            self.fd = None


# =============================================================================
# Helpers
# =============================================================================

def track_to_dict(t: TrackEntry) -> dict:
    """Convert TrackEntry to dict for convenience."""
    return {
        "track_id": t.track_id,
        "lat": t.lat,
        "lon": t.lon,
        "altitude": t.altitude,
        "velocity": t.velocity,
        "heading": t.heading,
        "timestamp_ms": t.timestamp_ms,
        "type": t.type,
        "force": t.force,
        "track_quality": t.track_quality,
    }