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
from . import wiki_ops
from . import pdf_ops

# Register tools on import
from .file_ops import register_tools as register_file_ops
from .shell import ShellRunTool
from .python_exec import register_tools as register_python_tools
from .doc_wiki import register_tools as register_doc_wiki
from .wiki_ops import register_tools as register_wiki_ops
from .office_ops import register_tools as register_office_ops
from .docx_ops import register_tools as register_docx_ops
from .pdf_ops import register_tools as register_pdf_ops

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
        register_wiki_ops(_registry)
        register_office_ops(_registry)
        register_docx_ops(_registry)
        register_pdf_ops(_registry)
    return _registry

__all__ = ['Tool', 'ToolRegistry', 'get_registry', 'get_initialized_registry']
