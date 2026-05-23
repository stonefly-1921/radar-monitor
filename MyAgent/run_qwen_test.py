"""
MyAgent 千问集成测试脚本 v2
基于 io/input.txt -> io/prompt.txt -> io/response.txt 流程

使用方法:
1. 双击 run.bat
2. 在 io/input.txt 写入任务
3. 程序生成 io/prompt.txt
4. 人工复制 prompt 到千问网页
5. 人工把千问回复粘贴到 io/response.txt
6. 程序自动解析并执行工具
7. 多轮循环直到 final answer
8. 统计模型调用次数
"""

import os
import sys
import time
import json
import warnings
warnings.filterwarnings('ignore')

# Suppress numpy warnings to stderr
import contextlib

# Add project root to path
sys.path.insert(0, 'C:/Users/15041/.openclaw/workspace/MyAgent')

BASE_DIR = 'C:/Users/15041/.openclaw/workspace/MyAgent'
INPUT_FILE = os.path.join(BASE_DIR, 'io', 'input.txt')
PROMPT_FILE = os.path.join(BASE_DIR, 'io', 'prompt.txt')
RESPONSE_FILE = os.path.join(BASE_DIR, 'io', 'response.txt')
TOOL_RESULT_FILE = os.path.join(BASE_DIR, 'io', 'tool_result.json')
SESSION_FILE = os.path.join(BASE_DIR, 'io', 'session.json')

# Global call counters
model_call_count = 0
tool_call_count = 0


def write_file(path, content):
    """Write content to file"""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def read_file(path):
    """Read file content"""
    if not os.path.exists(path):
        return ""
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def clear_io_files():
    """Clear IO files for fresh start"""
    for f in [INPUT_FILE, PROMPT_FILE, RESPONSE_FILE, TOOL_RESULT_FILE]:
        write_file(f, "")


def load_loop():
    """Load MyAgent loop"""
    from agent.loop_v2 import AgentLoopV2
    loop = AgentLoopV2()
    loop.initialize()
    return loop


def run_task_loop(task_text, max_turns=15):
    """Run task through MyAgent REPL loop"""
    global model_call_count, tool_call_count
    
    print(f"\n{'='*60}")
    print(f"任务开始: {task_text[:50]}...")
    print(f"{'='*60}")
    
    loop = load_loop()
    
    turn_details = []
    
    for turn in range(1, max_turns + 1):
        print(f"\n--- Turn {turn} ---")
        
        # Build prompt
        conversation = []
        if loop.session:
            try:
                conversation = loop.session.get_conversation_history()
            except:
                conversation = []
        
        prompt = loop.build_prompt_text(task_text, turn=turn, tool_results=None, conversation=conversation)
        write_file(PROMPT_FILE, prompt)
        model_call_count += 1
        
        print(f"[Turn {turn}] Prompt 已生成 ({len(prompt)} chars)")
        print(f"[Turn {turn}] 等待人工操作...")
        print(f"  1. 复制 io/prompt.txt 内容到千问")
        print(f"  2. 把千问回复粘贴到 io/response.txt")
        print(f"  3. 按回车继续...")
        
        # Wait for response.txt to have content
        input("按回车继续...")
        
        response = read_file(RESPONSE_FILE).strip()
        if not response or len(response) < 20:
            print("[错误] response.txt 为空或内容太少")
            return False, turn, tool_call_count
        
        print(f"[Turn {turn}] 收到回复 ({len(response)} chars)")
        
        # Parse response
        parsed = loop.parse_response(response)
        content = parsed.get('content', '')
        tool_calls = parsed.get('tool_calls', [])
        action = parsed.get('action', 'final')
        
        if action == 'final':
            print(f"\n✅ 完成！(Turn {turn})")
            print(f"最终回复: {content[:300]}...")
            turn_details.append({"turn": turn, "action": "final"})
            return True, turn, tool_call_count
        
        if action == 'tool_call':
            tool_results = []
            for tc in tool_calls:
                tool_name = tc.get('tool') or tc.get('name', 'unknown')
                params = tc.get('params') or tc.get('arguments', {})
                
                print(f"[Turn {turn}] 工具调用: {tool_name}")
                res = loop.registry.execute(tool_name, **params)
                tool_call_count += 1
                
                if res.get('success'):
                    print(f"  ✓ 成功")
                    tool_results.append({"tool": tool_name, "success": True, "result": res.get('result', '')})
                else:
                    print(f"  ✗ 失败: {res.get('error', 'unknown')}")
                    tool_results.append({"tool": tool_name, "success": False, "error": res.get('error', '')})
            
            turn_details.append({
                "turn": turn, 
                "action": "tool_call", 
                "tools": [t['tool'] for t in tool_results]
            })
            
            # Save tool results
            write_file(TOOL_RESULT_FILE, json.dumps(tool_results, ensure_ascii=False, indent=2))
            
            # Clear response for next turn
            write_file(RESPONSE_FILE, "")
            continue
    
    print(f"[超时] 达到最大 Turn 数 {max_turns}")
    return False, max_turns, tool_call_count


def main():
    global model_call_count, tool_call_count
    
    print(f"{'='*60}")
    print("  MyAgent 千问集成测试")
    print("  Win7 隔离网环境 | 不改变依赖")
    print(f"{'='*60}")
    
    tasks = [
        {
            "id": 1,
            "name": "文件查找与理解",
            "task": "请在 C:\\Users\\15041\\.openclaw\\workspace\\MyAgent 目录下找一个 Python 文件，读取它的内容，理解并总结其中的主要功能。"
        },
        {
            "id": 2,
            "name": "PDF分析综述",
            "task": "请读取桌面上论文文件夹中的PDF文件，分析其中内容，生成一个综述性的文献报告，保存为Word文档。"
        },
        {
            "id": 3,
            "name": "代码调试",
            "task": "请用Python写一个大于1000行的学生成绩管理系统，包含一些常见的bug，然后调试使其正常运行。"
        }
    ]
    
    results = []
    
    for td in tasks:
        clear_io_files()
        model_call_count = 0
        tool_call_count = 0
        
        # Write task
        write_file(INPUT_FILE, td['task'])
        
        success, turns, tool_calls = run_task_loop(td['task'])
        
        results.append({
            "id": td['id'],
            "name": td['name'],
            "success": success,
            "turns": turns,
            "model_calls": model_call_count,
            "tool_calls": tool_calls
        })
        
        print(f"\n任务 {td['id']} 完成: {'成功' if success else '失败'}")
        print(f"  模型调用: {model_call_count} 次")
        print(f"  工具调用: {tool_calls} 次")
    
    # Summary
    print(f"\n{'='*60}")
    print("测试汇总")
    print(f"{'='*60}")
    
    total_model = 0
    total_tool = 0
    
    for r in results:
        status = "✅" if r['success'] else "❌"
        print(f"{status} 任务{r['id']}: {r['name']}")
        print(f"   Turns: {r['turns']}, 模型调用: {r['model_calls']}, 工具调用: {r['tool_calls']}")
        total_model += r['model_calls']
        total_tool += r['tool_calls']
    
    print(f"\n总计:")
    print(f"  模型调用: {total_model} 次")
    print(f"  工具调用: {total_tool} 次")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()