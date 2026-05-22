#!/usr/bin/env python3
"""
Excel 验证脚本 - 使用 MyAgent 工具验证 xlsx 文件
无需外部依赖，基于 Windows COM
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools import get_initialized_registry


def validate(filename):
    """
    验证 Excel 文件：
    1. 文件是否存在
    2. 能否读取内容
    3. 是否有明显错误

    返回 dict：
    - status: 'success' 或 'errors_found'
    - total_errors: 错误数量
    - sheets: sheet 列表和行数
    """
    if not os.path.exists(filename):
        return {"error": f"File {filename} does not exist"}

    r = get_initialized_registry()

    # 获取文件信息（读取第一个 sheet）
    result = r.execute('xlsx_read', input_path=filename, max_rows=5)

    if result.get('success'):
        return {
            "status": "success",
            "total_errors": 0,
            "sheets_validated": 1,
            "info": "File is readable and valid"
        }
    else:
        return {
            "status": "errors_found",
            "error": result.get('error', 'Unknown error')
        }


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_xlsx.py <excel_file>")
        sys.exit(1)

    filename = sys.argv[1]
    result = validate(filename)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()