#!/usr/bin/env python
"""
Kill Chain Manager - Main Entry Point

Connects to AFSIM via DIS protocol and runs the kill chain management pipeline.

Usage:
    python -m src.main --afsim-host 192.168.1.100 --exercise-id 1

For help:
    python -m src.main --help
"""

import argparse
import logging
import signal
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.dis import DisClient, EntityTracker, FireControl, EsmClient, EntityId
from src.core.dis.dis_protocol import PDU_TYPE_ENTITY_STATE, PDU_TYPE_FIRE, PDU_TYPE_DETONATION, PDU_TYPE_SIGNAL
from src.research.algorithms.milp_allocator import MilpAllocator
from src.research.evaluation.metrics_evaluator import MetricsEvaluator


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )


def parse_args():
    parser = argparse.ArgumentParser(description='Kill Chain Manager - DIS Client for AFSIM')
    parser.add_argument('--multicast-addr', default='235.7.11.27',
                       help='DIS multicast address (default: 235.7.11.27)')
    parser.add_argument('--port', type=int, default=3002,
                       help='DIS port (default: 3002)')
    parser.add_argument('--exercise-id', type=int, default=0,
                       help='DIS exercise ID (default: 0)')
    parser.add_argument('--afsim-host', default=None,
                       help='AFSIM host (if different from multicast sender)')
    parser.add_argument('--time-limit', type=float, default=30.0,
                       help='MILP solver time limit in seconds (default: 30)')
    parser.add_argument('--eval-interval', type=float, default=10.0,
                       help='Metrics evaluation interval in seconds (default: 10)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    return parser.parse_args()


class KillChainManager:
    """Main kill chain manager integrating all components."""

    def __init__(self, multicast_addr: str, port: int, exercise_id: int,
                 time_limit_sec: float = 30.0):
        self.multicast_addr = multicast_addr
        self.port = port
        self.exercise_id = exercise_id
        self.time_limit_sec = time_limit_sec

        # DIS client and components
        self.dis_client = DisClient(multicast_addr=multicast_addr, port=port, exercise_id=exercise_id)
        self.allocator = MilpAllocator(time_limit_sec=time_limit_sec)
        self.evaluator = MetricsEvaluator()

        # Tracking state
        self.start_time = None
        self.track_events = []
        self.allocation_events = []
        self.engagement_results = []

        # Statistics
        self.stats = {
            "entities_tracked": 0,
            "allocations_made": 0,
            "fire_commands_sent": 0,
            "evaluations_run": 0,
        }

        self._running = False

    def start(self):
        """Start the kill chain manager."""
        logging.info("Starting Kill Chain Manager...")
        logging.info(f"  Multicast: {self.multicast_addr}:{self.port}")
        logging.info(f"  Exercise ID: {self.exercise_id}")
        logging.info(f"  MILP Time Limit: {self.time_limit_sec}s")

        # Register DIS handlers
        self.dis_client.register_handler(PDU_TYPE_ENTITY_STATE, self.on_entity_state)
        self.dis_client.register_handler(PDU_TYPE_FIRE, self.on_fire_pdu)
        self.dis_client.register_handler(PDU_TYPE_DETONATION, self.on_detonation)
        self.dis_client.register_handler(PDU_TYPE_SIGNAL, self.on_signal)

        # Start DIS client
        self.dis_client.start()
        self.start_time = time.time()
        self._running = True

        logging.info("Kill Chain Manager started successfully")

    def stop(self):
        """Stop the kill chain manager."""
        logging.info("Stopping Kill Chain Manager...")
        self._running = False
        self.dis_client.stop()
        self._print_summary()

    def _print_summary(self):
        """Print final summary."""
        elapsed = time.time() - self.start_time if self.start_time else 0
        logging.info("=" * 50)
        logging.info("KILL CHAIN MANAGER SUMMARY")
        logging.info("=" * 50)
        logging.info(f"  Runtime: {elapsed:.1f}s")
        logging.info(f"  Entities tracked: {self.stats['entities_tracked']}")
        logging.info(f"  Allocations made: {self.stats['allocations_made']}")
        logging.info(f"  Fire commands sent: {self.stats['fire_commands_sent']}")
        logging.info(f"  Evaluations run: {self.stats['evaluations_run']}")

        if self.track_events or self.allocation_events:
            summary = self.evaluator.evaluate(
                self.track_events,
                self.allocation_events,
                self.engagement_results
            )
            logging.info(f"  Composite Score: {summary.composite_score:.1f}/100")
        logging.info("=" * 50)

    def on_entity_state(self, pdu: dict):
        """Handle Entity State PDU - track the entity."""
        self.stats["entities_tracked"] += 1
        entity_id = pdu["entity_id"]
        logging.debug(f"Entity update: {entity_id} (site={entity_id.site_id}, app={entity_id.application_id}, entity={entity_id.entity_id})")

        # Record track event
        from src.research.evaluation.metrics_evaluator import TrackEvent
        self.track_events.append(TrackEvent(
            track_id=entity_id.entity_id,
            event_type="updated",
            timestamp=time.time() - self.start_time,
            lat=pdu["location"].x if hasattr(pdu["location"], "x") else 0,
            lon=pdu["location"].y if hasattr(pdu["location"], "y") else 0,
            alt=pdu["location"].z if hasattr(pdu["location"], "z") else 0,
        ))

    def on_fire_pdu(self, pdu: dict):
        """Handle Fire PDU - weapon launch detected."""
        logging.info(f"Fire event: mission={pdu['fire_mission_index']}, "
                    f"launcher={pdu['emitting_entity_id']}, target={pdu['target_entity_id']}")

    def on_detonation(self, pdu: dict):
        """Handle Detonation PDU - engagement result."""
        result = pdu["detonation_result"]
        result_names = {0: "OTHER", 1: "DETONATION", 2: "HIT", 3: "MISS", 4: "NONE"}
        logging.info(f"Detonation: target={pdu['target_entity_id']}, result={result_names.get(result, '?')}")

        from src.research.evaluation.metrics_evaluator import EngagementResult
        self.engagement_results.append(EngagementResult(
            target_id=pdu["target_entity_id"].entity_id,
            weapon_id=pdu["Munition_id"].entity_id,
            killed=1 if result in [1, 2] else 0,
            neutralized=0,
            escaped=1 if result == 3 else 0,
            failed=1 if result in [0, 4] else 0,
            timestamp=time.time() - self.start_time,
        ))

    def on_signal(self, pdu: dict):
        """Handle Signal PDU - ESM data."""
        logging.debug(f"Signal PDU from {pdu['entity_id']}")

    def run_allocation_cycle(self):
        """Run one allocation cycle."""
        logging.info("Running allocation cycle...")

        # Get tracked entities
        entities = self.dis_client.get_tracked_entities()
        if not entities:
            logging.debug("No entities to allocate - tracker empty")
            return

        # Log all entities and their categories
        for e in entities:
            logging.debug(f"Tracked entity: {e.entity_id}, category={e.category_name}, type={e.entity_type}")

        # Convert to allocator format
        from src.research.algorithms.milp_allocator import Target, Sensor, Weapon

        targets = []
        sensors = []
        weapons = []

        for entity in entities:
            if entity.category_name == "AIR" and entity.force_side == "red":
                targets.append(Target(
                    id=entity.entity_id.entity_id,
                    priority=5.0,
                    velocity_kts=300,
                    type="aircraft",
                    lat=entity.location.lat if hasattr(entity.location, 'lat') else 0,
                    lon=entity.location.lon if hasattr(entity.location, 'lon') else 0,
                    altitude_ft=10000,
                    range_to_sensors={1: 100}
                ))

        if not targets:
            return

        # Add default sensors and weapons
        sensors.append(Sensor(1, 150, "track", 60, 30))
        sensors.append(Sensor(2, 100, "search", 45, 20))
        weapons.append(Weapon(1, 600, 0.8, 600, "sam"))   # 600km range, 600kt max speed
        weapons.append(Weapon(2, 200, 0.6, 500, "aaa"))   # 200km range, 500kt max speed

        # Solve
        result = self.allocator.solve(targets, sensors, weapons)
        self.stats["allocations_made"] += len(result.allocations)

        logging.info(f"Allocation complete: {len(result.allocations)} assigned, "
                   f"{len(result.unassigned_targets)} unassigned")

        # Send fire commands for each allocation
        for alloc in result.allocations:
            # Get the tracked entity to find its normalized entity ID
            all_entities = self.dis_client.get_tracked_entities()
            # Find entity with matching entity_id
            target_entity = None
            for e in all_entities:
                if e.entity_id.entity_id == alloc.target_id:
                    target_entity = e
                    break
            if target_entity is None:
                logging.warning(f"Target entity {alloc.target_id} not found in tracker")
                continue

            # Use the normalized entity ID from the tracker
            launcher_id = EntityId(25, 1, alloc.sensor_id)
            target_id = target_entity.entity_id  # Already normalized (25:1:X)
            Munition_id = EntityId(25, 1, alloc.weapon_id)

            logging.info(f"Fire: launcher={launcher_id}, target={target_id}, munition={Munition_id}")
            mission = self.dis_client.fire_control.create_fire_mission(
                launcher_id, target_id, Munition_id
            )
            success = self.dis_client.send_fire(mission)
            logging.info(f"Fire PDU result: {success}, total sent: {self.stats['fire_commands_sent']}")
            if success:
                self.stats["fire_commands_sent"] += 1

    def run_evaluation(self):
        """Run metrics evaluation."""
        self.stats["evaluations_run"] += 1
        summary = self.evaluator.evaluate(
            self.track_events,
            self.allocation_events,
            self.engagement_results
        )
        logging.info(f"Metrics: Composite={summary.composite_score:.1f}/100, "
                    f"Track={summary.track_continuity_score:.1f}, "
                    f"Alloc={summary.allocation_efficiency_score:.1f}, "
                    f"Engage={summary.engagement_effectiveness_score:.1f}")

    def run_loop(self, eval_interval: float = 10.0, alloc_interval: float = 5.0):
        """Main run loop.

        Args:
            eval_interval: Seconds between evaluation runs
            alloc_interval: Seconds between allocation cycles
        """
        last_eval = 0
        last_alloc = 0

        logging.info("Entering main loop (Ctrl+C to stop)...")

        try:
            while self._running:
                now = time.time()
                elapsed = now - self.start_time if self.start_time else 0

                # Process DIS PDUs
                while True:
                    pdu = self.dis_client.process_next(timeout=0.01)
                    if pdu is None:
                        break

                # Periodic allocation
                if elapsed - last_alloc >= alloc_interval:
                    self.run_allocation_cycle()
                    last_alloc = elapsed

                # Periodic evaluation
                if elapsed - last_eval >= eval_interval:
                    self.run_evaluation()
                    last_eval = elapsed

                time.sleep(0.1)

        except KeyboardInterrupt:
            logging.info("Interrupted by user")
            self.stop()


def main():
    args = parse_args()
    setup_logging(args.verbose)

    manager = KillChainManager(
        multicast_addr=args.multicast_addr,
        port=args.port,
        exercise_id=args.exercise_id,
        time_limit_sec=args.time_limit,
    )

    # Handle signals
    def signal_handler(sig, frame):
        manager.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    manager.start()
    manager.run_loop(eval_interval=args.eval_interval)


if __name__ == "__main__":
    main()