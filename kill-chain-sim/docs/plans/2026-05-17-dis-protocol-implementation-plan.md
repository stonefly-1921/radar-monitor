# DIS Protocol Interface - Implementation Plan

> **For implementer:** Use TDD throughout. Write failing test first. Watch it fail. Then implement.

**Goal:** Build Python DIS client for bidirectional communication with AFSIM over UDP multicast.

**Architecture:** Async multi-threaded — receive thread + processing queue + send queue + main loop.

**Scope:** Full bidirectional DIS (Entity State, Fire, Detonation, Signal PDUs).

---

## Task 1: DIS PDU Protocol Definitions

**Goal:** Create DIS PDU structures and constants.

**Files:**
- Create: `src/core/dis/dis_protocol.py`

**Step 1: Write the unit test**
```python
import unittest
from dis_protocol import DisPdu, EntityStatePdu, FirePdu, DetonationPdu, SignalPdu

class TestDisProtocol(unittest.TestCase):
    def test_pdu_header_size(self):
        """PDU Header is 12 bytes (without padding)."""
        self.assertEqual(DisPdu.HEADER_SIZE, 12)
    
    def test_entity_state_pdu_type(self):
        """Entity State PDU type is 0x01."""
        self.assertEqual(EntityStatePdu.PDU_TYPE, 0x01)
    
    def test_fire_pdu_type(self):
        """Fire PDU type is 0x02."""
        self.assertEqual(FirePdu.PDU_TYPE, 0x02)
    
    def test_detonation_pdu_type(self):
        """Detonation PDU type is 0x03."""
        self.assertEqual(DetonationPdu.PDU_TYPE, 0x03)
    
    def test_signal_pdu_type(self):
        """Signal PDU type is 0x04."""
        self.assertEqual(SignalPdu.PDU_TYPE, 0x04)
```

**Step 2: Run test — confirm it fails**
```
python -m pytest tests/unit/test_dis_protocol.py -v
```
Expected: FAIL — module not found

**Step 3: Write implementation**
Define:
- PDU type constants (ENTITY_STATE=1, FIRE=2, DETONATION=3, SIGNAL=4)
- Entity ID structure (site, application, entity)
- PDU header struct (protocol_version, exercise_id, pdu_type, family, timestamp, length, padding)
-各 PDU 类型的字段定义

**Step 4: Run test — confirm it passes**

**Step 5: Commit**
```
git add src/core/dis/dis_protocol.py tests/unit/test_dis_protocol.py
git commit -m "feat: add DIS protocol PDU definitions"
```

---

## Task 2: DIS Socket (UDP Multicast)

**Goal:** Create UDP socket wrapper for DIS multicast receive/send.

**Files:**
- Create: `src/core/dis/dis_socket.py`

**Step 1: Write the unit test**
```python
import unittest
from dis_socket import DisSocket

class TestDisSocket(unittest.TestCase):
    def test_multicast_address_default(self):
        """Default multicast address is 235.7.11.27."""
        socket = DisSocket()
        self.assertEqual(socket.multicast_addr, "235.7.11.27")
        self.assertEqual(socket.multicast_port, 3002)
    
    def test_socket_reuse_addr(self):
        """Socket should have SO_REUSEADDR option."""
        socket = DisSocket()
        self.assertTrue(socket.sock.getsockopt(socket.sol, socket.so_reuseaddr))
```

**Step 2: Run test — confirm it fails**

**Step 3: Write implementation**
- Multicast UDP socket setup (IP_MULTICAST_LOOP, IP_MULTICAST_TTL)
- bind() to multicast group
- sendto() for unicast replies
- Exception handling

**Step 4: Run test — confirm it passes**

**Step 5: Commit**
```
git add src/core/dis/dis_socket.py tests/unit/test_dis_socket.py
git commit -m "feat: add DIS UDP multicast socket wrapper"
```

---

## Task 3: DIS Message Dispatcher

**Goal:** Create dispatcher that routes received PDUs to handlers.

**Files:**
- Create: `src/core/dis/dis_dispatcher.py`

**Step 1: Write the unit test**
```python
import unittest
from dis_dispatcher import DisDispatcher

class TestDispatcher(unittest.TestCase):
    def test_register_handler(self):
        """Can register handler for PDU type."""
        dispatcher = DisDispatcher()
        calls = []
        
        def handler(pdu):
            calls.append(pdu)
        
        dispatcher.register(1, handler)  # Entity State
        self.assertIn(1, dispatcher.handlers)
    
    def test_dispatch_entity_state(self):
        """Entity State PDU dispatches to registered handler."""
        dispatcher = DisDispatcher()
        received = []
        
        dispatcher.register(1, lambda p: received.append(p))
        
        mock_pdu = {"pdu_type": 1, "data": "test"}
        dispatcher.dispatch(mock_pdu)
        
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["data"], "test")
```

**Step 2: Run test — confirm it fails**

**Step 3: Write implementation**
- Handler registry (dict by PDU type)
- register(pdu_type, handler) method
- dispatch(pdu) method

**Step 4: Run test — confirm it passes**

**Step 5: Commit**
```
git add src/core/dis/dis_dispatcher.py tests/unit/test_dis_dispatcher.py
git commit -m "feat: add DIS message dispatcher"
```

---

## Task 4: Entity State PDU Parser

**Goal:** Parse Entity State PDU binary data to Python object.

**Files:**
- Create: `src/core/dis/entity_parser.py`

**Step 1: Write the unit test**
```python
import unittest
from entity_parser import EntityStateParser, EntityState

class TestEntityParser(unittest.TestCase):
    def test_parse_entity_state(self):
        """Parse Entity State PDU bytes to EntityState object."""
        # Create minimal Entity State PDU bytes
        pdu_bytes = self._create_minimal_entity_state_pdu()
        
        parser = EntityStateParser()
        entity = parser.parse(pdu_bytes)
        
        self.assertIsInstance(entity, EntityState)
        self.assertEqual(entity.entity_id.site_id, 1)
    
    def test_entity_state_location_fields(self):
        """Parsed EntityState has lat/lon/alt from Entity Location Record."""
        pdu_bytes = self._create_entity_state_with_location()
        
        parser = EntityStateParser()
        entity = parser.parse(pdu_bytes)
        
        self.assertIsNotNone(entity.latitude)
        self.assertIsNotNone(entity.longitude)
        self.assertIsNotNone(entity.altitude)
```

**Step 2: Run test — confirm it fails**

**Step 3: Write implementation**
- DIS Entity ID parsing (6 bytes: site, application, entity)
- Entity State PDU field extraction
- Entity Location Record parsing (dead reckoning parameters + position)
- Orientation (pitch, yaw, roll)
- Velocity (x, y, z)

**Step 4: Run test — confirm it passes**

**Step 5: Commit**
```
git add src/core/dis/entity_parser.py tests/unit/test_entity_parser.py
git commit -m "feat: add Entity State PDU parser"
```

---

## Task 5: Fire PDU Parser & Generator

**Goal:** Parse incoming Fire PDUs and generate outgoing Fire PDUs.

**Files:**
- Create: `src/core/dis/fire_pdu.py`

**Step 1: Write the unit test**
```python
import unittest
from fire_pdu import FirePduParser, FirePduGenerator, FirePduData

class TestFirePdu(unittest.TestCase):
    def test_parse_fire_pdu(self):
        """Parse Fire PDU bytes to FirePduData object."""
        pdu_bytes = self._create_fire_pdu_bytes()
        
        parser = FirePduParser()
        fire_data = parser.parse(pdu_bytes)
        
        self.assertIsInstance(fire_data, FirePduData)
        self.assertEqual(fire_data.fire_mission_index, 1)
        self.assertGreater(fire_data.launcher_id.entity_id.entity, 0)
    
    def test_generate_fire_pdu(self):
        """Generate Fire PDU bytes from FirePduData."""
        fire_data = FirePduData(
            fire_mission_index=1,
            launcher_id=EntityId(1, 1, 1),
            target_id=EntityId(2, 1, 1),
            mission_time=12345.0
        )
        
        generator = FirePduGenerator()
        pdu_bytes = generator.generate(fire_data)
        
        self.assertIsInstance(pdu_bytes, bytes)
        self.assertGreater(len(pdu_bytes), 0)
```

**Step 2: Run test — confirm it fails**

**Step 3: Write implementation**
- Fire PDU field layout (munition id, fire mission index, location, etc.)
- Fire PDU generation with sequential numbers
- Wire format (big-endian)

**Step 4: Run test — confirm it passes**

**Step 5: Commit**
```
git add src/core/dis/fire_pdu.py tests/unit/test_fire_pdu.py
git commit -m "feat: add Fire PDU parser and generator"
```

---

## Task 6: Detonation PDU Parser

**Goal:** Parse Detonation PDU for engagement results.

**Files:**
- Create: `src/core/dis/detonation_pdu.py`

**Step 1: Write the unit test**
```python
import unittest
from detonation_pdu import DetonationPduParser, DetonationPduData

class TestDetonationPdu(unittest.TestCase):
    def test_parse_detonation_pdu(self):
        """Parse Detonation PDU bytes."""
        pdu_bytes = self._create_detonation_pdu_bytes()
        
        parser = DetonationPduParser()
        detonation = parser.parse(pdu_bytes)
        
        self.assertIsInstance(detonation, DetonationPduData)
        self.assertIn(detonation.detonation_result, [0, 1, 2, 3, 4])  # Valid DIS results
```

**Step 2: Run test — confirm it fails**

**Step 3: Write implementation**
- Detonation PDU field layout
- Detonation result codes (DETONATION_SUCCESS=0, DETONATION_OTHER=4, etc.)

**Step 4: Run test — confirm it passes**

**Step 5: Commit**
```
git add src/core/dis/detonation_pdu.py tests/unit/test_detonation_pdu.py
git commit -m "feat: add Detonation PDU parser"
```

---

## Task 7: Signal PDU Parser (ESM Data)

**Goal:** Parse Signal PDU for ESM/electronic warfare data.

**Files:**
- Create: `src/core/dis/signal_pdu.py`

**Step 1: Write the unit test**
```python
import unittest
from signal_pdu import SignalPduParser, SignalPduData

class TestSignalPdu(unittest.TestCase):
    def test_parse_signal_pdu(self):
        """Parse Signal PDU for ESM data."""
        pdu_bytes = self._create_signal_pdu_bytes()
        
        parser = SignalPduParser()
        signal = parser.parse(pdu_bytes)
        
        self.assertIsInstance(signal, SignalPduData)
        self.assertGreater(signal.number_of_samples, 0)
        self.assertIsNotNone(signal.data)
```

**Step 2: Run test — confirm it fails**

**Step 3: Write implementation**
- Signal PDU field layout
- Variable datum record parsing
- Data samples extraction

**Step 4: Run test — confirm it passes**

**Step 5: Commit**
```
git add src/core/dis/signal_pdu.py tests/unit/test_signal_pdu.py
git commit -m "feat: add Signal PDU parser for ESM data"
```

---

## Task 8: Entity Tracker

**Goal:** Track entities over time, manage entity lifecycle.

**Files:**
- Create: `src/core/dis/entity_tracker.py`

**Step 1: Write the unit test**
```python
import unittest
from entity_tracker import EntityTracker, TrackedEntity

class TestEntityTracker(unittest.TestCase):
    def test_add_entity(self):
        """Add new entity to tracker."""
        tracker = EntityTracker()
        entity = TrackedEntity(
            entity_id=EntityId(1, 1, 1),
            entity_type=EntityType(...),
            location=Location(30.0, 120.0, 5000)
        )
        
        tracker.add(entity)
        self.assertEqual(tracker.count(), 1)
    
    def test_update_entity(self):
        """Update existing entity position."""
        tracker = EntityTracker()
        entity = TrackedEntity(entity_id=EntityId(1, 1, 1), ...)
        tracker.add(entity)
        
        # Update location
        tracker.update(EntityId(1, 1, 1), Location(30.1, 120.1, 5100))
        
        updated = tracker.get(EntityId(1, 1, 1))
        self.assertAlmostEqual(updated.location.lat, 30.1, places=2)
    
    def test_remove_entity(self):
        """Remove entity when marked dead."""
        tracker = EntityTracker()
        tracker.add(TrackedEntity(entity_id=EntityId(1, 1, 1), ...))
        
        tracker.remove(EntityId(1, 1, 1))
        self.assertEqual(tracker.count(), 0)
```

**Step 2: Run test — confirm it fails**

**Step 3: Write implementation**
- Entity dictionary (by entity ID)
- add(), update(), remove(), get() methods
- Entity state history

**Step 4: Run test — confirm it passes**

**Step 5: Commit**
```
git add src/core/dis/entity_tracker.py tests/unit/test_entity_tracker.py
git commit -m "feat: add entity tracker for track management"
```

---

## Task 9: DIS Client Integration

**Goal:** Integrate all components into a working DIS client.

**Files:**
- Create: `src/core/dis/dis_client.py`

**Step 1: Write the integration test**
```python
import unittest
from dis_client import DisClient

class TestDisClient(unittest.TestCase):
    def test_client_start_stop(self):
        """Client can start and stop."""
        client = DisClient(multicast_addr="235.7.11.27", port=3002)
        
        client.start()
        self.assertTrue(client.is_running())
        
        client.stop()
        self.assertFalse(client.is_running())
    
    def test_send_fire_command(self):
        """Client can send Fire PDU."""
        client = DisClient(multicast_addr="235.7.11.27", port=3002)
        client.start()
        
        fire_data = FirePduData(
            fire_mission_index=1,
            launcher_id=EntityId(1, 1, 1),
            target_id=EntityId(2, 1, 1),
            mission_time=12345.0
        )
        
        result = client.send_fire(fire_data)
        self.assertTrue(result)
        
        client.stop()
```

**Step 2: Run test — confirm it fails (expected, needs full system)**

**Step 3: Write integration wrapper**
- Async receive loop in thread
- Queue-based processing
- Send queue for outgoing PDUs
- Clean shutdown

**Step 4: Run test — confirm it passes (if AFSIM is running, otherwise mock test)**

**Step 5: Commit**
```
git add src/core/dis/dis_client.py tests/unit/test_dis_client.py
git commit -m "feat: add integrated DIS client"
```

---

## Task 10: AFSIM Configuration Helper

**Goal:** Create AFSIM scenario snippet for DIS/xio interface.

**Files:**
- Create: `src/sim/config/dis_interface.txt`

**Content:**
```
# DIS Interface for Kill Chain Manager
# Include this in AFSIM scenario to enable DIS communication

dis_interface
   application 2
end_dis_interface

xio_interface
   multicast 235.7.11.27 10.
   port 3002
   connect_to_simulations
   auto_dis_mapping yes
   time_to_live 8
end_xio_interface

event_output file output/kill_chain.evt end_event_output
event_pipe   file output/kill_chain.aer end_event_pipe
```

**Commit:**
```
git add src/sim/config/dis_interface.txt
git commit -m "feat: add AFSIM DIS interface configuration"
```

---

## Task 11: Integration Test with AFSIM

**Goal:** Full integration test running against AFSIM.

**Files:**
- Create: `tests/integration/test_afsim_dis_connection.py`

**Test scenario:**
1. Start AFSIM with `dis_interface.txt` configuration
2. Start Python DIS client
3. Verify entity state PDUs received
4. Send fire command
5. Verify detonation result received
6. Evaluate metrics

**Note:** This test requires AFSIM to be running. Can be skipped if AFSIM not available.

---

## Execution Options

**1. Subagent-Driven (Recommended)**
I'll dispatch subagents per task. Each task: write test → implement → verify → commit.

**2. Manual**
You run tasks yourself.

Which approach? Once confirmed, I'll start the subagent-driven execution loop.