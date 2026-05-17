# Fire Control - Generate Fire PDU commands for weapon launch

import struct
import logging
from dataclasses import dataclass
from typing import Optional

from src.core.dis.dis_protocol import (
    EntityId, FirePdu, PDU_TYPE_FIRE, EXERCISE_ID_DEFAULT,
    DisTimestamp, PDU_HEADER_SIZE,
)

logger = logging.getLogger(__name__)


# Weapon assignment rule types
WEAPON_RULE_GUIDED = "guided"
WEAPON_RULE_BALLISTIC = "ballistic"
WEAPON_RULE_ARMOR = "armor"


@dataclass
class FireMission:
    """Represents a weapon fire mission."""
    mission_index: int
    launcher_id: EntityId
    target_id: EntityId
    Munition_id: EntityId
    warhead: int = 100
    fuse: int = 2
    quantity: int = 1
    rate: int = 0


class FireControl:
    """Generate Fire PDUs and manage fire missions.

    Fire PDUs are sent to AFSIM to command weapon launches.
    """

    def __init__(self, exercise_id: int = EXERCISE_ID_DEFAULT):
        self.exercise_id = exercise_id
        self._mission_counter = 0
        self._active_missions = {}

    def next_mission_index(self) -> int:
        """Get next fire mission index.

        Returns:
            Incrementing mission index (wraps at 2^32).
        """
        self._mission_counter = (self._mission_counter + 1) % (2**32)
        return self._mission_counter

    def create_fire_mission(self, launcher_id: EntityId, target_id: EntityId,
                            Munition_id: EntityId, warhead: int = 100,
                            fuse: int = 2) -> FireMission:
        """Create a new fire mission.

        Args:
            launcher_id: Entity firing the weapon.
            target_id: Target entity.
            Munition_id: Munition type being fired.
            warhead: Warhead type code.
            fuse: Fuse type code.

        Returns:
            FireMission object.
        """
        mission = FireMission(
            mission_index=self.next_mission_index(),
            launcher_id=launcher_id,
            target_id=target_id,
            Munition_id=Munition_id,
            warhead=warhead,
            fuse=fuse,
        )
        self._active_missions[mission.mission_index] = mission
        return mission

    def generate_fire_pdu(self, mission: FireMission) -> FirePdu:
        """Generate a Fire PDU for a mission.

        Args:
            mission: FireMission to encode.

        Returns:
            FirePdu object ready to be encoded and sent.
        """
        return FirePdu(
            fire_mission_index=mission.mission_index,
            emitting_entity_id=mission.launcher_id,
            target_entity_id=mission.target_id,
            Munition_id=mission.Munition_id,
            warhead=mission.warhead,
            fuse=mission.fuse,
            quantity=mission.quantity,
            rate=mission.rate,
        )

    def build_fire_pdu_bytes(self, mission: FireMission) -> bytes:
        """Build raw Fire PDU bytes ready to send.

        This builds a complete DIS Fire PDU with header.

        Args:
            mission: FireMission to encode.

        Returns:
            Complete PDU bytes with header.
        """
        fire_pdu = self.generate_fire_pdu(mission)
        fire_data = fire_pdu.encode()

        # Build PDU header
        timestamp = DisTimestamp.now()
        header = struct.pack(
            ">BBBBHH",
            6,                      # protocol version
            self.exercise_id,       # exercise ID
            PDU_TYPE_FIRE,          # pdu type = 2
            1,                      # family = entity_management
            0,                      # length (placeholder)
            0,                      # padding
        )

        # Timestamp is first 5 bytes
        pdu_bytes = timestamp.encode() + header
        total_length = len(pdu_bytes) + len(fire_data)
        # Set length in header (offset: timestamp=0, version=5, exercise=6, type=7, family=8,
        # length at bytes 9-10 from start of header... but we appended timestamp before header)
        # Actually timestamp is first, then header fields. So length field is at byte offset 5+4=9 from start
        pdu_bytes = pdu_bytes[:9] + struct.pack(">H", total_length) + pdu_bytes[11:]
        pdu_bytes += fire_data

        return pdu_bytes

    def complete_mission(self, mission_index: int) -> bool:
        """Mark a mission as completed and remove from active missions.

        Args:
            mission_index: Mission to complete.

        Returns:
            True if mission was found and removed.
        """
        if mission_index in self._active_missions:
            del self._active_missions[mission_index]
            return True
        return False

    @property
    def active_mission_count(self) -> int:
        return len(self._active_missions)


# Default fire control instance
_default_fire_control: Optional[FireControl] = None


def get_fire_control() -> FireControl:
    """Get the default FireControl instance."""
    global _default_fire_control
    if _default_fire_control is None:
        _default_fire_control = FireControl()
    return _default_fire_control