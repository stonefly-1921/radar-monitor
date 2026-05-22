#!/usr/bin/env python3
"""
Excel 创建工具 - 使用 MyAgent xlsx_create 工具
零外部依赖，基于 Windows COM / PowerShell
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools import get_initialized_registry


def create_workbook(title, headers, rows, output_path, charts=None):
    """
    使用 MyAgent xlsx_create 工具创建 Excel 工作簿

    Args:
        title: 工作表名称（第一个工作表）
        headers: 表头列表
        rows: 数据行列表，每行是一个列表
        output_path: 输出 .xlsx 路径
        charts: 图表配置（暂不支持，仅记录）
    """
    r = get_initialized_registry()
    sheet = {
        'name': title,
        'headers': headers,
        'rows': rows
    }

    result = r.execute('xlsx_create', output_path=output_path, sheets=[sheet])

    if result.get('success'):
        print(f"[OK] Excel 已保存: {output_path}")
        return True
    else:
        print(f"[ERROR] 创建 Excel 失败: {result.get('error', '未知错误')}")
        return False


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='创建 Excel 工作簿（MyAgent COM 工具版）')
    parser.add_argument('--title', '-t', default='工作表1', help='工作表标题')
    parser.add_argument('--headers', default='[]', help='表头 JSON')
    parser.add_argument('--rows', default='[]', help='数据行 JSON')
    parser.add_argument('--output', '-o', default='output.xlsx', help='输出路径')
    args = parser.parse_args()
    create_workbook(args.title, json.loads(args.headers), json.loads(args.rows), args.output)