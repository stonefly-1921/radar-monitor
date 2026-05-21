"""
Tools module - Tool implementations and registry.
"""
from .base import Tool
from .registry import ToolRegistry, get_registry

# Import all tools to register them
from . import file_ops
from . import shell
from . import python_exec
from . import doc_wiki

# Register tools on import
from .file_ops import register_tools as register_file_ops
from .shell import ShellRunTool
from .python_exec import register_tools as register_python_tools
from .doc_wiki import register_tools as register_doc_wiki

# Initialize registry with all tools
_registry = None

def get_initialized_registry():
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        register_file_ops(_registry)
        _registry.register(ShellRunTool())
        register_python_tools(_registry)
        register_doc_wiki(_registry)
    return _registry

__all__ = ['Tool', 'ToolRegistry', 'get_registry', 'get_initialized_registry']
