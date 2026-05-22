"""
Base class for all tools.
"""
from abc import ABC, abstractmethod


class Tool(ABC):
    """Base class for all Agent tools."""
    
    name = "base_tool"
    description = "A base tool class"
    parameters = []
    
    @abstractmethod
    def execute(self, **kwargs):
        """
        Execute the tool with given parameters.
        
        Returns:
            dict: Result containing 'success', 'result', and optional 'error'
        """
        pass
    
    def validate(self, params):
        """
        Validate tool parameters.
        
        Args:
            params: dict of parameters
            
        Returns:
            tuple: (is_valid, error_message)
        """
        return True, None
    
    def get_spec(self):
        """Get tool specification for LLM."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }