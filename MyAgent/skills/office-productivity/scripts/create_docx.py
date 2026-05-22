#!/usr/bin/env python3
"""
Word 文档创建工具 - 使用 MyAgent docx_create 工具
零外部依赖，基于 Windows COM / PowerShell
"""
import sys
import os
import json
import tempfile
import shutil

# 导入 MyAgent 工具注册表
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools import get_initialized_registry


def create_document(title, paragraphs, output_path):
    """
    使用 MyAgent docx_create 工具创建 Word 文档

    Args:
        title: 文档标题
        paragraphs: 内容段落列表，支持类型：
            - 字符串: 普通文本段落
            - dict with 'type': 'heading', level: 标题（level=1~5）
            - dict with 'type': 'table', headers: [], rows: [[]]: 表格
            - dict with 'type': 'image', path: str: 图片（暂不支持）
        output_path: 输出 .docx 路径
    """
    # 构建段落数据
    para_list = []
    for item in paragraphs:
        if isinstance(item, str):
            para_list.append(item)
        elif isinstance(item, dict):
            t = item.get('type', 'text')
            if t == 'heading':
                para_list.append({'type': 'heading', 'text': item.get('text', ''), 'level': item.get('level', 1)})
            elif t == 'table':
                para_list.append({'type': 'table', 'headers': item.get('headers', []), 'rows': item.get('rows', []) })
            elif t == 'image':
                # 图片暂不支持，记录为普通段落
                para_list.append(f"[图片: {item.get('path', '')}]")
            else:
                para_list.append(item.get('text', ''))
        else:
            para_list.append(str(item))

    # 调用 docx_create 工具
    r = get_initialized_registry()
    result = r.execute('docx_create', output_path=output_path, title=title, paragraphs=para_list)

    if result.get('success'):
        print(f"[OK] 文档已保存: {output_path}")
        return True
    else:
        print(f"[ERROR] 创建文档失败: {result.get('error', '未知错误')}")
        return False


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='创建 Word 文档（MyAgent COM 工具版）')
    parser.add_argument('--title', '-t', default='未命名文档', help='文档标题')
    parser.add_argument('--output', '-o', default='output.docx', help='输出路径')
    parser.add_argument('--content', '-c', default='[]', help='内容 JSON')
    args = parser.parse_args()
    content = json.loads(args.content)
    create_document(args.title, content, args.output)