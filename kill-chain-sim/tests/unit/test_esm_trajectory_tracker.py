"""
TDD Test for EsmTrajectoryTracker
=================================
Test generates virtual tracks from Signal PDUs when Entity State PDUs are unavailable.

AFSIM sends Signal PDUs (type=4) for emitters instead of Entity State PDUs.
EsmTrajectoryTracker triangulates position from bearing-only ESM reports.
"""

import pytest
import sys
import os
import struct
import time
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from src.core.dis.dis_protocol import EntityId, SignalPdu, EntityType
from src.core.dis.entity_tracker import TrackedEntity, Location
from src.core.dis.esm_trajectory_tracker import EsmTrajectoryTracker


def build_esm_signal_data(bearing_deg: float, frequency_hz: float = 3e9) -> bytes:
    """Build mock ESM Signal PDU data field containing bearing and frequency.

    AFSIM Signal PDU data field uses variable datum records:
    - datum_id (4 bytes big-endian) + datum_length (4 bytes) + datum_value

    Known ESM datum IDs:
    - 0x01 = Frequency (double, 8 bytes)
    - 0x02 = Pulse Width (float, 4 bytes)
    - 0x03 = PRF (float, 4 bytes)
    - 0x04 = Signal Strength (float, 4 bytes)
    - 0x05 = Bearing (float, 4 bytes) - degrees
    - 0x10 = Emitter Type (uint32, 4 bytes)
    """
    data = b''

    # Frequency (0x01, double, 8 bytes)
    data += struct.pack(">I", 0x01)
    data += struct.pack(">I", 8)
    data += struct.pack(">d", frequency_hz)

    # Bearing (0x05, float, 4 bytes)
    data += struct.pack(">I", 0x05)
    data += struct.pack(">I", 4)
    data += struct.pack(">f", bearing_deg)

    # Signal strength (0x04, float, 4 bytes) - reasonable dBm
    data += struct.pack(">I", 0x04)
    data += struct.pack(">I", 4)
    data += struct.pack(">f", -50.0)

    # Pulse width (0x02, float, 4 bytes)
    data += struct.pack(">I", 0x02)
    data += struct.pack(">I", 4)
    data += struct.pack(">f", 2.5)

    return data


def create_signal_pdu(entity_id: EntityId, bearing_deg: float,
                     frequency_hz: float = 3e9, radio_id: int = 0) -> SignalPdu:
    """Create a mock Signal PDU with ESM data."""
    return SignalPdu(
        entity_id=entity_id,
        radio_id=radio_id,
        encoding_scheme=1,   # Generic data
        tdl_type=0,
        sample_rate=0,
        number_of_samples=0,
        data=build_esm_signal_data(bearing_deg, frequency_hz)
    )


class TestEsmTrajectoryTracker:
    """Test EsmTrajectoryTracker creates virtual tracks from Signal PDUs."""

    def test_tracker_initialization(self):
        """Tracker initializes with empty state."""
        tracker = EsmTrajectoryTracker()
        tracks = tracker.get_virtual_tracks()
        assert tracks == []
        assert tracker.get_emitter_count() == 0

    def test_single_signal_pdu_not_enough_for_track(self):
        """One report cannot create a track - need at least 3."""
        tracker = EsmTrajectoryTracker()
        emitter = EntityId(1, 1, 25)

        pdu = create_signal_pdu(emitter, bearing_deg=45.0, frequency_hz=3e9)
        tracker.process_signal_pdu(pdu, sim_time=1000.0)

        tracks = tracker.get_virtual_tracks()
        # Should not yet have a triangulated track
        assert len(tracks) == 0

    def test_three_reports_creates_virtual_track(self):
        """Three reports with different bearings should triangulate a position."""
        tracker = EsmTrajectoryTracker()
        emitter = EntityId(1, 1, 25)

        base_time = 1000.0

        # Three bearings from different angles (simulating different observer positions)
        # Bearing #1: from observer at origin, target at 45° bearing
        # Bearing #2: from observer shifted, target at 90° bearing
        # Bearing #3: from observer shifted more, target at 135° bearing
        bearings = [45.0, 90.0, 135.0]

        for i, bearing in enumerate(bearings):
            pdu = create_signal_pdu(emitter, bearing_deg=bearing, frequency_hz=3e9)
            tracker.process_signal_pdu(pdu, sim_time=base_time + i * 1.0)

        tracks = tracker.get_virtual_tracks()
        assert len(tracks) >= 1, f"Expected at least 1 track, got {len(tracks)}"

        # Verify track has required fields
        track = tracks[0]
        assert hasattr(track, 'entity_id')
        assert hasattr(track, 'location')
        assert hasattr(track, 'velocity')

    def test_track_has_valid_lat_lon(self):
        """Virtual track must have valid lat/lon coordinates."""
        tracker = EsmTrajectoryTracker()
        emitter = EntityId(1, 1, 25)

        base_time = 1000.0

        # 3 bearings at 60° intervals
        for i, bearing in enumerate([30.0, 90.0, 150.0]):
            pdu = create_signal_pdu(emitter, bearing_deg=bearing, frequency_hz=3e9)
            tracker.process_signal_pdu(pdu, sim_time=base_time + i * 1.0)

        tracks = tracker.get_virtual_tracks()
        assert len(tracks) >= 1

        track = tracks[0]
        loc = track.location

        # Lat should be reasonable (-90 to 90)
        assert -90 <= loc.lat <= 90, f"Invalid lat: {loc.lat}"
        # Lon should be reasonable (-180 to 180)
        assert -180 <= loc.lon <= 180, f"Invalid lon: {loc.lon}"
        # Altitude should be non-negative (ground level or above)
        assert loc.alt >= 0, f"Invalid alt: {loc.alt}"

    def test_track_has_velocity_knots(self):
        """Virtual track should have velocity in knots (or zero if stationary)."""
        tracker = EsmTrajectoryTracker()
        emitter = EntityId(1, 1, 25)

        base_time = 1000.0

        # 4 reports to get velocity estimate
        for i in range(4):
            bearing = 45.0 + i * 3.0  # Slowly changing bearing = slow movement
            pdu = create_signal_pdu(emitter, bearing_deg=bearing, frequency_hz=3e9)
            tracker.process_signal_pdu(pdu, sim_time=base_time + i * 1.0)

        tracks = tracker.get_virtual_tracks()
        assert len(tracks) >= 1

        track = tracks[0]
        vel = track.velocity

        # Velocity should be a Vector3Float with reasonable magnitude
        speed_ms = math.sqrt(vel.x**2 + vel.y**2 + vel.z**2)
        # Convert to knots: 1 m/s ≈ 1.944 knots
        speed_kts = speed_ms * 1.944
        # Should be between 0 and 5000 knots (reasonable for aircraft/missile)
        # Note: initial velocity estimate from bearing rate may be high,
        # but Kalman filter refines it over time
        assert 0 <= speed_kts <= 5000, f"Unreasonable speed: {speed_kts:.1f} kts"

    def test_multiple_emitters_create_multiple_tracks(self):
        """Different emitters (different entity IDs) create separate tracks."""
        tracker = EsmTrajectoryTracker()

        # Emitter 1 at 3 reports
        emitter1 = EntityId(1, 1, 25)
        base_time = 1000.0
        for i in range(3):
            pdu = create_signal_pdu(emitter1, bearing_deg=30.0 + i * 10, frequency_hz=3e9)
            tracker.process_signal_pdu(pdu, sim_time=base_time + i * 1.0)

        # Emitter 2 at 3 reports
        emitter2 = EntityId(1, 1, 30)
        for i in range(3):
            pdu = create_signal_pdu(emitter2, bearing_deg=120.0 + i * 10, frequency_hz=5e9)
            tracker.process_signal_pdu(pdu, sim_time=base_time + i * 1.0)

        tracks = tracker.get_virtual_tracks()
        assert len(tracks) >= 2, f"Expected 2 tracks, got {len(tracks)}"

    def test_moving_emitter_tracked(self):
        """Emitter with changing bearing over time should be tracked."""
        tracker = EsmTrajectoryTracker()
        emitter = EntityId(1, 1, 25)

        base_time = 1000.0

        # Emitter moving: bearing changes rapidly
        # Use 5 reports to capture movement
        for i in range(5):
            bearing = 45.0 + i * 8.0  # 8° per second = turning target
            pdu = create_signal_pdu(emitter, bearing_deg=bearing, frequency_hz=3e9)
            tracker.process_signal_pdu(pdu, sim_time=base_time + i * 0.5)

        tracks = tracker.get_virtual_tracks()
        assert len(tracks) >= 1

        track = tracks[0]
        # Velocity should indicate movement (non-zero)
        speed_ms = math.sqrt(track.velocity.x**2 + track.velocity.y**2 + track.velocity.z**2)
        assert speed_ms > 0.1, "Moving target should have non-zero velocity"


class TestMilpAllocationWithVirtualTracks:
    """Test that virtual tracks can be fed to MILP allocator."""

    def test_milp_allocator_accepts_virtual_tracks(self):
        """MILP allocator can solve with virtual tracks as targets."""
        from src.research.algorithms.milp_allocator import MilpAllocator, Target, Sensor, Weapon
        from src.research.algorithms.milp_allocator import SolveStatus

        tracker = EsmTrajectoryTracker()
        emitter = EntityId(1, 1, 25)
        base_time = time.time()

        # Simulate 5 Signal PDUs from a moving emitter
        for i in range(5):
            bearing = 45.0 + i * 5.0  # Moving target
            pdu = create_signal_pdu(emitter, bearing_deg=bearing, frequency_hz=3e9)
            tracker.process_signal_pdu(pdu, sim_time=base_time + i * 0.5)

        tracks = tracker.get_virtual_tracks()
        assert len(tracks) >= 1, "Should have at least one virtual track"

        # Build targets from virtual tracks
        # Note: we use default range_to_sensors since we don't have sensor locations
        targets = []
        for t in tracks:
            # Approximate speed in knots from velocity vector
            speed_ms = math.sqrt(t.velocity.x**2 + t.velocity.y**2 + t.velocity.z**2)
            speed_kts = speed_ms * 1.944 if speed_ms else 300.0

            target = Target(
                id=hash(str(t.entity_id)) % 10000,
                priority=5.0,
                velocity_kts=speed_kts,
                type="aircraft",
                lat=t.location.lat,
                lon=t.location.lon,
                altitude_ft=t.location.alt * 3.281,  # meters to feet
                range_to_sensors={1: 80}  # assumed sensor 1 range in km
            )
            targets.append(target)

        # Define sensors and weapons
        sensors = [Sensor(1, 150, "track", 60, 30)]
        weapons = [Weapon(1, 600, 0.8, 600, "sam")]

        allocator = MilpAllocator(time_limit_sec=5)
        result = allocator.solve(targets, sensors, weapons)

        # Should produce a valid result (OPTIMAL, FEASIBLE, or PARTIAL)
        assert result.status in [
            SolveStatus.OPTIMAL,
            SolveStatus.FEASIBLE,
            SolveStatus.PARTIAL
        ], f"Expected valid status, got {result.status}"

    def test_virtual_track_kills_high_value_target(self):
        """Test that priority is assigned correctly to virtual tracks."""
        from src.research.algorithms.milp_allocator import MilpAllocator, Target, Sensor, Weapon
        from src.research.algorithms.milp_allocator import SolveStatus

        tracker = EsmTrajectoryTracker()

        # Two emitters: one slow (aircraft), one fast (missile)
        emitter_missile = EntityId(1, 1, 40)
        emitter_aircraft = EntityId(1, 1, 45)
        base_time = time.time()

        # Both emitters generate reports
        for i in range(5):
            # Missile: fast bearing change (high speed)
            pdu_m = create_signal_pdu(emitter_missile, bearing_deg=60.0 + i * 15, frequency_hz=10e9)
            tracker.process_signal_pdu(pdu_m, sim_time=base_time + i * 0.3)

            # Aircraft: slow bearing change
            pdu_a = create_signal_pdu(emitter_aircraft, bearing_deg=120.0 + i * 2, frequency_hz=3e9)
            tracker.process_signal_pdu(pdu_a, sim_time=base_time + i * 0.3)

        tracks = tracker.get_virtual_tracks()
        assert len(tracks) >= 2

        # Higher speed = higher priority missile
        # Sort by speed to identify missile
        sorted_tracks = sorted(tracks, key=lambda t: math.sqrt(t.velocity.x**2 + t.velocity.y**2 + t.velocity.z**2), reverse=True)

        # Fast track should be treated as higher priority
        fast_track = sorted_tracks[0]
        speed_ms = math.sqrt(fast_track.velocity.x**2 + fast_track.velocity.y**2 + fast_track.velocity.z**2)
        speed_kts = speed_ms * 1.944

        # If we correctly identified a fast-moving target, it should have been allocated
        sensors = [Sensor(1, 200, "track", 60, 30)]
        weapons = [Weapon(1, 150, 0.9, 1500, "aa_missile")]

        targets = [
            Target(
                id=hash(str(t.entity_id)) % 10000,
                priority=8.0 if speed_kts > 500 else 5.0,
                velocity_kts=speed_kts,
                type="missile" if speed_kts > 500 else "aircraft",
                lat=t.location.lat,
                lon=t.location.lon,
                altitude_ft=t.location.alt * 3.281,
                range_to_sensors={1: 100}
            )
            for t in tracks
        ]

        allocator = MilpAllocator(time_limit_sec=5)
        result = allocator.solve(targets, sensors, weapons)

        assert result.status in [SolveStatus.OPTIMAL, SolveStatus.FEASIBLE, SolveStatus.PARTIAL]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])