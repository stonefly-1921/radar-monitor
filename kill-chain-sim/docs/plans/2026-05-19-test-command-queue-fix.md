# Kill Chain Sim — test_command_queue Fix & Shared Memory Test Isolation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the failing `test_command_queue` test and establish shared-memory test isolation so tests do not interfere with each other's state.

**Architecture:** The shared memory implementation uses memory-mapped files on Windows. The test file `test_kill_chain_shm.dat` persists on disk between test runs, so `cmd_in` accumulates across runs. Fix is a targeted `reinitialize_shm()` helper that resets header counters and clears command slots without destroying the mmap.

**Tech Stack:** Python 3.12, ctypes, mmap, pytest

---

## Chunk 1: Fix test_command_queue — Reset command queue state before test assertions

**Files:**
- Modify: `tests/unit/test_shm_client.py:74-106`
- Test: `tests/unit/test_shm_client.py::test_command_queue`

---

- [ ] **Step 1: Add a reinitialize helper to ShmClient**

In `src/core/shared_mem/shm_client.py`, add this method to `ShmClient`:

```python
def reinitialize(self) -> bool:
    """Re-initialize header counters to zero without closing mmap.

    Use this to reset cmd_in/cmd_out before a test that expects
    a clean command queue, without destroying data already written
    by other processes (e.g. TrackFileMonitor).
    """
    try:
        header = self._read_header()
        if not header:
            return False
        header.cmd_in = 0
        header.cmd_out = 0
        # Clear the command queue slots
        for i in range(MAX_CMDS):
            offset = CMDS_OFFSET + i * CMD_SIZE
            self.mm.seek(offset)
            self.mm.write(b'\x00' * CMD_SIZE)
        self._write_header(header)
        return True
    except Exception as e:
        print(f"reinitialize failed: {e}")
        return False
```

Run: `python -c "from src.core.shared_mem.shm_client import ShmClient; c=ShmClient('test_kill_chain_shm'); c.connect(); print(c.reinitialize()); c.close()"`  
Expected: `True`

---

- [ ] **Step 2: Modify test_command_queue to reinitialize before assertions**

In `tests/unit/test_shm_client.py`, update `test_command_queue()` around line 74:

```python
def test_command_queue():
    """Test sending a command and getting acknowledgment."""
    client = ShmClient("test_kill_chain_shm")
    assert client.connect()

    # Reset command queue to clean state before this test
    assert client.reinitialize(), "reinitialize failed"

    # Queue a sensor control command
    sensor_id = 100
    mode = SensorMode.TRACK
    result = client.send_sensor_control(sensor_id, mode)
    assert result, "send_sensor_control returned False"

    # Read the queued command
    header = client._read_header()
    assert header.cmd_in == 1, f"cmd_in={header.cmd_in}, expected 1"
    idx = (header.cmd_in - 1) % MAX_CMDS
    cmd = client._read_cmd(CMDS_OFFSET + idx * CMD_SIZE)

    assert cmd.cmd_id == 1
    assert cmd.type == CmdType.SENSOR_CONTROL
    assert cmd.param1 == sensor_id
    assert cmd.param2 == int(mode)
    assert cmd.acknowledged == 0

    # Acknowledge it (simulate AFSIM response)
    cmd.acknowledged = 1
    client._write_cmd(CMDS_OFFSET + idx * CMD_SIZE, cmd)

    # Poll for ack
    ack = client.poll_command_ack(1, timeout_ms=500)
    assert ack, "poll_command_ack timed out"

    client.close()
    print("PASS: test_command_queue")
```

---

- [ ] **Step 3: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_shm_client.py::test_command_queue -v`  
Expected: `PASS`

---

- [ ] **Step 4: Run all shm_client tests to ensure no regression**

Run: `python -m pytest tests/unit/test_shm_client.py -v`  
Expected: All 6 tests PASS

---

- [ ] **Step 5: Commit**

```bash
git add src/core/shared_mem/shm_client.py tests/unit/test_shm_client.py
git commit -m "fix: reset cmd queue in test_command_queue to fix persistent state failure

The test .dat file accumulates cmd_in across test runs. Added reinitialize()
helper to reset header counters and clear command slots before test assertions.
Also fixes assert message to show actual cmd_in value on failure."
```

---

## Chunk 2: Add session-scoped pytest fixture for shared memory isolation

**Files:**
- Modify: `tests/unit/test_shm_client.py:1-170`

---

- [ ] **Step 1: Add pytest fixture at module level**

At the top of `tests/unit/test_shm_client.py`, add:

```python
import pytest

@pytest.fixture(scope="module")
def clean_shm_client():
    """Provide a ShmClient connected to a clean shared memory state.

    Resets cmd_in/cmd_out before any tests run, so each test starts
    from a known-clean queue regardless of prior test runs.
    """
    client = ShmClient("test_kill_chain_shm")
    if not client.connect():
        pytest.fail("Failed to connect to shared memory")
    client.reinitialize()
    yield client
    client.close()
```

Update `test_shm_creation` through `test_weapon_assign_command` to accept the fixture as a parameter instead of creating their own client. For example:

```python
def test_shm_creation(clean_shm_client):
    """Test that we can create and connect to shared memory."""
    client = clean_shm_client
    assert client.is_valid(), "Invalid magic after connect"
    # ... rest unchanged
```

This ensures all tests share the same reinitialized client rather than each creating their own connections.

---

- [ ] **Step 2: Run full test suite**

Run: `python -m pytest tests/unit/test_shm_client.py -v`  
Expected: All 6 PASS

---

- [ ] **Step 3: Run all unit tests**

Run: `python -m pytest tests/unit/ -v --tb=short`  
Expected: 104 passed, 0 failed

---

- [ ] **Step 4: Commit**

```bash
git add tests/unit/test_shm_client.py
git commit -m "test: add session-scoped clean_shm_client fixture for test isolation

All shm_client tests now share a reinitialized client, preventing
interference from residual cmd_in state across test runs."
```

---

## Verification Command

After all chunks complete, run:

```bash
python -m pytest tests/unit/ -v --tb=short
```

Expected output:
```
=========================== 104 passed in X.XXs ============================
```