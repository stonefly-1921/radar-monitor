#!/usr/bin/env python3
"""
DIS Track Monitor - Listens for AFSIM Entity State PDUs on multicast
Extracts and displays IADS track information in real-time
"""

import socket
import struct
import logging
import time
from src.core.dis.dis_protocol import (
    EntityId, EntityStatePdu, PDU_TYPE_ENTITY_STATE,
    PDU_HEADER_SIZE,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s'
)
logger = logging.getLogger(__name__)

MULTICAST_ADDR = "235.7.11.27"
PORT = 3002

# Entity type (2:1:225:50:8:0:0) = UCAV
UCAV_KIND = 2
UCAV_DOMAIN = 1
UCAV_COUNTRY = 225
UCAV_CATEGORY = 50
UCAV_SUBCATEGORY = 8


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', PORT))
    mreq = struct.pack("4sH", socket.inet_aton(MULTICAST_ADDR), PORT)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    sock.settimeout(1.0)

    logger.info(f"Listening for DIS on {MULTICAST_ADDR}:{PORT}")
    logger.info("Waiting for AFSIM entity state PDUs...")

    pdu_buf = bytearray(1024)
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            if len(data) < PDU_HEADER_SIZE:
                continue

            pdu_type = struct.unpack("B", data[1:2])[0]

            if pdu_type == PDU_TYPE_ENTITY_STATE:
                pdu = EntityStatePdu.from_bytes(data)
                ent = pdu.entity

                # Decode entity type
                kind = ent.entity_type.kind
                domain = ent.entity_type.domain
                country = ent.entity_type.country
                cat = ent.entity_type.category
                subcat = ent.entity_type.subcategory

                loc = ent.entity_location
                lat = loc.latitude_deg
                lon = loc.longitude_deg
                alt = loc.altitude_m

                # Show all entities with their full entity type
                logger.info(
                    f"ESPDU [{addr[0]}] "
                    f"({kind}:{domain}:{country}:{cat}:{subcat}) "
                    f"ID={ent.id.site}:{ent.id.application}:{ent.id.entity} "
                    f"pos=({lat:.4f}, {lon:.4f}, {alt:.1f}m) "
                    f"vel=({pdu.entity.velocity.x:.1f}, {pdu.entity.velocity.y:.1f}, {pdu.entity.velocity.z:.1f})"
                )

        except socket.timeout:
            pass
        except Exception as e:
            logger.error(f"Error: {e}")

        time.sleep(0.01)


if __name__ == "__main__":
    main()