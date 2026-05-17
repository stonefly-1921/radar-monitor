# Entity Tracker - Track entities from DIS Entity State PDUs

import threading
from dataclasses import dataclass, field
from typing import Dict, Optional, List
import time

from src.core.dis.dis_protocol import EntityId, EntityType, Vector3Double, Orientation, Vector3Float


@dataclass
class Location:
    """Geographic location."""
    lat: float   # degrees North
    lon: float   # degrees East
    alt: float   # meters MSL

    def __str__(self):
        return f"({self.lat:.4f}°, {self.lon:.4f}°, {self.alt:.0f}m)"


@dataclass
class TrackedEntity:
    """A single tracked entity."""
    entity_id: EntityId
    entity_type: EntityType
    location: Location
    velocity: Vector3Float  # m/s (ECEF velocity)
    orientation: Orientation  # radians
    timestamp: float = 0.0  # simulation time in seconds

    # Entity category (derived from entity_type)
    @property
    def category_name(self) -> str:
        """Human-readable category from entity type."""
        kind = self.entity_type.kind
        domain = self.entity_type.domain
        category = self.entity_type.category

        if kind == 1 and domain == 1:  # Platform - Land
            return "LAND"
        elif kind == 1 and domain == 2:  # Platform - Air
            return "AIR"
        elif kind == 1 and domain == 3:  # Platform - Surface
            return "SURFACE"
        elif kind == 1 and domain == 4:  # Platform - Subsurface
            return "SUBSURFACE"
        elif kind == 2:  # Munition
            return "MUNITION"
        elif kind == 3:  # Lifeform
            return "LIFEFORM"
        elif kind == 5:  # Sensor/Emitter
            return "SENSOR"
        return "UNKNOWN"


class EntityTracker:
    """Thread-safe entity tracker maintaining all live entities.

    Entities are stored by EntityId. Updated when Entity State PDU received.
    Stale entities can be detected by age.
    """

    def __init__(self, stale_threshold_sec: float = 10.0):
        """Initialize tracker.

        Args:
            stale_threshold_sec: Entities older than this are considered stale.
        """
        self._entities: Dict[str, TrackedEntity] = {}
        self._lock = threading.RLock()
        self.stale_threshold_sec = stale_threshold_sec

    def _entity_key(self, entity_id: EntityId) -> str:
        return f"{entity_id.site_id}:{entity_id.application_id}:{entity_id.entity_id}"

    def add(self, entity: TrackedEntity) -> None:
        """Add a new tracked entity.

        Args:
            entity: TrackedEntity to add.
        """
        with self._lock:
            self._entities[self._entity_key(entity.entity_id)] = entity

    def update(self, entity_id: EntityId, location: Location, velocity: Vector3Float,
               orientation: Orientation, timestamp: float, entity_type: EntityType = None) -> None:
        """Update an existing tracked entity or add if new.

        Args:
            entity_id: Entity identifier.
            location: New location.
            velocity: New velocity vector.
            orientation: New orientation.
            timestamp: Simulation time.
            entity_type: Entity type (only used when adding new entity).
        """
        key = self._entity_key(entity_id)
        with self._lock:
            if key in self._entities:
                existing = self._entities[key]
                existing.location = location
                existing.velocity = velocity
                existing.orientation = orientation
                existing.timestamp = timestamp
            elif entity_type is not None:
                self._entities[key] = TrackedEntity(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    location=location,
                    velocity=velocity,
                    orientation=orientation,
                    timestamp=timestamp,
                )

    def remove(self, entity_id: EntityId) -> bool:
        """Remove an entity.

        Args:
            entity_id: Entity to remove.

        Returns:
            True if entity was removed, False if not found.
        """
        key = self._entity_key(entity_id)
        with self._lock:
            if key in self._entities:
                del self._entities[key]
                return True
            return False

    def get(self, entity_id: EntityId) -> Optional[TrackedEntity]:
        """Get an entity by ID.

        Args:
            entity_id: Entity identifier.

        Returns:
            TrackedEntity or None if not found.
        """
        with self._lock:
            return self._entities.get(self._entity_key(entity_id))

    def get_all(self) -> List[TrackedEntity]:
        """Get all tracked entities.

        Returns:
            List of all TrackedEntity objects.
        """
        with self._lock:
            return list(self._entities.values())

    def count(self) -> int:
        """Get number of tracked entities."""
        with self._lock:
            return len(self._entities)

    def get_by_category(self, category_prefix: str) -> List[TrackedEntity]:
        """Get entities matching category prefix.

        Args:
            category_prefix: e.g. "AIR", "LAND", "SURFACE"

        Returns:
            List of matching entities.
        """
        with self._lock:
            return [e for e in self._entities.values()
                   if e.category_name.startswith(category_prefix)]

    def get_stale(self, current_time: float) -> List[TrackedEntity]:
        """Get entities that haven't been updated recently.

        Args:
            current_time: Current simulation time.

        Returns:
            List of stale entities.
        """
        with self._lock:
            return [e for e in self._entities.values()
                   if (current_time - e.timestamp) > self.stale_threshold_sec]

    def clear(self) -> None:
        """Remove all entities."""
        with self._lock:
            self._entities.clear()

    def __len__(self) -> int:
        return self.count()

    def __repr__(self) -> str:
        return f"EntityTracker(count={self.count()})"