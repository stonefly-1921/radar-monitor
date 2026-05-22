"""
Document and Knowledge Base tools.
"""
import os
import json
from datetime import datetime
from .base import Tool


class DocReadTool(Tool):
    """Read a document file."""
    
    name = "doc_read"
    description = "读取文档内容"
    parameters = [
        {"name": "path", "type": "string", "required": True, "description": "文档路径"}
    ]
    
    def execute(self, **kwargs):
        path = kwargs.get("path")
        if not path:
            return {"success": False, "error": "缺少文档路径参数"}
        
        if not os.path.exists(path):
            return {"success": False, "error": f"文档不存在: {path}"}
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "success": True,
                "result": content,
                "path": path,
                "lines": len(content.splitlines())
            }
        except Exception as e:
            return {"success": False, "error": f"读取文档失败: {str(e)}"}
    
    def validate(self, params):
        if "path" not in params:
            return False, "缺少必需参数: path"
        return True, None


class DocWriteTool(Tool):
    """Write content to a document."""
    
    name = "doc_write"
    description = "写入文档内容"
    parameters = [
        {"name": "path", "type": "string", "required": True, "description": "文档路径"},
        {"name": "content", "type": "string", "required": True, "description": "文档内容"},
        {"name": "append", "type": "bool", "required": False, "description": "是否追加模式"}
    ]
    
    def execute(self, **kwargs):
        path = kwargs.get("path")
        content = kwargs.get("content", "")
        append = kwargs.get("append", False)
        
        if not path:
            return {"success": False, "error": "缺少文档路径参数"}
        
        try:
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            mode = 'a' if append else 'w'
            with open(path, mode, encoding='utf-8') as f:
                f.write(content)
            
            return {
                "success": True,
                "result": f"成功{'追加' if append else '写入'} {len(content)} 个字符到 {path}",
                "path": path
            }
        except Exception as e:
            return {"success": False, "error": f"写入文档失败: {str(e)}"}
    
    def validate(self, params):
        if "path" not in params:
            return False, "缺少必需参数: path"
        return True, None


class WikiSearchTool(Tool):
    """Search the knowledge base."""
    
    name = "wiki_search"
    description = "搜索知识库"
    parameters = [
        {"name": "query", "type": "string", "required": True, "description": "搜索关键词"},
        {"name": "limit", "type": "int", "required": False, "description": "返回结果数量"}
    ]
    
    def __init__(self, wiki_dir=None):
        self.wiki_dir = wiki_dir or os.path.join(
            os.path.dirname(__file__), "..", "wiki"
        )
    
    def execute(self, **kwargs):
        query = kwargs.get("query", "")
        limit = kwargs.get("limit", 10)
        
        if not query:
            return {"success": False, "error": "缺少搜索关键词"}
        
        if not os.path.exists(self.wiki_dir):
            return {"success": False, "error": f"知识库目录不存在: {self.wiki_dir}"}
        
        results = []
        query_lower = query.lower()
        
        try:
            for filename in os.listdir(self.wiki_dir):
                if filename.endswith('.md') or filename.endswith('.txt'):
                    filepath = os.path.join(self.wiki_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        if query_lower in content.lower():
                            # Extract matching context
                            lines = content.split('\n')
                            matching_lines = [
                                line for line in lines 
                                if query_lower in line.lower()
                            ]
                            
                            results.append({
                                "file": filename,
                                "path": filepath,
                                "match_count": content.lower().count(query_lower),
                                "preview": matching_lines[:3] if matching_lines else []
                            })
                    except Exception:
                        pass
                
                if len(results) >= limit:
                    break
            
            return {
                "success": True,
                "result": results,
                "query": query,
                "count": len(results)
            }
        except Exception as e:
            return {"success": False, "error": f"搜索知识库失败: {str(e)}"}
    
    def validate(self, params):
        if "query" not in params:
            return False, "缺少必需参数: query"
        return True, None


class WikiUpdateTool(Tool):
    """Update or create a wiki entry."""
    
    name = "wiki_update"
    description = "更新或创建知识库条目"
    parameters = [
        {"name": "title", "type": "string", "required": True, "description": "条目标题"},
        {"name": "content", "type": "string", "required": True, "description": "条目内容"},
        {"name": "tags", "type": "list", "required": False, "description": "标签列表"}
    ]
    
    def __init__(self, wiki_dir=None):
        self.wiki_dir = wiki_dir or os.path.join(
            os.path.dirname(__file__), "..", "wiki"
        )
    
    def execute(self, **kwargs):
        title = kwargs.get("title", "")
        content = kwargs.get("content", "")
        tags = kwargs.get("tags", [])
        
        if not title:
            return {"success": False, "error": "缺少条目标题"}
        
        if not os.path.exists(self.wiki_dir):
            os.makedirs(self.wiki_dir, exist_ok=True)
        
        # Create filename from title
        safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title)
        safe_title = safe_title[:100]  # Limit length
        filename = f"{safe_title}.md"
        filepath = os.path.join(self.wiki_dir, filename)
        
        # Add frontmatter
        frontmatter = f"""---
title: {title}
tags: {', '.join(tags) if tags else 'none'}
created: {datetime.now().isoformat()}
---

"""
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(frontmatter + content)
            
            return {
                "success": True,
                "result": f"成功更新知识库条目: {title}",
                "path": filepath
            }
        except Exception as e:
            return {"success": False, "error": f"更新知识库失败: {str(e)}"}
    
    def validate(self, params):
        if "title" not in params:
            return False, "缺少必需参数: title"
        if "content" not in params:
            return False, "缺少必需参数: content"
        return True, None


def register_tools(registry):
    """Register doc/wiki tools."""
    registry.register(DocReadTool())
    registry.register(DocWriteTool())
    registry.register(WikiSearchTool())
    registry.register(WikiUpdateTool())
