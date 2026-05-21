"""
Persona module - Agent personality and behavior configuration.
"""
import json
import os
from datetime import datetime


class Persona:
    """Defines the Agent's personality, guidelines, and style."""
    
    DEFAULT_PERSONA = {
        "name": "Hermes",
        "role": "智能助手",
        "version": "1.0.0",
        "guidelines": [
            "在执行前先理解任务目标",
            "使用最少的工具完成目标",
            "复杂任务分步骤执行",
            "保持回复简洁清晰",
            "如果不确定，先确认再执行"
        ],
        "style": {
            "language": "zh-CN",
            "emoji": False,
            "format": "professional"
        },
        "capabilities": [
            "文件操作",
            "命令执行",
            "Python脚本执行",
            "文档和知识库管理"
        ]
    }
    
    def __init__(self, config_path=None):
        self.config_path = config_path or os.path.join(
            os.path.dirname(__file__), "..", "config", "persona.json"
        )
        self.config = self._load_config()
    
    def _load_config(self):
        """Load persona configuration from file or use default."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return self.DEFAULT_PERSONA.copy()
    
    @property
    def name(self):
        return self.config.get("name", "Hermes")
    
    @property
    def role(self):
        return self.config.get("role", "智能助手")
    
    @property
    def guidelines(self):
        return self.config.get("guidelines", [])
    
    @property
    def style(self):
        return self.config.get("style", {})
    
    @property
    def capabilities(self):
        return self.config.get("capabilities", [])
    
    def get_system_prompt(self):
        """Generate the system prompt for the LLM."""
        guidelines_text = "\n".join([f"- {g}" for g in self.guidelines])
        capabilities_text = ", ".join(self.capabilities)
        
        return f"""你是 {self.name}，一个{self.role}。

你的行为准则：
{guidelines_text}

你的能力范围：{capabilities_text}

请根据用户的需求，选择合适的工具来完成任务。"""
    
    def to_dict(self):
        return self.config.copy()


class PersonaConfig:
    """Configuration loader for the Agent."""
    
    def __init__(self, config_file=None):
        if config_file is None:
            config_file = os.path.join(
                os.path.dirname(__file__), "..", "config", "agent_config.json"
            )
        self.config_file = config_file
        self.config = self._load()
    
    def _load(self):
        """Load agent configuration."""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def get(self, key, default=None):
        return self.config.get(key, default)
    
    @property
    def name(self):
        return self.config.get("name", "Hermes")
    
    @property
    def memory_config(self):
        return self.config.get("memory", {})
    
    @property
    def loop_config(self):
        return self.config.get("loop", {})
    
    @property
    def io_config(self):
        return self.config.get("io", {})