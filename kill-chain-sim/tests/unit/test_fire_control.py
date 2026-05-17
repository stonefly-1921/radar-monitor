# Fire Control Tests

import unittest
from src.core.dis.fire_control import FireControl, FireMission, WEAPON_RULE_GUIDED
from src.core.dis.dis_protocol import EntityId


class TestFireControl(unittest.TestCase):
    def test_next_mission_index(self):
        fc = FireControl()
        idx1 = fc.next_mission_index()
        idx2 = fc.next_mission_index()
        self.assertNotEqual(idx1, idx2)
        self.assertEqual(idx2, idx1 + 1)

    def test_create_fire_mission(self):
        fc = FireControl()
        launcher = EntityId(1, 1, 10)
        target = EntityId(2, 1, 20)
        Munition = EntityId(1, 1, 99)

        mission = fc.create_fire_mission(launcher, target, Munition, warhead=100, fuse=2)

        self.assertIsInstance(mission, FireMission)
        self.assertEqual(mission.launcher_id, launcher)
        self.assertEqual(mission.target_id, target)
        self.assertEqual(mission.Munition_id, Munition)
        self.assertEqual(mission.warhead, 100)
        self.assertEqual(mission.fuse, 2)
        self.assertGreater(mission.mission_index, 0)

    def test_generate_fire_pdu(self):
        fc = FireControl()
        mission = fc.create_fire_mission(
            EntityId(1, 1, 10),
            EntityId(2, 1, 20),
            EntityId(1, 1, 99),
        )
        pdu = fc.generate_fire_pdu(mission)
        self.assertEqual(pdu.PDU_TYPE, 2)
        self.assertEqual(pdu.fire_mission_index, mission.mission_index)

    def test_build_fire_pdu_bytes(self):
        fc = FireControl()
        mission = fc.create_fire_mission(
            EntityId(1, 1, 10),
            EntityId(2, 1, 20),
            EntityId(1, 1, 99),
        )
        pdu_bytes = fc.build_fire_pdu_bytes(mission)
        self.assertIsInstance(pdu_bytes, bytes)
        self.assertGreater(len(pdu_bytes), 30)

    def test_complete_mission(self):
        fc = FireControl()
        mission = fc.create_fire_mission(
            EntityId(1, 1, 10),
            EntityId(2, 1, 20),
            EntityId(1, 1, 99),
        )
        self.assertEqual(fc.active_mission_count, 1)
        fc.complete_mission(mission.mission_index)
        self.assertEqual(fc.active_mission_count, 0)


if __name__ == '__main__':
    unittest.main()