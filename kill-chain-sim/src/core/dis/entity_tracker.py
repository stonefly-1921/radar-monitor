# Entity Tracker - Track entities from DIS Entity State PDUs

import threading
from dataclasses import dataclass, field
from typing import Dict, Optional, List
import time
import logging

from src.core.dis.dis_protocol import EntityId, EntityType, Vector3Double, Orientation, Vector3Float

logger = logging.getLogger(__name__)


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
        """Human-readable category from entity type.

        DIS entity type encoding (kind:domain:country:category:subcategory:specific:extra):
        - kind 1 = Platform, 2 = Munition, 3 = Lifeform, 5 = Sensor, 7 = Radio, etc.
        - domain 1 = Land, 2 = Air, 3 = Surface, 4 = Subsurface, 5 = Space

        Many AFSIM scenarios use 0:0:X for country-only identification (X = country code).
        We derive category from country code ranges and specific/subcategory patterns.
        """
        kind = self.entity_type.kind
        domain = self.entity_type.domain
        country = self.entity_type.country
        category = self.entity_type.category
        subcategory = self.entity_type.subcategory
        specific = self.entity_type.specific

        # Platform kinds (1)
        if kind == 1:
            if domain == 1:
                return "LAND"
            elif domain == 2:
                return "AIR"
            elif domain == 3:
                return "SURFACE"
            elif domain == 4:
                return "SUBSURFACE"
            elif domain == 5:
                return "SPACE"
            return "UNKNOWN_PLATFORM"

        # Munition kind (2) - often has country code for nationality
        if kind == 2:
            return "MUNITION"

        # Lifeform kind (3)
        if kind == 3:
            return "LIFEFORM"

        # Sensor/Emitter kind (5)
        if kind == 5:
            return "SENSOR"

        # Radio kind (7)
        if kind == 7:
            return "RADIO"

        # Handle AFSIM's entity type format: country field carries entity classification info
        # when kind=0 (uninitialized). Common AFSIM country codes:
        # 6400 = test/unknown, 840 = USA, 276 = Germany, 250 = France, 826 = UK, 356 = India, etc.
        # specific field can indicate sub-type: 1 = fighter, 2 = bomber, etc.
        if kind == 0 and country != 0:
            # If specific > 0, treat as aircraft (typical for air targets)
            if specific > 0:
                return "AIR"
            # If subcategory > 0, could be a specific platform type
            if subcategory > 0:
                return "AIR"
            # Unknown entity with country code but no type info
            return "UNKNOWN"

        return "UNKNOWN"



    # Entity side (force: blue friendly, red hostile, neutral)
    # DIS has no explicit force ID field, so we derive it from entity_type.extra
    # In AFSIM: extra=1 often means blue/friendly, extra=2 means red/hostile
    @property
    def force_side(self) -> str:
        """Force side (blue/red/neutral) derived from entity type extra field."""
        if self.entity_type.extra == 1:
            return "blue"
        elif self.entity_type.extra == 2:
            return "red"
        return "neutral"

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
        self._entity_id_map: Dict[str, int] = {}  # raw ID -> normalized ID
        self._lock = threading.RLock()
        self.stale_threshold_sec = stale_threshold_sec

    def _entity_key(self, entity_id: EntityId) -> str:
        return f"{entity_id.site_id}:{entity_id.application_id}:{entity_id.entity_id}"

    def normalize_entity_id(self, entity_id: EntityId, entity_type=None) -> EntityId:
        """Normalize entity ID to AFSIM's internal entity numbering.

        AFSIM uses the entity_type.specific field to indicate its internal
        entity ID (e.g., specific=1 -> entity 1, specific=2 -> entity 2).
        The raw entity_id.entity field (36864) is stable but does NOT match
        AFSIM's internal DIS entity ID.

        Since multiple entities can have the same raw entity field (36864)
        but different specific values, we use (entity_field, specific) as
        the mapping key to distinguish them.

        Args:
            entity_id: Raw entity ID from DIS PDU.
            entity_type: Entity type with specific field for mapping.

        Returns:
            Normalized entity ID with site=25, app=1, entity=<specific or 1-based index>.
        """
        # Use combination of entity field and specific for unique mapping
        if entity_type is not None and entity_type.specific > 0:
            key = f"{entity_id.entity_id}:{entity_type.specific}"
            normalized_entity = entity_type.specific
            logger.debug(f"Entity ID mapping: {entity_id} (specific={entity_type.specific}) -> 25:1:{normalized_entity}")
        else:
            key = str(entity_id.entity_id)
            normalized_entity = None  # Will assign sequentially

        with self._lock:
            if key not in self._entity_id_map:
                if normalized_entity is None:
                    normalized_entity = len(self._entity_id_map) + 1
                    logger.debug(f"Entity ID mapping: {entity_id} -> 25:1:{normalized_entity} (sequential fallback)")
                self._entity_id_map[key] = normalized_entity
            else:
                normalized_entity = self._entity_id_map[key]

            return EntityId(site_id=25, application_id=1, entity_id=normalized_entity)

    def add(self, entity: TrackedEntity) -> None:
        """Add a new tracked entity.

        Args:
            entity: TrackedEntity to add.
        """
        with self._lock:
            # Normalize entity ID for consistent tracking
            normalized_eid = self.normalize_entity_id(entity.entity_id)
            entity.entity_id = normalized_eid
            self._entities[self._entity_key(normalized_eid)] = entity

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
        normalized_eid = self.normalize_entity_id(entity_id, entity_type)
        key = self._entity_key(normalized_eid)
        with self._lock:
            if key in self._entities:
                existing = self._entities[key]
                existing.location = location
                existing.velocity = velocity
                existing.orientation = orientation
                existing.timestamp = timestamp
            elif entity_type is not None:
                self._entities[key] = TrackedEntity(
                    entity_id=normalized_eid,
                    entity_type=entity_type,
                    location=location,
                    velocity=velocity,
                    orientation=orientation,
                    timestamp=timestamp,
                )

    def remove(self, entity_id: EntityId) -> bool:
        """Remove an entity.

        Args:
            entity_id: Entity to remove (can be normalized or raw).

        Returns:
            True if entity was removed, False if not found.
        """
        normalized_eid = self.normalize_entity_id(entity_id)
        key = self._entity_key(normalized_eid)
        with self._lock:
            if key in self._entities:
                del self._entities[key]
                return True
            return False

    def get(self, entity_id: EntityId) -> Optional[TrackedEntity]:
        """Get an entity by ID.

        Args:
            entity_id: Entity identifier (can be raw or normalized).

        Returns:
            TrackedEntity or None if not found.
        """
        normalized_eid = self.normalize_entity_id(entity_id)
        with self._lock:
            return self._entities.get(self._entity_key(normalized_eid))

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