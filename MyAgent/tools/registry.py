"""
Tool registry - manages tool registration and retrieval.
"""
import os
import json


class ToolRegistry:
    """
    Central registry for all available tools.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
            cls._instance._initialized = False
        return cls._instance
    
    def register(self, tool):
        """
        Register a tool.
        
        Args:
            tool: Tool instance
        """
        self._tools[tool.name] = tool
        self._initialized = True
    
    def unregister(self, name):
        """Unregister a tool by name."""
        if name in self._tools:
            del self._tools[name]
    
    def get(self, name):
        """
        Get a tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool instance or None
        """
        return self._tools.get(name)
    
    def list_tools(self):
        """
        List all registered tool names.
        
        Returns:
            list: List of tool names
        """
        return list(self._tools.keys())
    
    def get_all_specs(self):
        """
        Get specifications for all tools.
        
        Returns:
            list: List of tool specifications
        """
        return [tool.get_spec() for tool in self._tools.values()]
    
    def execute(self, name, **kwargs):
        """
        Execute a tool by name.
        
        Args:
            name: Tool name
            **kwargs: Tool parameters
            
        Returns:
            dict: Execution result
        """
        tool = self.get(name)
        if tool is None:
            return {
                "success": False,
                "error": f"Tool '{name}' not found"
            }
        
        # Validate parameters
        is_valid, error = tool.validate(kwargs)
        if not is_valid:
            return {
                "success": False,
                "error": error
            }
        
        # Execute
        try:
            result = tool.execute(**kwargs)
            return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def clear(self):
        """Clear all registered tools."""
        self._tools.clear()
        self._initialized = False
    
    @property
    def tool_count(self):
        """Get number of registered tools."""
        return len(self._tools)


# Global registry instance
_registry = None

def get_registry():
    """Get the global tool registry instance."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry