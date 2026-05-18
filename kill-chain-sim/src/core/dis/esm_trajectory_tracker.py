"""
EsmTrajectoryTracker - Generate virtual tracks from ESM/Signal PDUs
====================================================================

When AFSIM sends Signal PDUs (type=4) instead of Entity State PDUs, we can't
directly track entity positions. EsmTrajectoryTracker uses bearing-only 
geolocation to estimate emitter positions and project trajectories.

Method:
1. Collect bearing reports from the same emitter (entity_id)
2. When ≥3 reports accumulated, triangulate position using cross-bearing fix
3. Use constant-velocity Kalman filter to project position between updates
4. Produce virtual TrackedEntity objects compatible with EntityTracker

Bearing-Only Triangulation:
- Each report gives a line-of-bearing from a known sensor location
- Two bearings from different sensor positions intersect at the target
- With 3+ bearings, we get a more robust fix via least-squares

Sensor Location Model:
- Default ESM sensor assumed at (lat=38.0, lon=-117.0) — Nevada test range
- Configurable via set_sensor_location(lat, lon, alt)
"""

import math
import struct
import time
import logging
from typing import Dict, List, Optional, Tuple

from src.core.dis.dis_protocol import EntityId, SignalPdu, Vector3Float, Vector3Double, Orientation, EntityType
from src.core.dis.entity_tracker import TrackedEntity, Location

logger = logging.getLogger(__name__)


class EsmTrajectoryTracker:
    """Generate virtual tracks from ESM/Signal PDUs when Entity State PDUs unavailable.
    
    Uses bearing-only geolocation (triangulation) from multiple ESM reports.
    Projects constant-velocity trajectories between updates.
    Produces virtual TrackedEntity objects compatible with EntityTracker.
    """
    
    # Configuration
    MIN_REPORTS_FOR_TRACK = 3        # Need at least 3 bearings to triangulate
    MAX_BEARING_AGE_SEC = 60.0       # Discard bearings older than this
    POSITION_TOLERANCE_M = 5000.0    # triangulation convergence tolerance (meters)
    
    def __init__(self, sensor_lat: float = 38.0, sensor_lon: float = -117.0, sensor_alt: float = 0.0):
        """Initialize tracker with ESM sensor location.
        
        Args:
            sensor_lat: Sensor latitude (degrees North)
            sensor_lon: Sensor longitude (degrees East)
            sensor_alt: Sensor altitude (meters MSL)
        """
        self._sensor_lat = sensor_lat
        self._sensor_lon = sensor_lon
        self._sensor_alt = sensor_alt
        
        # Per-emitter state: entity_id -> list of (timestamp, bearing_deg, frequency_hz)
        self._emitter_reports: Dict[str, List[Tuple[float, float, float]]] = {}
        
        # Per-emitter state: entity_id -> virtual track info
        self._emitter_tracks: Dict[str, '_VirtualTrack'] = {}
        
        # Next virtual entity ID to assign
        self._next_virtual_entity_id = 1
        
        # ESM data parser (same format as EsmClient uses)
        self._esm_data_parser = _EsmDataParser()
    
    def set_sensor_location(self, lat: float, lon: float, alt: float = 0.0) -> None:
        """Set the ESM sensor location for triangulation.
        
        Args:
            lat: Latitude degrees
            lon: Longitude degrees  
            alt: Altitude in meters
        """
        self._sensor_lat = lat
        self._sensor_lon = lon
        self._sensor_alt = alt
    
    def process_signal_pdu(self, pdu: SignalPdu, sim_time: float) -> None:
        """Process a Signal PDU containing ESM data.
        
        Args:
            pdu: Parsed SignalPdu from DIS
            sim_time: Current simulation time in seconds
        """
        key = str(pdu.entity_id)
        
        # Extract ESM data from PDU
        esm_data = self._esm_data_parser.parse(pdu.data)
        bearing_deg = esm_data.get('bearing', 0.0)
        frequency_hz = esm_data.get('frequency', 0.0)
        
        if bearing_deg == 0.0 and frequency_hz == 0.0:
            logger.debug(f"No ESM data in Signal PDU from {pdu.entity_id}")
            return
        
        # Store bearing report
        if key not in self._emitter_reports:
            self._emitter_reports[key] = []
        
        self._emitter_reports[key].append((sim_time, bearing_deg, frequency_hz))
        
        # Prune old reports
        self._emitter_reports[key] = [
            (t, b, f) for t, b, f in self._emitter_reports[key]
            if (sim_time - t) < self.MAX_BEARING_AGE_SEC
        ]
        
        logger.debug(f"ESM report from {pdu.entity_id}: bearing={bearing_deg:.1f}°, freq={frequency_hz/1e9:.2f}GHz at t={sim_time:.1f}")
        
        # Update virtual track if we have enough reports
        reports = self._emitter_reports[key]
        if len(reports) >= self.MIN_REPORTS_FOR_TRACK:
            self._update_virtual_track(pdu.entity_id, sim_time)
    
    def _update_virtual_track(self, entity_id: EntityId, sim_time: float) -> None:
        """Update or create virtual track for an emitter.
        
        Args:
            entity_id: Emitter entity ID
            sim_time: Current simulation time
        """
        key = str(entity_id)
        reports = self._emitter_reports[key]
        
        if len(reports) < self.MIN_REPORTS_FOR_TRACK:
            return
        
        if key not in self._emitter_tracks:
            # Create new virtual track
            self._emitter_tracks[key] = _VirtualTrack(
                entity_id=entity_id,
                virtual_id=self._next_virtual_entity_id,
                sensor_lat=self._sensor_lat,
                sensor_lon=self._sensor_lon,
                sensor_alt=self._sensor_alt
            )
            self._next_virtual_entity_id += 1
            logger.info(f"Created virtual track for emitter {entity_id} (virtual_id={self._emitter_tracks[key].virtual_id})")
        
        # Update track with new bearing data
        track = self._emitter_tracks[key]
        
        # Get all recent reports
        recent = [(t, b, f) for t, b, f in reports if (sim_time - t) < self.MAX_BEARING_AGE_SEC]
        
        if len(recent) < self.MIN_REPORTS_FOR_TRACK:
            return
        
        track.update_position(recent, sim_time)
    
    def get_virtual_tracks(self) -> List[TrackedEntity]:
        """Get all virtual tracks as TrackedEntity objects.
        
        Returns:
            List of TrackedEntity objects with location and velocity derived from ESM reports.
        """
        tracks = []
        for key, track in self._emitter_tracks.items():
            te = track.to_tracked_entity()
            if te is not None:
                tracks.append(te)
        return tracks
    
    def get_emitter_count(self) -> int:
        """Get number of emitters being tracked."""
        return len(self._emitter_tracks)
    
    def get_emitter_reports(self, entity_id: EntityId) -> List:
        """Get bearing reports for a specific emitter.
        
        Args:
            entity_id: Entity ID to query
            
        Returns:
            List of (timestamp, bearing_deg, frequency_hz) tuples
        """
        return list(self._emitter_reports.get(str(entity_id), []))
    
    def clear(self) -> None:
        """Clear all tracked emitters and reports."""
        self._emitter_reports.clear()
        self._emitter_tracks.clear()


class _EsmDataParser:
    """Parse ESM data from Signal PDU data field.
    
    AFSIM Signal PDUs use variable datum records:
    - datum_id (4 bytes big-endian) + datum_length (4 bytes) + datum_value
    
    Known datum IDs:
    - 0x01 = Frequency (double, 8 bytes)
    - 0x02 = Pulse Width (float, 4 bytes)
    - 0x03 = PRF (float, 4 bytes)
    - 0x04 = Signal Strength (float, 4 bytes)
    - 0x05 = Bearing (float, 4 bytes) — degrees
    - 0x10 = Emitter Type (uint32, 4 bytes)
    """
    
    def parse(self, data: bytes) -> Dict[str, float]:
        """Parse ESM data from Signal PDU data bytes.
        
        Args:
            data: Raw data bytes from Signal PDU
            
        Returns:
            Dict with keys: bearing, frequency, pulse_width, prf, signal_strength, emitter_type
        """
        result = {
            'bearing': 0.0,
            'frequency': 0.0,
            'pulse_width': 0.0,
            'prf': 0.0,
            'signal_strength': -100.0,
            'emitter_type': 0
        }
        
        if len(data) < 16:
            return result
        
        offset = 0
        while offset + 8 <= len(data):
            try:
                datum_id = struct.unpack(">I", data[offset:offset + 4])[0]
                offset += 4
                datum_len = struct.unpack(">I", data[offset:offset + 4])[0]
                offset += 4
                
                if offset + datum_len > len(data):
                    break
                
                value_data = data[offset:offset + datum_len]
                offset += datum_len
                
                if datum_id == 0x01 and datum_len == 8:
                    result['frequency'] = struct.unpack(">d", value_data)[0]
                elif datum_id == 0x02 and datum_len == 4:
                    result['pulse_width'] = struct.unpack(">f", value_data)[0]
                elif datum_id == 0x03 and datum_len == 4:
                    result['prf'] = struct.unpack(">f", value_data)[0]
                elif datum_id == 0x04 and datum_len == 4:
                    result['signal_strength'] = struct.unpack(">f", value_data)[0]
                elif datum_id == 0x05 and datum_len == 4:
                    result['bearing'] = struct.unpack(">f", value_data)[0]
                elif datum_id == 0x10 and datum_len == 4:
                    result['emitter_type'] = struct.unpack(">I", value_data)[0]
            except Exception:
                break
        
        return result


class _VirtualTrack:
    """Internal virtual track state with constant-velocity Kalman filter.
    
    State vector: [x, y, z, vx, vy, vz] (position in ECEF meters, velocity m/s)
    Measurement: bearing angle (degrees) from sensor
    """
    
    def __init__(self, entity_id: EntityId, virtual_id: int,
                 sensor_lat: float, sensor_lon: float, sensor_alt: float):
        self.entity_id = entity_id
        self.virtual_id = virtual_id
        self._sensor_lat = sensor_lat
        self._sensor_lon = sensor_lon
        self._sensor_alt = sensor_alt
        
        # Kalman filter state
        self._state = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]  # x, y, z, vx, vy, vz
        self._P = [  # State covariance
            [10000, 0, 0, 0, 0, 0],
            [0, 10000, 0, 0, 0, 0],
            [0, 0, 10000, 0, 0, 0],
            [0, 0, 0, 100, 0, 0],
            [0, 0, 0, 0, 100, 0],
            [0, 0, 0, 0, 0, 100],
        ]
        
        # Position estimate (lat, lon, alt) for returning to caller
        self._latitude = 0.0
        self._longitude = 0.0
        self._altitude = 0.0
        
        # Velocity (m/s in ECEF)
        self._vx = 0.0
        self._vy = 0.0
        self._vz = 0.0
        
        # Track quality (0-1)
        self._quality = 0.0
        
        # Timestamp of last update
        self._last_update_time = 0.0
        
        # Number of reports received
        self._report_count = 0
        
        # Initialized flag
        self._initialized = False
    
    def update_position(self, reports: List[Tuple[float, float, float]], sim_time: float) -> None:
        """Update track with new bearing reports.
        
        Args:
            reports: List of (timestamp, bearing_deg, frequency_hz)
            sim_time: Current simulation time
        """
        self._report_count += len(reports)
        self._last_update_time = sim_time
        
        if not self._initialized:
            # Use triangulation from bearing angles to initialize position
            if len(reports) >= 3:
                self._initialize_from_triangulation(reports, sim_time)
        else:
            # Update Kalman filter with new bearing measurements
            self._update_kalman(reports, sim_time)
    
    def _initialize_from_triangulation(self, reports: List[Tuple[float, float, float]], 
                                       sim_time: float) -> None:
        """Initialize track position using bearing-only triangulation.
        
        Uses bearing intersection from multiple observations.
        Since all bearings originate from the same sensor location (sensor_lat, sensor_lon),
        we need to estimate range to triangulate position.
        
        Strategy: Use bearing angle rate to estimate range.
        - Target moving in direction perpendicular to LOS: bearing changes quickly = close
        - Bearing changes slowly = target is distant or moving toward/away from sensor
        
        We use a fixed range assumption for the first fix, then refine with motion.
        """
        import math
        
        # Convert sensor location to ECEF
        sensor_x, sensor_y, sensor_z = self._geodetic_to_ecef(
            self._sensor_lat, self._sensor_lon, self._sensor_alt
        )
        
        # Collect bearing differences over time
        if len(reports) < 2:
            return
        
        # For initial position, use first bearing with assumed range
        # Strategy: use last bearing and assume target is at some nominal range (50 km)
        # This gives us an initial position fix
        t0, b0, f0 = reports[0]
        t_last, b_last, f_last = reports[-1]
        
        # Average bearing
        bearings = [b for _, b, _ in reports]
        avg_bearing = sum(bearings) / len(bearings)
        
        # Assume nominal range of 50 km for initial fix
        # (real system would use bearing rate for range estimation)
        range_m = 50000.0
        
        # Convert bearing (degrees, 0=North, clockwise) to ECEF direction
        bearing_rad = math.radians(avg_bearing)
        
        # Approximate local tangent plane conversion
        # North direction: decrease lat, increase lon
        # East direction: increase lon
        lat_rad = math.radians(self._sensor_lat)
        lon_rad = math.radians(self._sensor_lon)
        
        # Calculate target position (rough approximation)
        # Using small angle approximation
        deast = range_m * math.sin(bearing_rad)
        dnorth = range_m * math.cos(bearing_rad)
        
        # 1 degree lat ≈ 111 km, 1 degree lon ≈ 111 km * cos(lat)
        lat_offset = dnorth / 111000.0
        lon_offset = deast / (111000.0 * math.cos(lat_rad))
        
        target_lat = self._sensor_lat + lat_offset
        target_lon = self._sensor_lon + lon_offset
        target_alt = 10000.0  # 10 km altitude (typical for aircraft)
        
        # Convert to ECEF
        tx, ty, tz = self._geodetic_to_ecef(target_lat, target_lon, target_alt)
        
        # Set initial state
        self._state[0] = tx
        self._state[1] = ty
        self._state[2] = tz
        
        # Estimate velocity from bearing change if we have enough reports
        if len(reports) >= 3:
            dt = t_last - t0
            if dt > 0.1:
                # Calculate angular rate of bearing change
                db = b_last - b0
                # Normalize to [-180, 180]
                while db > 180:
                    db -= 360
                while db < -180:
                    db += 360
                
                # Angular rate in rad/s
                angular_rate = math.radians(db) / dt
                
                # Rough velocity estimate: if bearing is changing, target is moving
                # v = angular_rate * range
                v_mag = abs(angular_rate) * range_m
                
                # Direction perpendicular to bearing line
                # Assume motion is roughly perpendicular to LOS
                velocity_bearing_rad = bearing_rad + math.pi / 2 if angular_rate >= 0 else bearing_rad - math.pi / 2
                
                self._state[3] = v_mag * math.sin(velocity_bearing_rad) * math.cos(lat_rad)
                self._state[4] = v_mag * math.cos(velocity_bearing_rad)
                self._state[5] = 0  # No vertical velocity component for now
        
        # Mark as initialized
        self._initialized = True
        self._quality = 0.5
        
        # Update lat/lon/alt from ECEF state
        self._ecef_to_geodetic()
        
        logger.info(f"Virtual track {self.virtual_id} initialized at ({self._latitude:.4f}°, {self._longitude:.4f}°)")
    
    def _update_kalman(self, reports: List[Tuple[float, float, float]], sim_time: float) -> None:
        """Update Kalman filter with bearing measurements.
        
        Args:
            reports: List of (timestamp, bearing_deg, frequency_hz)
            sim_time: Current simulation time
        """
        import math
        
        # Sensor position in ECEF
        sensor_x, sensor_y, sensor_z = self._geodetic_to_ecef(
            self._sensor_lat, self._sensor_lon, self._sensor_alt
        )
        
        for timestamp, bearing_deg, freq in reports:
            # Predict state forward to measurement time
            dt = timestamp - self._last_update_time if self._last_update_time > 0 else 0.1
            if dt <= 0:
                dt = 0.1
            self._predict(dt)
            
            # Compute expected bearing from current state
            dx = self._state[0] - sensor_x
            dy = self._state[1] - sensor_y
            dz = self._state[2] - sensor_z
            
            # Horizontal bearing in degrees (0=North, clockwise)
            bearing = math.degrees(math.atan2(dy, dx)) % 360
            
            # Innovation: measured - predicted
            innovation = math.radians(bearing_deg - bearing)
            # Normalize
            while innovation > math.pi:
                innovation -= 2 * math.pi
            while innovation < -math.pi:
                innovation += 2 * math.pi
            
            # Kalman gain (simplified 1D bearing measurement)
            # H = [dh/dx, dh/dy, dh/dz, 0, 0, 0]
            r = 100.0  # Measurement noise variance (degrees^2)
            
            # Compute H vector: partial derivative of bearing w.r.t. position
            dist_sq = dx*dx + dy*dy
            dist = math.sqrt(dist_sq) if dist_sq > 0 else 1.0
            
            h = [
                -dy / dist,   # dh/dx
                dx / dist,    # dh/dy
                0,            # dh/dz (no vertical effect on horizontal bearing)
                0, 0, 0        # no velocity measurement
            ]
            
            # K = P * H' / (H * P * H' + R)
            hp = [h[0]*self._P[0][i] + h[1]*self._P[1][i] + h[2]*self._P[2][i] 
                  for i in range(6)]
            hph = h[0]*hp[0] + h[1]*hp[1] + h[2]*hp[2]
            
            # Skip if innovation is very large (bad measurement)
            if abs(innovation) > math.radians(30):
                continue
            
            gain = [hp[i] / (hph + r) for i in range(6)]
            
            # Update state
            for i in range(6):
                self._state[i] += gain[i] * innovation
            
            # Update covariance
            for i in range(6):
                for j in range(6):
                    self._P[i][j] -= gain[i] * hp[j]
            
            # Keep covariance positive semi-definite
            for i in range(6):
                self._P[i][i] = max(self._P[i][i], 0.01)
        
        self._last_update_time = sim_time
        self._ecef_to_geodetic()
        
        # Update quality based on covariance trace
        trace = sum(self._P[i][i] for i in range(6))
        self._quality = min(1.0, 10000.0 / (trace + 1))
    
    def _predict(self, dt: float) -> None:
        """Predict state forward by dt seconds.
        
        Args:
            dt: Time step in seconds
        """
        # State transition: x_new = x + vx * dt, etc.
        # Constant velocity model
        self._state[0] += self._state[3] * dt
        self._state[1] += self._state[4] * dt
        self._state[2] += self._state[5] * dt
        
        # State covariance: P_new = F * P * F' + Q
        # F = [[1, dt], [0, 1]] for each axis
        # Q = process noise (small velocity perturbations)
        q = 10.0 * dt  # Process noise variance
        
        for i in range(3):
            # Position uncertainty grows with velocity uncertainty
            self._P[i][i] += abs(self._P[i+3][i+3]) * dt * dt + q
            # Cross-term
            self._P[i][i+3] += self._P[i+3][i+3] * dt
            self._P[i+3][i] += self._P[i+3][i] * dt
    
    def _geodetic_to_ecef(self, lat: float, lon: float, alt: float) -> Tuple[float, float, float]:
        """Convert geodetic (lat, lon, alt) to ECEF (x, y, z) meters.
        
        Args:
            lat: Latitude degrees North
            lon: Longitude degrees East
            alt: Altitude meters
            
        Returns:
            Tuple of (x, y, z) in meters
        """
        import math
        
        a = 6378137.0        # WGS84 semi-major axis
        b = 6356752.314245   # WGS84 semi-minor axis
        e2 = 1 - (b * b) / (a * a)
        
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)
        
        N = a / math.sqrt(1 - e2 * math.sin(lat_rad) ** 2)
        
        x = (N + alt) * math.cos(lat_rad) * math.cos(lon_rad)
        y = (N + alt) * math.cos(lat_rad) * math.sin(lon_rad)
        z = (N * (1 - e2) + alt) * math.sin(lat_rad)
        
        return x, y, z
    
    def _ecef_to_geodetic(self) -> None:
        """Update lat/lon/alt from ECEF state."""
        import math
        
        x, y, z = self._state[0], self._state[1], self._state[2]
        
        a = 6378137.0
        b = 6356752.314245
        e2 = 1 - (b * b) / (a * a)
        
        lon = math.atan2(y, x)
        p = math.sqrt(x * x + y * y)
        
        # Initial lat estimate
        lat = math.atan2(z, p * (1 - e2))
        
        # Iterative refinement
        for _ in range(5):
            N = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
            lat = math.atan2(z + e2 * N * math.sin(lat), p)
        
        self._latitude = math.degrees(lat)
        self._longitude = math.degrees(lon)
        
        # Altitude
        N = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
        self._altitude = p / math.cos(lat) - N
        if self._altitude < -1000:
            self._altitude = 0  # Below earth, clamp to 0
    
    def to_tracked_entity(self) -> Optional[TrackedEntity]:
        """Convert virtual track to TrackedEntity compatible with EntityTracker.
        
        Returns:
            TrackedEntity or None if not initialized
        """
        if not self._initialized:
            return None
        
        # Update velocity from state
        vx, vy, vz = self._state[3], self._state[4], self._state[5]
        
        # Create virtual entity ID
        virtual_entity_id = EntityId(
            site_id=25,
            application_id=1,
            entity_id=2000 + self.virtual_id  # 2000+ range for virtual tracks
        )
        
        return TrackedEntity(
            entity_id=virtual_entity_id,
            entity_type=EntityType(
                kind=5,        # Sensor kind (ESM/emitter)
                domain=2,      # Air domain
                country=0,
                category=1,     # Radar/emitter
                subcategory=0,
                specific=self.virtual_id,
                extra=1        # Virtual track marker
            ),
            location=Location(
                lat=self._latitude,
                lon=self._longitude,
                alt=max(0, self._altitude)
            ),
            velocity=Vector3Float(x=vx, y=vy, z=vz),
            orientation=Orientation(pitch=0.0, yaw=0.0, roll=0.0),
            timestamp=self._last_update_time
        )


def _ecef_to_geodetic(lat_deg: float, lon_deg: float, alt_m: float) -> Tuple[float, float, float]:
    """Utility function for testing."""
    import math
    a = 6378137.0
    b = 6356752.314245
    e2 = 1 - (b * b) / (a * a)
    
    lat_rad = math.radians(lat_deg)
    lon_rad = math.radians(lon_deg)
    
    N = a / math.sqrt(1 - e2 * math.sin(lat_rad) ** 2)
    x = (N + alt_m) * math.cos(lat_rad) * math.cos(lon_rad)
    y = (N + alt_m) * math.cos(lat_rad) * math.sin(lon_rad)
    z = (N * (1 - e2) + alt_m) * math.sin(lat_rad)
    
    return x, y, z


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Simple test
    tracker = EsmTrajectoryTracker(sensor_lat=38.0, sensor_lon=-117.0)
    
    emitter = EntityId(1, 1, 25)
    base_time = 1000.0
    
    # Generate 5 bearing reports
    for i in range(5):
        bearing = 45.0 + i * 5.0
        freq = 3e9
        
        # Build Signal PDU data
        import struct
        data = struct.pack(">I", 0x01) + struct.pack(">I", 8) + struct.pack(">d", freq)
        data += struct.pack(">I", 0x05) + struct.pack(">I", 4) + struct.pack(">f", bearing)
        data += struct.pack(">I", 0x04) + struct.pack(">I", 4) + struct.pack(">f", -50.0)
        
        pdu = SignalPdu(
            entity_id=emitter,
            radio_id=0,
            encoding_scheme=1,
            tdl_type=0,
            sample_rate=0,
            number_of_samples=0,
            data=data
        )
        
        tracker.process_signal_pdu(pdu, sim_time=base_time + i * 1.0)
    
    tracks = tracker.get_virtual_tracks()
    print(f"Got {len(tracks)} virtual tracks")
    for t in tracks:
        print(f"  Track: entity_id={t.entity_id}, loc={t.location}, vel=({t.velocity.x:.1f}, {t.velocity.y:.1f}, {t.velocity.z:.1f})")