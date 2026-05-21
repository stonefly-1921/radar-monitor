"""
Tests for Persona module.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agent.persona import Persona, PersonaConfig
from agent.config import AgentConfig


def test_persona_default():
    """Test that Persona loads with correct defaults."""
    p = Persona()
    assert p.name == "Hermes"
    assert p.role == "智能助手"
    assert len(p.guidelines) > 0
    print("[PASS] test_persona_default")


def test_persona_system_prompt():
    """Test system prompt generation."""
    p = Persona()
    prompt = p.get_system_prompt()
    assert "Hermes" in prompt
    assert "智能助手" in prompt
    print("[PASS] test_persona_system_prompt")


def test_persona_to_dict():
    """Test persona serialization."""
    p = Persona()
    d = p.to_dict()
    assert "name" in d
    assert "guidelines" in d
    print("[PASS] test_persona_to_dict")


def test_agent_config():
    """Test AgentConfig loading."""
    config = AgentConfig()
    assert config.name == "Hermes"
    assert config.memory is not None
    assert config.loop is not None
    print("[PASS] test_agent_config")


if __name__ == "__main__":
    test_persona_default()
    test_persona_system_prompt()
    test_persona_to_dict()
    test_agent_config()
    print("\n[OK] All persona tests passed!")