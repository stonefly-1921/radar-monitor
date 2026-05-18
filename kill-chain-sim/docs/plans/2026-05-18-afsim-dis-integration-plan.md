# AFSIM DIS Real-Time Integration Plan
**Date:** 2026-05-18
**Project:** kill-chain-sim
**Status:** Planning

---

## Problem Statement

AFSIM is running (`mission.exe -rt kill_chain_scenario.txt`) and Python DIS client (`src/main.py`) is listening on UDP `235.7.11.27:3002`. AFSIM sends **Signal PDUs (type=4, entity 1:1:25)** but **NO Entity State PDUs (type=1)**. The Python `EntityTracker` is always empty, so MILP allocation never runs.

**Known root causes:**
1. `xio_interface` uses `auto_dis_mapping yes` — AFSIM's internal DIS mapping may suppress standard Entity State PDUs
2. Exercise ID mismatch: AFSIM PDUs use `exercise_id=0`, Python client defaults to `exercise_id=1`
3. Signal PDUs carry ESM data (96 bytes each) but no entity position data

---

## Task A: Diagnose AFSIM Entity State PDU Output

### Problem
AFSIM is not sending Entity State PDUs. Likely causes:
- `auto_dis_mapping yes` in xio_interface bypasses standard DIS Entity State output
- `dis_interface application 2` set but exercise ID defaults to 0 (not 1)

### Steps

**A1. Inspect kill_chain_scenario.txt and related includes**

```bash
# Verify scenario DIS/xio configuration
cat src/sim/kill_chain_scenario.txt
cat D:/afsim-2.9.0-win64/demos/iads/xio_interface.txt
```

**A2. Add dis_interface force-entity-state output**

Modify `src/sim/kill_chain_scenario.txt` — add explicit DIS settings under `dis_interface` to force Entity State output:

```
dis_interface
   application 2
   exercise_id 0        # ← Add this (AFSIM uses 0)
   entity_state_filter 1 # ← Attempt to force Entity State output
end_dis_interface
```

Alternatively, try adding `include D:/afsim-2.9.0-win64/demos/iads/dis_realtime.txt` (as noted in the scenario, it was removed).

**A3. Write a test to capture raw PDUs and log pdu_type distribution**

Create `tests/integration/test_afsim_pdu_capture.py`:

```python
"""Capture and analyze raw PDUs from AFSIM for 10 seconds."""
import socket, time, struct

def test_afsim_pdu_capture():
    """Test: receive PDUs for 10s and report type distribution."""
    multicast_addr = "235.7.11.27"
    port = 3002
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', port))
    mreq = struct.pack("4s4s", bytes(map(int, multicast_addr.split('.'))), b'\x00\x00\x00\x00')
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    sock.settimeout(0.5)
    
    pdu_types = {}
    start = time.time()
    while time.time() - start < 10:
        try:
            data, addr = sock.recvfrom(2048)
            if len(data) >= 4:
                pdu_type = data[3]
                exercise_id = data[2]
                pdu_types[pdu_type] = pdu_types.get(pdu_type, 0) + 1
                print(f"RX type={pdu_type} exercise={exercise_id} size={len(data)}")
        except socket.timeout:
            continue
    
    print(f"PDU distribution: {pdu_types}")
    assert pdu_types, "No PDUs received from AFSIM"
    # Verify Signal PDUs received
    assert 4 in pdu_types, "No Signal PDUs received"
```

**A4. Run test and verify results**

```bash
cd kill-chain-sim
python -m tests.integration.test_afsim_pdu_capture
```

**Expected output:**
- Signal PDUs (type=4) received from entity 1:1:25
- Entity State PDUs (type=1) — either present (fix works) or absent (confirm fallback needed)
- Exercise ID = 0 for all PDUs (confirms AFSIM default)

**A5. Fix exercise ID mismatch in Python client**

If AFSIM uses exercise_id=0, update `src/main.py` argument default:
```python
parser.add_argument('--exercise-id', type=int, default=0,
                   help='DIS exercise ID (default: 0 for AFSIM)')
```

Also update `src/core/dis/fire_control.py` — FireControl constructor must accept and use the correct exercise_id for Fire PDU headers.

### Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `tests/integration/test_afsim_pdu_capture.py` | Create | Capture raw PDUs, analyze type distribution |
| `src/sim/kill_chain_scenario.txt` | Modify | Add `exercise_id 0`, try forcing Entity State output |
| `src/main.py` | Modify | Change default `--exercise-id` from 1 to 0 |
| `src/core/dis/fire_control.py` | Modify | Pass correct exercise_id into PDU header |

### Verification
- `test_afsim_pdu_capture` shows non-zero Entity State PDUs received, OR confirms type=4 only
- Exercise ID in captured PDUs matches what AFSIM sends (0)
- `EntityTracker.count() > 0` after 10 seconds of AFSIM running

---

## Task B: Implement Signal-PDU-Driven Simulation Fallback

### Problem
If AFSIM genuinely does not send Entity State PDUs (confirmed by Task A), implement a simulation mode where:
- Signal PDUs detect/track entities via ESM geolocation
- A built-in trajectory simulator generates virtual tracks from ESM reports
- Tracks are fed to MILP allocator the same way as real tracks

### Steps

**B1. Write failing test first — signal-driven tracking test**

Create `tests/unit/test_esm_trajectory_tracker.py`:

```python
"""Test that Signal PDUs can drive entity tracking via ESM geolocation."""
import unittest
from src.core.dis.dis_protocol import EntityId, SignalPdu
from src.core.dis.esm_client import EsmClient
from src.core.dis.esm_trajectory_tracker import EsmTrajectoryTracker

class TestEsmTrajectoryTracker(unittest.TestCase):
    def test_signal_pdu_creates_track(self):
        """Test: given Signal PDUs with bearing data, a virtual track is created."""
        tracker = EsmTrajectoryTracker()
        
        # Simulate 3 Signal PDUs from the same emitter with different bearings
        eid = EntityId(1, 1, 25)
        
        reports = [
            # (radio_id, frequency, bearing_deg, signal_strength_dbm)
            (1, 3e9, 45.0, -60.0),
            (1, 3e9, 50.0, -55.0),
            (1, 3e9, 55.0, -50.0),
        ]
        
        for bearing in [45.0, 50.0, 55.0]:
            pdu = SignalPdu(
                entity_id=eid,
                radio_id=1,
                encoding_scheme=0, tdl_type=0, sample_rate=1000,
                number_of_samples=1,
                data=build_esm_data_bytes(frequency=3e9, bearing=bearing, strength=-60)
            )
            result = tracker.process_signal_pdu(pdu, sim_time=0.0)
            tracker.run_trajectory_estimation()
        
        # After 3 reports, a virtual track should exist
        tracks = tracker.get_virtual_tracks()
        self.assertGreaterEqual(len(tracks), 1, 
            "EsmTrajectoryTracker should create virtual track from 3+ ESM reports")
```

**B2. Implement EsmTrajectoryTracker class**

Create `src/core/dis/esm_trajectory_tracker.py`:

```python
"""ESM Trajectory Tracker - Generate virtual tracks from Signal/ESM PDUs.

When Entity State PDUs are unavailable, this module uses:
- Multiple Signal PDUs with bearing data ( emitter geolocation via triangulation)
- Built-in trajectory simulator to project entity positions
- Feeds virtual tracks to the MILP allocator
```

The class should:
1. Maintain a list of ESM reports per emitter (from EsmClient)
2. Run triangulation when ≥3 bearing reports received from same emitter
3. Project trajectory using constant velocity model
4. Produce virtual `TrackedEntity` objects fed to `EntityTracker`
5. Expose `get_virtual_tracks()` method

**B3. Write mock Signal PDU test**

Create `tests/unit/test_signal_pdu_fallback.py`:

```python
"""Test Signal PDU fallback mode with mock ESM data."""
def test_allocation_from_signal_pdu_fallback():
    """Test: given Signal PDUs, EsmTrajectoryTracker produces tracks, 
    and MILP allocator runs successfully."""
    from src.core.dis.esm_trajectory_tracker import EsmTrajectoryTracker
    from src.research.algorithms.milp_allocator import MilpAllocator, Target, Sensor, Weapon
    
    tracker = EsmTrajectoryTracker()
    
    # Feed mock Signal PDUs representing a moving aircraft emitting ESM
    # ... (inject 5 Signal PDUs at different times with bearing changes)
    
    tracks = tracker.get_virtual_tracks()
    assert len(tracks) >= 1, "Should have virtual track from ESM"
    
    # Verify allocation runs without error
    allocator = MilpAllocator(time_limit_sec=5)
    targets = [Target(t.track_id, t.priority, t.velocity_kts, t.type, 
                      t.lat, t.lon, t.altitude_ft, t.range_to_sensors)
               for t in tracks]
    sensors = [Sensor(1, 150, "track", 60, 30)]
    weapons = [Weapon(1, 600, 0.8, 600, "sam")]
    
    result = allocator.solve(targets, sensors, weapons)
    assert result is not None, "MILP allocation should complete"
```

**B4. Integrate EsmTrajectoryTracker into DisClient**

Modify `src/core/dis/dis_client.py` — add optional mode where:
- `_auto_track` remains True for Entity State PDUs
- If only Signal PDUs arrive and no Entity State for N seconds, `EsmTrajectoryTracker` is activated
- Virtual tracks are added to the same `EntityTracker` instance

### Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `src/core/dis/esm_trajectory_tracker.py` | Create | Generate virtual tracks from ESM/Signal PDUs |
| `tests/unit/test_esm_trajectory_tracker.py` | Create | TDD test for ESM trajectory tracking |
| `tests/unit/test_signal_pdu_fallback.py` | Create | End-to-end mock Signal PDU test |
| `src/core/dis/dis_client.py` | Modify | Integrate EsmTrajectoryTracker as fallback |
| `src/core/dis/entity_tracker.py` | Modify | Support adding virtual/derived tracks |

### Verification
- `test_signal_pdu_creates_track` passes (virtual track created from mock Signal PDUs)
- `test_allocation_from_signal_pdu_fallback` passes (allocation runs with virtual tracks)
- `python -m src.main --exercise-id 0` shows `EntityTracker.count() > 0` after 10s (using either real Entity State or ESM fallback)

---

## Task C: Verify Fire PDU Delivery to AFSIM

### Problem
After entity tracking is fixed, Fire PDUs must be correctly formed and delivered to AFSIM. Known issue: FireControl uses `exercise_id=1` but AFSIM expects `exercise_id=0`.

### Steps

**C1. Write failing test — Fire PDU wire capture**

Create `tests/unit/test_fire_pdu_exercise_id.py`:

```python
"""Test Fire PDU exercise_id matches AFSIM expectations."""
import unittest
from src.core.dis.dis_protocol import EntityId
from src.core.dis.fire_control import FireControl

class TestFirePduExerciseId(unittest.TestCase):
    def test_fire_pdu_exercise_id_zero(self):
        """Test: Fire PDU built with exercise_id=0 matches AFSIM."""
        fc = FireControl(exercise_id=0)
        mission = fc.create_fire_mission(
            launcher_id=EntityId(25, 1, 1),
            target_id=EntityId(25, 1, 10),
            Munition_id=EntityId(25, 1, 99)
        )
        pdu_bytes = fc.build_fire_pdu_bytes(mission)
        
        # PDU header: timestamp(4) + version(1) + exercise(1) + type(1) + family(1) + length(2) + padding(2)
        exercise_id_in_pdu = pdu_bytes[5]  # offset after 4-byte timestamp
        self.assertEqual(exercise_id_in_pdu, 0,
            f"Fire PDU exercise_id should be 0, got {exercise_id_in_pdu}")
    
    def test_fire_pdu_sent_to_wire(self):
        """Test: Fire PDU bytes appear on wire (socket send capture)."""
        import socket, threading
        
        sent_packets = []
        def capture_thread():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', 3003))  # Separate port for capture
            mreq = struct.pack("4s4s", socket.inet_aton("235.7.11.27"), b'\x00\x00\x00\x00')
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            data, _ = sock.recvfrom(2048)
            sent_packets.append(data)
        
        # NOTE: This test requires running main.py and capturing output
        # Full e2e test is in Task D
```

**C2. Fix FireControl exercise_id**

`src/core/dis/fire_control.py` — `build_fire_pdu_bytes` uses `self.exercise_id` in the header packing. Verify the constructor sets `self.exercise_id = exercise_id` (not always 1).

Current code (dis_protocol.py): `EXERCISE_ID_DEFAULT = 1`  
Current FireControl: `def __init__(self, exercise_id: int = EXERCISE_ID_DEFAULT)` — this is correct.

The issue: `DisClient` creates `FireControl(exercise_id=exercise_id)` where `exercise_id` comes from `main.py` args (default 1). Fix by passing the correct exercise_id from main.py.

**C3. Write test sending Fire PDU and capturing on wire**

Create `tests/integration/test_fire_pdu_wire_capture.py`:

```python
"""Capture Fire PDU sent to network to verify it is well-formed on wire."""
import socket, struct, time, threading

def test_fire_pdu_wire_capture():
    """Test Fire PDU appears on wire with correct structure."""
    # Start a capture socket on same multicast group
    capture_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    capture_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    capture_sock.bind(('', 3002))
    mreq = struct.pack("4s4s", socket.inet_aton("235.7.11.27"), b'\x00\x00\x00\x00')
    capture_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    capture_sock.settimeout(2.0)
    
    # Send a Fire PDU
    from src.core.dis.fire_control import FireControl
    from src.core.dis.dis_protocol import EntityId
    
    fc = FireControl(exercise_id=0)
    mission = fc.create_fire_mission(
        launcher_id=EntityId(25, 1, 1),
        target_id=EntityId(25, 1, 10),
        Munition_id=EntityId(25, 1, 99)
    )
    pdu_bytes = fc.build_fire_pdu_bytes(mission)
    
    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    send_sock.sendto(pdu_bytes, ("235.7.11.27", 3002))
    
    # Capture
    data, addr = capture_sock.recvfrom(2048)
    assert len(data) >= 6, "Should receive Fire PDU on wire"
    assert data[3] == 2, "PDU type should be 2 (Fire)"
    assert data[2] == 0, "Exercise ID should be 0"
    print(f"Fire PDU captured: type={data[3]} exercise={data[2]} size={len(data)}")
```

**C4. Verify exercise_id=0 for all DIS operations**

Review all DIS PDU building code:
- `FirePdu.encode()` — no exercise_id field (it's in the header only)
- `EntityStatePdu`, `DetonationPdu` — same pattern (exercise_id in header only)
- Verify `DisClient.fire_control = FireControl(exercise_id=self.exercise_id)` — `self.exercise_id` comes from DisClient constructor which defaults to 1, not the main.py corrected value

### Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `tests/unit/test_fire_pdu_exercise_id.py` | Create | Verify Fire PDU exercise_id |
| `tests/integration/test_fire_pdu_wire_capture.py` | Create | Capture Fire PDU on wire |
| `src/core/dis/dis_client.py` | Modify | Pass correct exercise_id to FireControl |
| `src/main.py` | Modify | Change default exercise_id to 0 |

### Verification
- `test_fire_pdu_exercise_id_zero` passes
- `test_fire_pdu_wire_capture` shows type=2, exercise=0 PDU on wire
- Wireshark/tshark capture confirms Fire PDU sent to `235.7.11.27:3002`

---

## Task D: End-to-End Integration Test

### Problem
No automated end-to-end test exists that:
1. Starts AFSIM as subprocess
2. Starts Python main.py
3. Verifies the full kill chain pipeline runs

### Steps

**D1. Write failing integration test**

Create `tests/integration/test_kill_chain_integration.py`:

```python
"""End-to-end integration test for AFSIM DIS real-time kill chain."""
import subprocess, time, socket, struct, threading, sys, os

def test_afsim_dis_e2e():
    """Full kill chain: AFSIM → Python DIS client → MILP → Fire PDU → AFSIM Detonation."""
    
    AFSIM_PATH = "D:/afsim-2.9.0-win64/bin/mission.exe"
    SCENARIO = "src/sim/kill_chain_scenario.txt"
    PYTHON_MAIN = "src/main.py"
    
    # Check prerequisites
    if not os.path.exists(AFSIM_PATH):
        pytest.skip(f"AFSIM not found at {AFSIM_PATH}")
    
    # 1. Start AFSIM subprocess
    afsim_proc = subprocess.Popen(
        [AFSIM_PATH, "-rt", SCENARIO],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        cwd=os.path.dirname(AFSIM_PATH)
    )
    
    # 2. Start Python DIS client
    python_proc = subprocess.Popen(
        [sys.executable, "-m", "src.main", "--exercise-id", "0", "--verbose"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        cwd=os.path.dirname(__file__) + "/../.."
    )
    
    # 3. Capture PDUs for 30 seconds
    capture_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    capture_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    capture_sock.bind(('', 3002))
    mreq = struct.pack("4s4s", socket.inet_aton("235.7.11.27"), b'\x00\x00\x00\x00')
    capture_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    capture_sock.settimeout(1.0)
    
    pdu_types = {}
    fire_pdus_sent = 0
    
    start_time = time.time()
    while time.time() - start_time < 30:
        try:
            data, addr = capture_sock.recvfrom(2048)
            if len(data) >= 4:
                pdu_type = data[3]
                pdu_types[pdu_type] = pdu_types.get(pdu_type, 0) + 1
                if pdu_type == 2:
                    fire_pdus_sent += 1
        except socket.timeout:
            continue
    
    # 4. Cleanup
    python_proc.terminate()
    afsim_proc.terminate()
    python_proc.wait(timeout=5)
    afsim_proc.wait(timeout=5)
    
    # 5. Verify results
    print(f"PDU distribution: {pdu_types}")
    
    # Either Entity State PDUs received (primary mode) or Signal PDUs (fallback mode)
    assert 4 in pdu_types, "No Signal PDUs received from AFSIM"
    assert pdu_types[4] > 0, "AFSIM should send Signal PDUs"
    
    # Tracker should have tracked something (Entity State mode OR ESM fallback)
    # We can't directly check tracker count, but we check that allocation ran
    # by looking for Fire PDUs or process output
    
    print(f"Fire PDUs sent: {fire_pdus_sent}")
    print(f"Total PDUs: {sum(pdu_types.values())}")
    
    # PASS condition: at least Signal PDUs received (AFSIM is talking)
    assert sum(pdu_types.values()) > 0, "No PDUs received at all"
```

**D2. Create test environment configuration**

Create `tests/integration/conftest.py`:

```python
"""Pytest configuration for integration tests."""
import os, pytest

@pytest.fixture(scope="session")
def afsim_path():
    path = "D:/afsim-2.9.0-win64/bin/mission.exe"
    if not os.path.exists(path):
        pytest.skip("AFSIM not installed")
    return path

@pytest.fixture(scope="session")
def scenario_path():
    path = "src/sim/kill_chain_scenario.txt"
    if not os.path.exists(path):
        pytest.skip("Scenario file not found")
    return path
```

**D3. Implement integration test with subprocess management**

The test above is simplified. A more robust version should:
1. Use `threading.Event` to signal when AFSIM is ready (check mission.log)
2. Parse `python_proc.stdout` for allocation confirmation
3. Handle Windows-specific process termination
4. Add timeout watchdog thread
5. Provide detailed failure diagnostics

**D4. Run integration test with AFSIM**

```bash
cd kill-chain-sim
python -m pytest tests/integration/test_kill_chain_integration.py -v -s
```

**D5. Verify Detonation PDU reception**

After Fire PDUs are sent to AFSIM, we expect Detonation PDUs back. Add verification:

```python
assert 3 in pdu_types, "No Detonation PDU received after Fire commands"
```

### Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `tests/integration/test_kill_chain_integration.py` | Create | E2E test for full kill chain |
| `tests/integration/conftest.py` | Create | Pytest fixtures for integration tests |
| `docs/plans/2026-05-18-test-matrix.md` | Create | Test matrix documenting all test cases |

### Verification
- Test completes in ≤45 seconds (30s capture + startup/shutdown)
- `pdu_types[4] > 0` — Signal PDUs received (AFSIM talking)
- `pdu_types[1] > 0` — Entity State PDUs received (primary mode working) OR test uses ESM fallback
- Fire PDUs (type=2) sent by Python client appear in capture
- Detonation PDUs (type=3) received confirming engagement

---

## Summary: Test-Driven Implementation Order

| Order | Task | Test File | Success Criteria |
|-------|------|-----------|-------------------|
| 1 | A1-A3: PDU capture diagnosis | `test_afsim_pdu_capture.py` | Confirms PDU types from AFSIM |
| 2 | A4-A5: Fix exercise ID | `test_fire_pdu_exercise_id.py` | Fire PDU has exercise_id=0 |
| 3 | B1: ESM trajectory tracker TDD | `test_esm_trajectory_tracker.py` | Virtual track from Signal PDUs |
| 4 | B2: Implement EsmTrajectoryTracker | `esm_trajectory_tracker.py` | TDD test passes |
| 5 | B3: Integration with DisClient | `test_signal_pdu_fallback.py` | Allocation runs from ESM |
| 6 | C3: Fire PDU wire capture | `test_fire_pdu_wire_capture.py` | Fire PDU on wire, correct header |
| 7 | D1-D5: E2E integration | `test_kill_chain_integration.py` | Full pipeline works end-to-end |

---

## Known Issues to Address During Implementation

1. **`auto_dis_mapping yes` in xio_interface** — This is the likely reason Entity State PDUs are suppressed. Try setting `auto_dis_mapping no` or remove it to force AFSIM to use standard DIS output.

2. **Exercise ID mismatch** — AFSIM uses 0, Python expects 1. Fix defaults in main.py and verify FireControl receives correct value.

3. **Signal PDU data format** — ESM data from AFSIM Signal PDUs uses variable datum records (0x01-0x05 IDs). Ensure EsmClient parsing handles AFSIM's actual datum format (may differ from spec).

4. **Entity ID mapping** — AFSIM entity IDs in Signal PDUs (1:1:25) differ from the normalized ID scheme (25:1:X). EsmTrajectoryTracker should use the raw EntityId until Entity State PDUs arrive to provide the mapping.

5. **Shared memory alternative** — The codebase also supports UCS/shared memory for AFSIM communication. If DIS fails completely, fall back to `src/core/shared_mem/shm_client.cpp` which bypasses DIS entirely.

---

## Appendix: DIS PDU Format Reference

```
PDU Header (14 bytes total):
  Offset 0-3:   Timestamp (4 bytes) — DIS format: hours(1) + time(4)
  Offset 4:     Protocol Version (1 byte) — should be 6
  Offset 5:     Exercise ID (1 byte) — 0 or 1
  Offset 6:     PDU Type (1 byte) — 1=Entity State, 2=Fire, 3=Detonation, 4=Signal
  Offset 7:     Family (1 byte) — 1=warfare/entity management
  Offset 8-9:   Length (2 bytes) — total PDU length
  Offset 10-11: Padding (2 bytes)

Signal PDU Data (96 bytes ESM):
  Variable datum records with datum_id + datum_length + value

Entity State PDU Body:
  Entity ID (6 bytes) + Entity Type (8 bytes) + Location (24 bytes) + 
  Orientation (12 bytes) + Velocity (12 bytes) + dead reckoning (9 bytes) + ...
```