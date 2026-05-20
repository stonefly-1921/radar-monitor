"""
wsf_shm_client.py
Python ctypes interface to wsf_shm.dll for writing kill chain commands.
Python writes commands → AFSIM WSF_SCRIPT_PROCESSOR reads via wsf_shm_process_new_commands()
"""
import ctypes
import os
import time
from pathlib import Path

# SHM constants (must match wsf_shm.c)
SHM_NAME = "KILL_CHAIN_SHM"
MAX_TRACKS = 256
MAX_CMDS = 256
CMD_TYPE_SENSOR = 1
CMD_TYPE_WEAPON = 2
CMD_TYPE_ENGAGE = 3
CMD_TYPE_ALLOCATE = 4

# Find wsf_shm.dll
DLL_PATHS = [
    r"C:\Users\15041\.openclaw\workspace\kill-chain-sim\src\core\wsf_shm\wsf_shm.dll",
    r"D:\afsim-2.9.0-win64\bin\wsf_shm.dll",
]
DLL_PATH = next((p for p in DLL_PATHS if os.path.exists(p)), None)


class ShmClient:
    def __init__(self, shm_name: str = SHM_NAME):
        if DLL_PATH is None:
            raise FileNotFoundError(f"wsf_shm.dll not found in {DLL_PATHS}")
        self._dll = ctypes.CDLL(DLL_PATH)
        self._name = shm_name
        self._open = False

    def create(self) -> bool:
        """Create the shared memory (call once before opening)."""
        self._dll.wsf_shm_create.argtypes = [ctypes.c_char_p]
        self._dll.wsf_shm_create.restype = ctypes.c_int
        r = self._dll.wsf_shm_create(self._name.encode('utf-8'))
        return r == 1

    def open(self) -> bool:
        """Open existing shared memory."""
        self._dll.wsf_shm_open.argtypes = [ctypes.c_char_p]
        self._dll.wsf_shm_open.restype = ctypes.c_int
        r = self._dll.wsf_shm_open(self._name.encode('utf-8'))
        self._open = r == 1
        return self._open

    def close(self):
        """Close shared memory."""
        self._dll.wsf_shm_close.argtypes = []
        self._dll.wsf_shm_close.restype = None
        self._dll.wsf_shm_close()
        self._open = False

    def set_debug(self, enable: bool) -> bool:
        """Enable/disable debug output."""
        self._dll.wsf_shm_set_debug.argtypes = [ctypes.c_int]
        self._dll.wsf_shm_set_debug.restype = ctypes.c_int
        return self._dll.wsf_shm_set_debug(1 if enable else 0) == 1

    def get_track_count(self) -> int:
        self._dll.wsf_shm_get_track_count.argtypes = []
        self._dll.wsf_shm_get_track_count.restype = ctypes.c_int
        return self._dll.wsf_shm_get_track_count()

    def get_cmd_in(self) -> int:
        self._dll.wsf_shm_get_cmd_in.argtypes = []
        self._dll.wsf_shm_get_cmd_in.restype = ctypes.c_int
        return self._dll.wsf_shm_get_cmd_in()

    def write_track(self, track_id: int, lat: float, lon: float,
                    alt_m: float, vel_mps: float, heading_deg: float) -> bool:
        """Write a track entry to SHM (AFSIM can read these)."""
        self._dll.wsf_shm_write_track.argtypes = [
            ctypes.c_uint32, ctypes.c_double, ctypes.c_double,
            ctypes.c_double, ctypes.c_double, ctypes.c_double]
        self._dll.wsf_shm_write_track.restype = ctypes.c_int
        r = self._dll.wsf_shm_write_track(
            track_id, lat, lon, alt_m, vel_mps, heading_deg)
        return r == 1

    def write_cmd(self, cmd_type: int, target_id: int,
                  param1: int, param2: int) -> bool:
        """Write a command entry to SHM (AFSIM reads via process_new_commands).

        cmd_type:
          1 = SENSOR   - param1=sensor_id, param2=mode
          2 = WEAPON   - param1=weapon_id, param2=weapon_mode
          3 = ENGAGE   - param1=interceptor_track_id, param2=target_track_id
          4 = ALLOCATE - param1=weapon_id, param2=target_track_id
        target_id: platform index or track_id depending on cmd_type
        """
        self._dll.wsf_shm_write_cmd.argtypes = [
            ctypes.c_uint8, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32]
        self._dll.wsf_shm_write_cmd.restype = ctypes.c_int
        r = self._dll.wsf_shm_write_cmd(cmd_type, target_id, param1, param2)
        return r == 1

    def clear_tracks(self) -> bool:
        return self._dll.wsf_shm_clear_tracks() == 1

    def engage(self, interceptor_track_id: int, target_track_id: int) -> bool:
        """Convenience: send ENGAGE command (type=3)."""
        return self.write_cmd(CMD_TYPE_ENGAGE, 0, interceptor_track_id, target_track_id)

    def allocate(self, weapon_id: int, target_track_id: int) -> bool:
        """Convenience: send ALLOCATE command (type=4)."""
        return self.write_cmd(CMD_TYPE_ALLOCATE, 0, weapon_id, target_track_id)


def test():
    """Quick test: create SHM, write some data, read it back."""
    client = ShmClient("TEST_SHM")

    # Create
    if not client.create():
        print("create() failed (already exists?)")
    client.open()
    client.set_debug(True)

    # Clear any old tracks
    client.clear_tracks()

    # Write tracks
    for i in range(3):
        ok = client.write_track(100 + i, 30.0 + i, 120.0 + i,
                                5000.0, 200.0, 45.0)
        print(f"write_track({100+i}): {ok}")

    # Write commands
    ok = client.write_cmd(CMD_TYPE_ENGAGE, 0, 101, 200)
    print(f"write_cmd(ENGAGE, interceptor=101, target=200): {ok}")

    ok = client.write_cmd(CMD_TYPE_ALLOCATE, 0, 5, 200)
    print(f"write_cmd(ALLOCATE, weapon=5, target=200): {ok}")

    print(f"\nTracks in SHM: {client.get_track_count()}")
    print(f"Commands in SHM: {client.get_cmd_in()}")

    client.close()
    print("Done")


if __name__ == "__main__":
    test()
