"""
Wiki Operations - karpathy-llm-wiki business layer
Zero external dependencies - Python built-ins only
"""
import os
import re
from datetime import datetime
from .base import Tool


WIKI_ROOT_DEFAULT = "wiki"
SOURCES_ROOT = "sources"


class WikiIndexTool(Tool):
    name = "wiki_index"
    description = "Read or rebuild wiki index.md"
    parameters = [
        {"name": "wiki_root", "type": "string", "required": False, "description": "wiki root directory"},
        {"name": "rebuild", "type": "bool", "required": False, "description": "force rebuild index"}
    ]
    
    def execute(self, **kwargs):
        wiki_root = kwargs.get("wiki_root", WIKI_ROOT_DEFAULT)
        rebuild = kwargs.get("rebuild", False)
        
        index_path = os.path.join(wiki_root, "index.md")
        wiki_dir = os.path.join(wiki_root, "wiki")
        
        if not os.path.exists(wiki_dir):
            os.makedirs(wiki_dir, exist_ok=True)
        
        if rebuild or not os.path.exists(index_path):
            pages = self._scan_pages(wiki_dir)
            index_content = self._build_index(pages, wiki_dir)
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(index_content)
            return {
                "success": True,
                "result": "Rebuilt index with " + str(len(pages)) + " pages",
                "pages": pages,
                "index_path": index_path
            }
        else:
            with open(index_path, 'r', encoding='utf-8') as f:
                index_content = f.read()
            pages = self._scan_pages(wiki_dir)
            return {
                "success": True,
                "result": "Index contains " + str(len(pages)) + " pages",
                "pages": pages,
                "index_content": index_content,
                "index_path": index_path
            }
    
    def _scan_pages(self, wiki_dir):
        pages = []
        if not os.path.exists(wiki_dir):
            return pages
        for filename in os.listdir(wiki_dir):
            if filename.endswith('.md') and filename != 'index.md':
                slug = filename[:-3]
                filepath = os.path.join(wiki_dir, filename)
                stat = os.stat(filepath)
                pages.append({
                    "slug": slug,
                    "filename": filename,
                    "path": filepath,
                    "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "size": stat.st_size
                })
        return pages
    
    def _build_index(self, pages, wiki_dir):
        lines = [
            "# Wiki Index\n",
            "_Last updated: " + datetime.now().strftime('%Y-%m-%d') + " - " + str(len(pages)) + " pages_\n",
            "\n## Entities",
            "| Page | Summary | Updated |",
            "|------|---------|---------|",
        ]
        for p in sorted(pages, key=lambda x: x['slug']):
            dt = datetime.fromtimestamp(os.stat(p['path']).st_mtime).strftime('%Y-%m-%d')
            lines.append("| [[" + p['slug'] + "]] | | " + dt + " |")
        
        lines.append("\n## Concepts")
        lines.append("| Page | Summary | Updated |")
        lines.append("|------|---------|---------|")
        
        lines.append("\n## Sources processed")
        lines.append("| Page | Summary | Updated |")
        lines.append("|------|---------|---------|")
        
        return '\n'.join(lines)
    
    def validate(self, params):
        return True, None


class WikiLintTool(Tool):
    name = "wiki_lint"
    description = "Wiki health check: orphans, broken links, contradictions"
    parameters = [
        {"name": "wiki_root", "type": "string", "required": False, "description": "wiki root directory"},
        {"name": "verbose", "type": "bool", "required": False, "description": "verbose output"}
    ]
    
    def execute(self, **kwargs):
        wiki_root = kwargs.get("wiki_root", WIKI_ROOT_DEFAULT)
        verbose = kwargs.get("verbose", False)
        
        wiki_dir = os.path.join(wiki_root, "wiki")
        if not os.path.exists(wiki_dir):
            return {"success": False, "error": "Wiki directory not found: " + wiki_dir}
        
        pages = {}
        link_graph = {}
        
        for filename in os.listdir(wiki_dir):
            if not filename.endswith('.md') or filename == 'index.md':
                continue
            slug = filename[:-3]
            filepath = os.path.join(wiki_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            pages[slug] = content
            
            links = re.findall(r'\[\[([^\]]+)\]\]', content)
            link_graph[slug] = set(links)
        
        issues = []
        warnings = []
        
        # 1. Orphan pages
        for slug in pages:
            inbound = [s for s, links in link_graph.items() if slug in links]
            if not inbound and len(pages) > 1:
                issues.append({
                    "type": "orphan",
                    "page": slug,
                    "detail": "No inbound links (" + str(len(pages)) + " total pages)"
                })
        
        # 2. Broken links
        for slug, links in link_graph.items():
            for link in links:
                if link not in pages and link != 'index':
                    issues.append({
                        "type": "broken_link",
                        "page": slug,
                        "target": link,
                        "detail": "Target page does not exist: " + link
                    })
        
        # 3. Empty pages
        for slug, content in pages.items():
            stripped = content.replace('#', '').replace('---', '').strip()
            if len(stripped) < 50:
                warnings.append({
                    "type": "empty_page",
                    "page": slug,
                    "detail": "Page content too short (" + str(len(stripped)) + " chars)"
                })
        
        # 4. Missing Sources section
        for slug, content in pages.items():
            if '## Sources' not in content:
                warnings.append({
                    "type": "missing_sources",
                    "page": slug,
                    "detail": "Missing ## Sources section"
                })
        
        result = {
            "success": True,
            "total_pages": len(pages),
            "issues_count": len(issues),
            "warnings_count": len(warnings),
            "issues": issues,
            "warnings": warnings
        }
        
        if verbose:
            result["link_graph"] = {k: list(v) for k, v in link_graph.items()}
        
        return result
    
    def validate(self, params):
        return True, None


class WikiLinkCheckTool(Tool):
    name = "wiki_link_check"
    description = "Check [[wiki-link]] references are valid"
    parameters = [
        {"name": "page", "type": "string", "required": True, "description": "page slug to check"},
        {"name": "wiki_root", "type": "string", "required": False, "description": "wiki root directory"}
    ]
    
    def execute(self, **kwargs):
        page = kwargs.get("page", "")
        wiki_root = kwargs.get("wiki_root", WIKI_ROOT_DEFAULT)
        
        if not page:
            return {"success": False, "error": "Missing page parameter"}
        
        wiki_dir = os.path.join(wiki_root, "wiki")
        filepath = os.path.join(wiki_dir, page + ".md")
        
        if not os.path.exists(filepath):
            return {"success": False, "error": "Page does not exist: " + page + ".md"}
        
        valid_pages = set()
        if os.path.exists(wiki_dir):
            for f in os.listdir(wiki_dir):
                if f.endswith('.md') and f != 'index.md':
                    valid_pages.add(f[:-3])
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        links = re.findall(r'\[\[([^\]]+)\]\]', content)
        
        broken = []
        valid = []
        for link in links:
            if link in valid_pages or link == 'index':
                valid.append(link)
            else:
                broken.append(link)
        
        return {
            "success": True,
            "page": page,
            "total_links": len(links),
            "valid": valid,
            "broken": broken,
            "broken_count": len(broken)
        }
    
    def validate(self, params):
        if "page" not in params:
            return False, "Missing required parameter: page"
        return True, None


class WikiReadTool(Tool):
    name = "wiki_read"
    description = "Read a specific wiki page by slug"
    parameters = [
        {"name": "page", "type": "string", "required": True, "description": "page slug"},
        {"name": "wiki_root", "type": "string", "required": False, "description": "wiki root directory"}
    ]
    
    def execute(self, **kwargs):
        page = kwargs.get("page", "")
        wiki_root = kwargs.get("wiki_root", WIKI_ROOT_DEFAULT)
        
        if not page:
            return {"success": False, "error": "Missing page parameter"}
        
        if page.endswith('.md'):
            page = page[:-3]
        
        wiki_dir = os.path.join(wiki_root, "wiki")
        filepath = os.path.join(wiki_dir, page + ".md")
        
        if not os.path.exists(filepath):
            return {"success": False, "error": "Page does not exist: " + page + ".md"}
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        frontmatter = {}
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                for line in parts[1].strip().split('\n'):
                    if ':' in line:
                        key, val = line.split(':', 1)
                        frontmatter[key.strip()] = val.strip()
                content = parts[2].strip()
        
        return {
            "success": True,
            "page": page,
            "path": filepath,
            "frontmatter": frontmatter,
            "content": content,
            "lines": len(content.splitlines())
        }
    
    def validate(self, params):
        if "page" not in params:
            return False, "Missing required parameter: page"
        return True, None


class WikiWriteTool(Tool):
    name = "wiki_write"
    description = "Create or update a wiki page with frontmatter"
    parameters = [
        {"name": "page", "type": "string", "required": True, "description": "page slug"},
        {"name": "content", "type": "string", "required": True, "description": "page content (without frontmatter)"},
        {"name": "summary", "type": "string", "required": False, "description": "one-line summary"},
        {"name": "tags", "type": "list", "required": False, "description": "list of tags"},
        {"name": "sources", "type": "list", "required": False, "description": "list of sources"},
        {"name": "wiki_root", "type": "string", "required": False, "description": "wiki root directory"}
    ]
    
    def execute(self, **kwargs):
        page = kwargs.get("page", "")
        content = kwargs.get("content", "")
        summary = kwargs.get("summary", "")
        tags = kwargs.get("tags", [])
        sources = kwargs.get("sources", [])
        wiki_root = kwargs.get("wiki_root", WIKI_ROOT_DEFAULT)
        
        if not page:
            return {"success": False, "error": "Missing page parameter"}
        
        if not content:
            return {"success": False, "error": "Missing content parameter"}
        
        if page.endswith('.md'):
            page = page[:-3]
        
        wiki_dir = os.path.join(wiki_root, "wiki")
        if not os.path.exists(wiki_dir):
            os.makedirs(wiki_dir, exist_ok=True)
        
        filepath = os.path.join(wiki_dir, page + ".md")
        
        now = datetime.now().isoformat()
        tags_str = ', '.join(tags) if tags else 'none'
        sources_str = ', '.join(sources) if sources else 'none'
        frontmatter_lines = [
            "---",
            "title: " + page,
            "summary: " + summary,
            "tags: " + tags_str,
            "sources: " + sources_str,
            "created: " + now,
            "updated: " + now,
            "---",
            ""
        ]
        
        full_content = '\n'.join(frontmatter_lines) + content
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        return {
            "success": True,
            "result": "Wrote page: " + page,
            "path": filepath,
            "bytes": len(full_content.encode('utf-8'))
        }
    
    def validate(self, params):
        if "page" not in params:
            return False, "Missing required parameter: page"
        if "content" not in params:
            return False, "Missing required parameter: content"
        return True, None


class WikiDeleteTool(Tool):
    name = "wiki_delete"
    description = "Delete a wiki page"
    parameters = [
        {"name": "page", "type": "string", "required": True, "description": "page slug"},
        {"name": "wiki_root", "type": "string", "required": False, "description": "wiki root directory"}
    ]
    
    def execute(self, **kwargs):
        page = kwargs.get("page", "")
        wiki_root = kwargs.get("wiki_root", WIKI_ROOT_DEFAULT)
        
        if not page:
            return {"success": False, "error": "Missing page parameter"}
        
        if page.endswith('.md'):
            page = page[:-3]
        
        wiki_dir = os.path.join(wiki_root, "wiki")
        filepath = os.path.join(wiki_dir, page + ".md")
        
        if not os.path.exists(filepath):
            return {"success": False, "error": "Page does not exist: " + page + ".md"}
        
        try:
            os.remove(filepath)
            return {
                "success": True,
                "result": "Deleted page: " + page,
                "path": filepath
            }
        except Exception as e:
            return {"success": False, "error": "Delete failed: " + str(e)}
    
    def validate(self, params):
        if "page" not in params:
            return False, "Missing required parameter: page"
        return True, None


def register_tools(registry):
    registry.register(WikiIndexTool())
    registry.register(WikiLintTool())
    registry.register(WikiLinkCheckTool())
    registry.register(WikiReadTool())
    registry.register(WikiWriteTool())
    registry.register(WikiDeleteTool())
