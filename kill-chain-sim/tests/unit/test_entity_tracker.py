# Integration test for DIS Client (Task 9)

import unittest
from src.core.dis.dis_protocol import EntityId, EntityType, Vector3Double, Vector3Float, Orientation
from src.core.dis.entity_tracker import EntityTracker, Location, TrackedEntity


class TestEntityTracker(unittest.TestCase):
    def test_add_entity(self):
        tracker = EntityTracker()
        entity = TrackedEntity(
            entity_id=EntityId(1, 1, 100),
            entity_type=EntityType(2, 1, 222, 2, 1, 1, 0),
            location=Location(30.0, 120.0, 5000),
            velocity=Vector3Float(100.0, 50.0, 0.0),
            orientation=Orientation(0.0, 1.57, 0.0),
            timestamp=10.0,
        )
        tracker.add(entity)
        self.assertEqual(tracker.count(), 1)

    def test_update_entity(self):
        tracker = EntityTracker()
        entity = TrackedEntity(
            entity_id=EntityId(1, 1, 100),
            entity_type=EntityType(2, 1, 222, 2, 1, 1, 0),
            location=Location(30.0, 120.0, 5000),
            velocity=Vector3Float(100.0, 50.0, 0.0),
            orientation=Orientation(0.0, 1.57, 0.0),
            timestamp=10.0,
        )
        tracker.add(entity)

        tracker.update(
            EntityId(1, 1, 100),
            Location(30.1, 120.1, 5100),
            Vector3Float(110.0, 55.0, 0.0),
            Orientation(0.0, 1.57, 0.0),
            timestamp=11.0,
        )

        updated = tracker.get(EntityId(1, 1, 100))
        self.assertIsNotNone(updated)
        self.assertAlmostEqual(updated.location.lat, 30.1, places=2)

    def test_remove_entity(self):
        tracker = EntityTracker()
        entity = TrackedEntity(
            entity_id=EntityId(1, 1, 100),
            entity_type=EntityType(2, 1, 222, 2, 1, 1, 0),
            location=Location(30.0, 120.0, 5000),
            velocity=Vector3Float(100.0, 50.0, 0.0),
            orientation=Orientation(0.0, 1.57, 0.0),
            timestamp=10.0,
        )
        tracker.add(entity)
        result = tracker.remove(EntityId(1, 1, 100))
        self.assertTrue(result)
        self.assertEqual(tracker.count(), 0)

    def test_get_by_category(self):
        tracker = EntityTracker()

        # Add air entity
        tracker.add(TrackedEntity(
            entity_id=EntityId(1, 1, 1),
            entity_type=EntityType(1, 2, 222, 1, 9, 10, 0),  # Air domain
            location=Location(30.0, 120.0, 5000),
            velocity=Vector3Float(100, 0, 0),
            orientation=Orientation(0, 0, 0),
            timestamp=10.0,
        ))

        # Add land entity
        tracker.add(TrackedEntity(
            entity_id=EntityId(1, 1, 2),
            entity_type=EntityType(1, 1, 222, 28, 4, 3, 0),  # Land domain
            location=Location(31.0, 121.0, 100),
            velocity=Vector3Float(0, 0, 0),
            orientation=Orientation(0, 0, 0),
            timestamp=10.0,
        ))

        air_entities = tracker.get_by_category("AIR")
        self.assertEqual(len(air_entities), 1)
        self.assertEqual(air_entities[0].entity_id.entity_id, 1)

    def test_category_name(self):
        entity = TrackedEntity(
            entity_id=EntityId(1, 1, 1),
            entity_type=EntityType(1, 2, 222, 1, 9, 10, 0),  # kind=1, domain=2 (air)
            location=Location(30.0, 120.0, 5000),
            velocity=Vector3Float(100, 0, 0),
            orientation=Orientation(0, 0, 0),
            timestamp=10.0,
        )
        self.assertEqual(entity.category_name, "AIR")

    def test_stale_entities(self):
        tracker = EntityTracker(stale_threshold_sec=5.0)
        tracker.add(TrackedEntity(
            entity_id=EntityId(1, 1, 1),
            entity_type=EntityType(1, 2, 222, 1, 9, 10, 0),
            location=Location(30.0, 120.0, 5000),
            velocity=Vector3Float(100, 0, 0),
            orientation=Orientation(0, 0, 0),
            timestamp=10.0,
        ))
        tracker.add(TrackedEntity(
            entity_id=EntityId(1, 1, 2),
            entity_type=EntityType(1, 2, 222, 1, 9, 10, 0),
            location=Location(30.0, 120.0, 5000),
            velocity=Vector3Float(100, 0, 0),
            orientation=Orientation(0, 0, 0),
            timestamp=20.0,  # More recent
        ))

        stale = tracker.get_stale(current_time=22.0)
        self.assertEqual(len(stale), 1)
        self.assertEqual(stale[0].entity_id.entity_id, 1)


if __name__ == '__main__':
    unittest.main()