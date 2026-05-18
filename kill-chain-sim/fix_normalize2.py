with open('src/core/dis/entity_tracker.py', 'r') as f:
    content = f.read()

# Find the function
import re
pattern = r'(    def normalize_entity_id\(self, entity_id: EntityId, entity_type=None\) -> EntityId:.*?return EntityId\(site_id=25, application_id=1, entity_id=original_entity\))'
m = re.search(pattern, content, re.DOTALL)
if m:
    print('Found function at:', m.start(), '-', m.end())
    old_func = m.group(1)
    
    new_func = '''    def normalize_entity_id(self, entity_id: EntityId, entity_type=None) -> EntityId:
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

            return EntityId(site_id=25, application_id=1, entity_id=normalized_entity)'''
    
    content = content.replace(old_func, new_func)
    with open('src/core/dis/entity_tracker.py', 'w') as f:
        f.write(content)
    print('Replacement successful')
else:
    print('Function not found')
