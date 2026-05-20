#!/usr/bin/env python3
"""
AFSIM Event File Parser - Extracts IADS tracks from AFSIM .evt event file
and outputs track data to a file for the Kill Chain simulator

Monitors the event file continuously and outputs track data in a format
suitable for the Kill Chain SHM interface.
"""

import os
import re
import time
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s'
)
logger = logging.getLogger(__name__)

EVT_FILE = r"D:\afsim-2.9.0-win64\output\kill_chain.evt"
TRACK_OUTPUT_FILE = r"D:\afsim-2.9.0-win64\output\iads_tracks.txt"

# Patterns for parsing event lines
PATTERNS = {
    'LOCAL_TRACK_INITIATED': re.compile(
        r'^(\S+)\s+(LOCAL_TRACK_INITIATED)\s+(\S+)\s+(\S+)\s+TrackId:\s*(\S+)\s+'
        r'Start_Time:\s*(\S+)\s+Update_Time:\s*(\S+)\s+'
        r'Track:\s+LLA:\s+([\d:]+[ns])\s+([\d:]+[ew])\s+([\d.]+)\s*m\s+'
        r'Flags:\s*(\S+)'
    ),
    'LOCAL_TRACK_UPDATED': re.compile(
        r'^(\S+)\s+(LOCAL_TRACK_UPDATED)\s+(\S+)\s+(\S+)\s+TrackId:\s*(\S+)\s+'
        r'Update_Time:\s*(\S+)\s+Update_Count:\s*(\d+)\s+'
        r'Track:\s+LLA:\s+([\d:]+[ns])\s+([\d:]+[ew])\s+([\d.]+)\s*m'
    ),
    'TASK_ASSIGNED': re.compile(
        r'^(\S+)\s+(TASK_ASSIGNED)\s+(\S+)\s+(\S+)\s+(\S+)\s+'
        r'Task_Type:\s*(\S+)\s+Resource:\s*(\S+)'
    ),
    'WEAPON_FIRED': re.compile(
        r'^(\S+)\s+(WEAPON_FIRED)\s+(\S+)\s+Target:\s*(\S+)'
    ),
}

def parse_ll_angle(s):
    """Parse AFSIM lat/lon angle like '38:16:36.00n' to decimal degrees"""
    match = re.match(r'(\d+):(\d+):([\d.]+)([nsNS])', s)
    if not match:
        return None
    deg, min_, sec, sign = int(match.group(1)), int(match.group(2)), float(match.group(3)), match.group(4).lower()
    dec = deg + min_/60 + sec/3600
    return dec if sign == 'n' else -dec

def parse_lon_angle(s):
    """Parse AFSIM lon angle like '116:19:48.00w' to decimal degrees"""
    match = re.match(r'(\d+):(\d+):([\d.]+)([ewEW])', s)
    if not match:
        return None
    deg, min_, sec, sign = int(match.group(1)), int(match.group(2)), float(match.group(3)), match.group(4).lower()
    dec = deg + min_/60 + sec/3600
    return dec if sign == 'e' else -dec

def format_tracks(tracks, sim_time):
    """Format track data for output file"""
    lines = [f"# AFSIM IADS Tracks at T={sim_time:.1f}s"]
    for track_id, data in sorted(tracks.items()):
        lat, lon, alt = data['lat'], data['lon'], data['alt']
        lines.append(
            f"TRACK: {track_id} lat={lat:.6f} lon={lon:.6f} alt={alt:.1f}m "
            f"state={data['state']} source={data['source']}"
        )
    lines.append(f"# Total tracks: {len(tracks)}")
    return '\n'.join(lines)

def main():
    logger.info(f"Monitoring {EVT_FILE} for IADS track events")
    logger.info(f"Outputting to {TRACK_OUTPUT_FILE}")

    tracks = {}  # track_id -> {lat, lon, alt, state, source}
    last_size = 0
    last_sim_time = "0"
    poll_interval = 1.0

    while True:
        try:
            if not os.path.exists(EVT_FILE):
                time.sleep(poll_interval)
                continue

            file_size = os.path.getsize(EVT_FILE)

            # Read only new content
            with open(EVT_FILE, 'r', encoding='utf-8', errors='replace') as f:
                if file_size > last_size:
                    f.seek(max(0, last_size - 2000))  # Seek back a bit for partial lines
                    lines = f.readlines()
                    if last_size > 0:
                        lines = lines[-(file_size - last_size):]
                    last_size = file_size

                    for line in lines:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue

                        # Extract simulation time from line start
                        time_match = re.match(r'^(\d+:\d+:\d+\.\d+)', line)
                        if time_match:
                            last_sim_time = time_match.group(1)

                        # Parse LOCAL_TRACK_INITIATED
                        m = PATTERNS['LOCAL_TRACK_INITIATED'].match(line)
                        if m:
                            _, event_type, originator, target, track_id = m.groups()[:5]
                            lat_str = m.group(8)
                            lon_str = m.group(9)
                            alt_str = m.group(10)
                            lat = parse_ll_angle(lat_str)
                            lon = parse_lon_angle(lon_str)
                            alt = float(alt_str)
                            if lat is not None and lon is not None:
                                tracks[track_id] = {
                                    'lat': lat, 'lon': lon, 'alt': alt,
                                    'state': 'INITIATED',
                                    'source': originator
                                }
                            continue

                        # Parse LOCAL_TRACK_UPDATED
                        m = PATTERNS['LOCAL_TRACK_UPDATED'].match(line)
                        if m:
                            _, event_type, originator, target, track_id = m.groups()[:5]
                            lat_str = m.group(8)
                            lon_str = m.group(9)
                            alt_str = m.group(10)
                            lat = parse_ll_angle(lat_str)
                            lon = parse_lon_angle(lon_str)
                            alt = float(alt_str)
                            if lat is not None and lon is not None:
                                if track_id in tracks:
                                    tracks[track_id].update({
                                        'lat': lat, 'lon': lon, 'alt': alt,
                                        'state': 'UPDATED'
                                    })
                                else:
                                    tracks[track_id] = {
                                        'lat': lat, 'lon': lon, 'alt': alt,
                                        'state': 'UPDATED',
                                        'source': originator
                                    }
                            continue

                        # Parse TASK_ASSIGNED
                        m = PATTERNS['TASK_ASSIGNED'].match(line)
                        if m:
                            sim_time, event_type, assignee, target, commander = m.groups()[:5]
                            task_type = m.group(6)
                            logger.info(
                                f"TASK_ASSIGNED: {assignee} <- {commander} "
                                f"target={target} type={task_type}"
                            )
                            continue

                        # Parse WEAPON_FIRED
                        m = PATTERNS['WEAPON_FIRED'].match(line)
                        if m:
                            sim_time, event_type, platform, target = m.groups()[:4]
                            logger.info(f"WEAPON_FIRED: {platform} -> {target}")
                            continue

                    # Write track output
                    if tracks:
                        output = format_tracks(tracks, sum(
                            int(x) * 60**i for i, x in
                            enumerate(reversed(last_sim_time.split(':')))
                        ) if last_sim_time != "0" else 0)
                        with open(TRACK_OUTPUT_FILE, 'w') as f:
                            f.write(output + '\n')

            time.sleep(poll_interval)

        except KeyboardInterrupt:
            logger.info("Shutting down")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            time.sleep(poll_interval)

if __name__ == "__main__":
    main()