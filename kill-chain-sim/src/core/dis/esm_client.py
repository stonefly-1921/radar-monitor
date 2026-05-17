# ESM (Electronic Support Measures) Client
# Parses Signal PDUs for electronic warfare data

import struct
import logging
from dataclasses import dataclass
from typing import Optional, List

from src.core.dis.dis_protocol import EntityId, SignalPdu

logger = logging.getLogger(__name__)


# ESM emitter classification
class EmitterType:
    """Known emitter types from AFSIM DIS configuration."""
    SOJ_SBAND_JAMMER = 1
    SOJ_VHF_JAMMER = 2
    SOJ_XBAND_JAMMER = 3
    UCAV_ESM = 10
    EW_RADAR = 11
    TTR_RADAR = 12
    ACQ_RADAR = 13

    @classmethod
    def name(cls, code: int) -> str:
        names = {
            1: "SOJ_SBAND_JAMMER",
            2: "SOJ_VHF_JAMMER",
            3: "SOJ_XBAND_JAMMER",
            10: "UCAV_ESM",
            11: "EW_RADAR",
            12: "TTR_RADAR",
            13: "ACQ_RADAR",
        }
        return names.get(code, f"UNKNOWN_{code}")


@dataclass
class EsmReport:
    """Electronic Support Measures report from Signal PDU."""
    entity_id: EntityId
    radio_id: int
    emitter_type: int
    frequency_hz: float       # Hz
    pulse_width_us: float      # microseconds
    prf_hz: float             # Hz (pulse repetition frequency)
    signal_strength_dbm: float  # dBm
    bearing_deg: float         # degrees
    timestamp: float           # simulation time

    @property
    def emitter_name(self) -> str:
        return EmitterType.name(self.emitter_type)


class EsmClient:
    """Client for processing ESM/Signal PDUs.

    Maintains a list of detected emitters and their states.
    Signal PDUs carry variable data records with emitter parameters.
    """

    def __init__(self):
        self._emitters: dict = {}  # keyed by entity_id string
        self._reports: List[EsmReport] = []

    def process_signal_pdu(self, pdu: SignalPdu, sim_time: float = 0.0) -> Optional[EsmReport]:
        """Process a Signal PDU and extract ESM data.

        DIS Signal PDUs carry variable data records. For ESM, they typically contain:
        - Frequency (Hz)
        - Pulse width (μs)
        - PRF (Hz)
        - Signal strength (dBm)
        - Bearing (degrees)

        Args:
            pdu: Parsed SignalPdu object.
            sim_time: Current simulation time in seconds.

        Returns:
            EsmReport or None if parsing failed.
        """
        try:
            # Parse variable datum records from signal data
            emitter_type, frequency, pw, prf, strength, bearing = \
                self._parse_esm_data(pdu.data)

            key = str(pdu.entity_id)
            self._emitters[key] = {
                "entity_id": pdu.entity_id,
                "emitter_type": emitter_type,
                "frequency": frequency,
                "pulse_width": pw,
                "prf": prf,
                "strength": strength,
                "bearing": bearing,
                "last_update": sim_time,
            }

            report = EsmReport(
                entity_id=pdu.entity_id,
                radio_id=pdu.radio_id,
                emitter_type=emitter_type,
                frequency_hz=frequency,
                pulse_width_us=pw,
                prf_hz=prf,
                signal_strength_dbm=strength,
                bearing_deg=bearing,
                timestamp=sim_time,
            )
            self._reports.append(report)
            return report

        except Exception as e:
            logger.warning(f"Failed to parse Signal PDU: {e}")
            return None

    def _parse_esm_data(self, data: bytes) -> tuple:
        """Parse ESM data from Signal PDU data field.

        AFSIM Signal PDUs for ESM use variable datum records.
        Format is: datum_id (4 bytes) + datum_length (4 bytes) + datum_value (variable)

        Known datum IDs:
        - 0x01 = Frequency (Hz) as double
        - 0x02 = Pulse Width (μs) as float
        - 0x03 = PRF (Hz) as float
        - 0x04 = Signal Strength (dBm) as float
        - 0x05 = Bearing (degrees) as float

        Args:
            data: Raw data bytes from Signal PDU.

        Returns:
            tuple: (emitter_type, frequency, pulse_width, prf, strength, bearing)
        """
        if len(data) < 16:
            # Minimal data, return defaults
            return 0, 0.0, 0.0, 0.0, -100.0, 0.0

        emitter_type = 0
        frequency = 0.0
        pw = 0.0
        prf = 0.0
        strength = -100.0
        bearing = 0.0

        offset = 0
        while offset + 8 <= len(data):
            datum_id = struct.unpack(">I", data[offset:offset + 4])[0]
            offset += 4
            datum_len = struct.unpack(">I", data[offset:offset + 4])[0]
            offset += 4

            if offset + datum_len > len(data):
                break

            value_data = data[offset:offset + datum_len]
            offset += datum_len

            if datum_id == 0x01 and datum_len == 8:
                frequency = struct.unpack(">d", value_data)[0]
            elif datum_id == 0x02 and datum_len == 4:
                pw = struct.unpack(">f", value_data)[0]
            elif datum_id == 0x03 and datum_len == 4:
                prf = struct.unpack(">f", value_data)[0]
            elif datum_id == 0x04 and datum_len == 4:
                strength = struct.unpack(">f", value_data)[0]
            elif datum_id == 0x05 and datum_len == 4:
                bearing = struct.unpack(">f", value_data)[0]
            elif datum_id == 0x10 and datum_len == 4:
                emitter_type = struct.unpack(">I", value_data)[0]

        return emitter_type, frequency, pw, prf, strength, bearing

    def get_emitter(self, entity_id: EntityId) -> Optional[dict]:
        """Get current emitter state.

        Args:
            entity_id: Entity to look up.

        Returns:
            Emitter dict or None.
        """
        return self._emitters.get(str(entity_id))

    def get_all_emitters(self) -> List[dict]:
        """Get all tracked emitters."""
        return list(self._emitters.values())

    def get_recent_reports(self, count: int = 10) -> List[EsmReport]:
        """Get most recent ESM reports.

        Args:
            count: Maximum number of reports to return.

        Returns:
            List of recent EsmReport objects.
        """
        return self._reports[-count:]

    def clear(self) -> None:
        """Clear all emitters and reports."""
        self._emitters.clear()
        self._reports.clear()