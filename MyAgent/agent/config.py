"""
Agent configuration module.
"""
import json
import os


class AgentConfig:
    """Loads and provides access to agent configuration."""
    
    DEFAULT_CONFIG = {
        "name": "Hermes",
        "version": "1.0.0",
        "memory": {
            "short_term_max": 20,
            "long_term_enabled": True,
            "summary_threshold": 10
        },
        "session": {
            "auto_save": True,
            "max_turns_per_session": 50
        },
        "loop": {
            "max_iterations": 50,
            "tool_timeout": 30,
            "response_format": "json"
        }
    }
    
    def __init__(self, config_path=None):
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__), "..", "config", "agent_config.json"
            )
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self):
        """Load configuration from file or return defaults."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return self.DEFAULT_CONFIG.copy()
    
    def get(self, key, default=None):
        """Get a configuration value by key."""
        return self.config.get(key, default)
    
    @property
    def name(self):
        return self.config.get("name", "Hermes")
    
    @property
    def memory(self):
        return self.config.get("memory", self.DEFAULT_CONFIG["memory"])
    
    @property
    def session(self):
        return self.config.get("session", self.DEFAULT_CONFIG["session"])
    
    @property
    def loop(self):
        return self.config.get("loop", self.DEFAULT_CONFIG["loop"])
    
    @property
    def io(self):
        return self.config.get("io", {})