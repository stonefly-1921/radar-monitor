"""
Memory storage - JSON file based persistence.
"""
import json
import os
from datetime import datetime


class MemoryStorage:
    """Handles memory persistence to JSON files."""
    
    def __init__(self, storage_path=None):
        if storage_path is None:
            storage_path = os.path.join(
                os.path.dirname(__file__), "..", "io", "memory.json"
            )
        self.storage_path = storage_path
    
    def save(self, data):
        """Save memory data to file."""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load(self):
        """Load memory data from file."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return self._default_data()
    
    def _default_data(self):
        return {
            "short_term": [],
            "long_term": [],
            "summaries": [],
            "updated_at": datetime.now().isoformat()
        }
    
    def clear(self):
        """Clear all memory."""
        self.save(self._default_data())