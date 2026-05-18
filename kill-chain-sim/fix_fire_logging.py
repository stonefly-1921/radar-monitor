import re

with open('src/main.py', 'r') as f:
    content = f.read()

# Pattern to find and replace
old = '''for alloc in result.allocations:
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

            mission = self.dis_client.fire_control.create_fire_mission(
                launcher_id, target_id, Munition_id
            )
            success = self.dis_client.send_fire(mission)
            if success:
                self.stats["fire_commands_sent"] += 1'''

new = '''for alloc in result.allocations:
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
                self.stats["fire_commands_sent"] += 1'''

if old in content:
    content = content.replace(old, new)
    with open('src/main.py', 'w') as f:
        f.write(content)
    print('Replacement successful')
else:
    print('Pattern not found')