"""
Demonstration: Run a real task with Hermes Agent and count file operations.
This simulates how the agent loop works with file-based I/O.
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent.persona import Persona
from agent.config import AgentConfig
from memory.core import Memory
from tools import get_initialized_registry
from session import Session
from agent.loop import AgentLoop

# Track file operations for counting
file_operation_log = []

def log_operation(op_type, path, data_len=None):
    file_operation_log.append({
        "op": op_type,
        "path": path,
        "data_len": data_len,
        "timestamp": len(file_operation_log) + 1
    })
    print(f"  [{len(file_operation_log)}] {op_type}: {path}" + (f" ({data_len} bytes)" if data_len else ""))

# Demo task: Create a simple task and execute it
def run_task(task_description):
    print(f"\n{'='*60}")
    print(f"  Running Task: {task_description}")
    print(f"{'='*60}")
    
    base_dir = os.path.dirname(os.path.dirname(__file__))
    io_dir = os.path.join(base_dir, "io")
    
    # Ensure io directory exists
    os.makedirs(io_dir, exist_ok=True)
    
    # 1. Create session (writes to session file)
    session_file = os.path.join(io_dir, "session.json")
    session = Session.load_or_create(session_file)
    log_operation("WRITE", session_file)
    
    # 2. Create memory
    memory = Memory()
    log_operation("READ", "memory/core.py (in-memory, no file)")
    
    # 3. Get tools registry (singleton init)
    registry = get_initialized_registry()
    tools = registry.list_tools()
    log_operation("READ", "tools/registry.py (in-memory init)")
    
    # 4. Build prompt (writes to prompt.json)
    persona = Persona()
    prompt_file = os.path.join(io_dir, "prompt.json")
    
    # Simulate building a prompt
    prompt_data = {
        "type": "prompt",
        "system": persona.get_system_prompt(),
        "user_input": task_description,
        "turn": session.turn_count + 1
    }
    
    with open(prompt_file, 'w', encoding='utf-8') as f:
        json.dump(prompt_data, f, ensure_ascii=False, indent=2)
    log_operation("WRITE", prompt_file, len(json.dumps(prompt_data, ensure_ascii=False)))
    
    # 5. Read prompt back (simulating LLM reading)
    with open(prompt_file, 'r', encoding='utf-8') as f:
        read_prompt = json.load(f)
    log_operation("READ", prompt_file, len(json.dumps(read_prompt, ensure_ascii=False)))
    
    # 6. Simulate tool execution: file_read
    input_file = os.path.join(io_dir, "input.json")
    test_content = f"Task: {task_description}\n"
    with open(input_file, 'w', encoding='utf-8') as f:
        json.dump({"task": task_description, "content": test_content}, f)
    log_operation("WRITE", input_file, len(test_content))
    
    # 7. Execute tool
    with open(input_file, 'r', encoding='utf-8') as f:
        input_data = json.load(f)
    log_operation("READ", input_file, len(json.dumps(input_data, ensure_ascii=False)))
    
    # 8. Execute shell tool
    result = registry.execute("shell_run", command="echo hello", cwd=base_dir)
    log_operation("EXEC", "shell_run: echo hello", len(str(result)))
    
    # 9. Write response
    response_file = os.path.join(io_dir, "response.json")
    response_data = {
        "success": True,
        "result": f"Completed task: {task_description}",
        "tool_results": file_operation_log[-5:]  # Last 5 ops
    }
    with open(response_file, 'w', encoding='utf-8') as f:
        json.dump(response_data, f, ensure_ascii=False, indent=2)
    log_operation("WRITE", response_file, len(json.dumps(response_data, ensure_ascii=False)))
    
    # 10. Read response
    with open(response_file, 'r', encoding='utf-8') as f:
        final_response = json.load(f)
    log_operation("READ", response_file, len(json.dumps(final_response, ensure_ascii=False)))
    
    return final_response

def main():
    print("="*60)
    print("  Hermes Agent - Practical Task Demo + Copy Counting")
    print("="*60)
    
    # Run a practical task
    result = run_task("List all Python files in the tests directory")
    
    # Summary
    print(f"\n{'='*60}")
    print("  File Operation Summary")
    print(f"{'='*60}")
    
    op_counts = {}
    for op in file_operation_log:
        op_type = op["op"]
        op_counts[op_type] = op_counts.get(op_type, 0) + 1
    
    print(f"\n  Total file operations: {len(file_operation_log)}")
    print(f"\n  Breakdown:")
    for op_type, count in sorted(op_counts.items()):
        print(f"    {op_type}: {count}")
    
    print(f"\n  Total JSON file read/write cycles: {op_counts.get('READ', 0) + op_counts.get('WRITE', 0)}")
    
    print(f"\n  For a single task, we did {len(file_operation_log)} file operations.")
    print(f"  In the full test suite (66 tests), that's ~{len(file_operation_log) * 66} operations!")
    
    print(f"\n  Note: This is the 'manual copy via files' pattern.")
    print(f"  A direct function call would be 1 operation, not {len(file_operation_log)}.")
    
    print(f"\n  Result: {result['result']}")
    print("="*60)

if __name__ == "__main__":
    main()