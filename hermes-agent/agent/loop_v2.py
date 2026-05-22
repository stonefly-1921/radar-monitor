"""
Agent Loop v2 - Optimized for minimal manual intervention.

Key optimizations:
1. Batch tool calls: One LLM call can return multiple tools
2. Parallel execution: Execute all tools in a batch simultaneously  
3. Auto-loop: Continue until final answer or max iterations
4. Direct API mode: No manual file copy between prompt/response

Expected manual operations per task: 2-3 (input + final answer review)
"""

import os
import sys
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent.persona import Persona
from agent.config import AgentConfig
from memory.core import Memory
from session import Session
from tools import get_initialized_registry


class AgentLoopV2:
    """
    Optimized Agent Loop that minimizes manual intervention.
    
    Flow:
    1. User provides input ONCE
    2. Build full prompt (persona + memory + history + tools)
    3. LLM processes and returns:
       - Final answer (done, 1 manual operation total)
       - Tool calls (batch execute, auto-continue, ~3-5 manual operations max)
    4. If tools: execute all in parallel, feed results back
    5. LLM continues until final answer or max iterations
    """
    
    def __init__(self, config=None, llm_client=None):
        """
        Args:
            config: AgentConfig instance
            llm_client: Optional LLM API client for direct calls.
                       If None, uses file-based mode (requires manual copying).
        """
        self.config = config or AgentConfig()
        self.persona = Persona()
        self.registry = get_initialized_registry()
        self.llm_client = llm_client  # Direct API client for auto mode
        
        self.session = None
        self.memory = None
        
        # I/O paths (for file-based fallback mode)
        self.io_config = {
            "input_file": "io/input.json",
            "prompt_file": "io/prompt.json", 
            "response_file": "io/response.json",
            "session_file": "io/session.json",
            "tool_result_file": "io/tool_result.json"
        }
        
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        
        # Stats
        self.stats = {
            "llm_calls": 0,
            "tools_called": 0,
            "tools_succeeded": 0,
            "tools_failed": 0,
            "iterations": 0
        }
        
        # Limits
        self.max_iterations = 20  # Prevent infinite loops
        self.max_tools_per_call = 10  # Batch size limit
    
    def _resolve_path(self, filename):
        return os.path.join(self.base_dir, filename)
    
    def initialize(self):
        """Initialize session and memory."""
        print("\n" + "=" * 60)
        print("  Hermes Agent Loop v2 - Optimized")
        print("=" * 60)
        
        # Session
        session_file = self._resolve_path(self.io_config["session_file"])
        self.session = Session.load_or_create(session_file)
        print(f"\n[会话] ID={self.session.session_id}, 轮次={self.session.turn_count}")
        
        # Memory
        self.memory = Memory()
        if self.session.memory and any(self.session.memory.values()):
            self.memory.load_from_session(self.session.to_dict())
        
        # Tools
        tools = self.registry.list_tools()
        print(f"[工具] {len(tools)} 个可用: {', '.join(sorted(tools))}")
        
        # Reset stats
        self.stats = {"llm_calls": 0, "tools_called": 0, "tools_succeeded": 0, "tools_failed": 0, "iterations": 0}
        
        print()
    
    def build_prompt(self, user_input: str, tool_results: List[Dict] = None) -> Dict:
        """
        Build complete prompt for LLM.
        
        Args:
            user_input: Current user input
            tool_results: Optional list of previous tool results to include
        """
        conversation = self.session.get_conversation_history()
        
        # Add current input
        conversation.append({"role": "user", "content": user_input})
        
        # Build prompt
        prompt = {
            "type": "prompt",
            "system": self.persona.get_system_prompt(),
            "context": {
                "session_id": self.session.session_id,
                "turn": self.session.turn_count + 1,
                "iteration": self.stats["iterations"],
                "memory": self.memory.get_context_for_llm()
            },
            "conversation": conversation,
            "tools_available": self.registry.get_all_specs(),
            "instructions": {
                "max_tools_per_response": self.max_tools_per_call,
                "batch_execute_encouraged": True,
                "auto_continue_until_done": True
            }
        }
        
        # Include previous tool results if any
        if tool_results:
            prompt["tool_results"] = tool_results
            prompt["context"]["last_tool_results"] = tool_results
        
        return prompt
    
    def call_llm(self, prompt: Dict) -> Dict:
        """
        Call LLM API (direct mode) or load from file (file mode).
        """
        self.stats["llm_calls"] += 1
        
        if self.llm_client:
            # Direct API mode - fully automated
            return self._call_llm_direct(prompt)
        else:
            # File-based mode - requires manual copying
            return self._call_llm_file_based(prompt)
    
    def _call_llm_direct(self, prompt: Dict) -> Dict:
        """Direct API call - fully automated."""
        print(f"\n[LLM 调用 #{self.stats['llm_calls']}] 直接 API 模式")
        
        messages = [{"role": "system", "content": prompt["system"]}]
        
        # Add conversation
        for msg in prompt["conversation"]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            messages.append({"role": role, "content": content})
        
        # Add tool results context
        if prompt.get("tool_results"):
            tool_context = "\n\n[工具执行结果]\n"
            for tr in prompt["tool_results"]:
                tool_context += f"- {tr['tool']}: {tr.get('result', {}).get('result', tr.get('error', 'unknown'))}\n"
            messages.append({"role": "system", "content": tool_context})
        
        # Call LLM with tools
        response = self.llm_client.chat(
            messages=messages,
            tools=prompt["tools_available"]
        )
        
        return response
    
    def _call_llm_file_based(self, prompt: Dict) -> Dict:
        """File-based mode - requires manual intervention."""
        print(f"\n[LLM 调用 #{self.stats['llm_calls']}] 文件模式 (需要手动复制)")
        
        # Save prompt
        prompt_file = self._resolve_path(self.io_config["prompt_file"])
        os.makedirs(os.path.dirname(prompt_file), exist_ok=True)
        with open(prompt_file, 'w', encoding='utf-8') as f:
            json.dump(prompt, f, ensure_ascii=False, indent=2)
        
        print(f"  → 提示词已写入: {prompt_file}")
        print(f"  → 请复制到 LLM 接口，将响应粘贴到: {self.io_config['response_file']}")
        
        # Wait for response
        input("  按 Enter 继续...")
        
        # Load response
        response_file = self._resolve_path(self.io_config["response_file"])
        if not os.path.exists(response_file):
            return {"error": "response.json not found"}
        
        with open(response_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def execute_tools_parallel(self, tool_calls: List[Dict]) -> List[Dict]:
        """
        Execute multiple tools in parallel.
        
        Args:
            tool_calls: List of {"tool": "name", "params": {...}}
            
        Returns:
            List of {"tool": "name", "params": {...}, "result": {...}}
        """
        print(f"\n[批量工具执行] {len(tool_calls)} 个工具")
        
        results = []
        
        # Execute all tools in parallel using ThreadPoolExecutor
        def execute_single(tool_call):
            tool_name = tool_call.get("tool")
            params = tool_call.get("params", {})
            self.stats["tools_called"] += 1
            
            print(f"  执行: {tool_name}...", end=" ")
            result = self.registry.execute(tool_name, **params)
            
            if result.get("success"):
                self.stats["tools_succeeded"] += 1
                print("OK")
            else:
                self.stats["tools_failed"] += 1
                print("FAIL")
            
            return {
                "tool": tool_name,
                "params": params,
                "result": result
            }
        
        # Parallel execution
        with ThreadPoolExecutor(max_workers=min(len(tool_calls), 5)) as executor:
            futures = [executor.submit(execute_single, tc) for tc in tool_calls]
            for future in as_completed(futures):
                results.append(future.result())
        
        # Sort results to match original tool order
        tool_order = {tc["tool"]: i for i, tc in enumerate(tool_calls)}
        results.sort(key=lambda r: tool_order.get(r["tool"], 999))
        
        return results
    
    def parse_response(self, response: Dict) -> Dict:
        """
        Parse LLM response to extract final answer or tool calls.
        
        Returns:
            {"type": "final_answer" | "tool_call", ...}
        """
        if not response:
            return {"type": "error", "content": "Empty response"}
        
        # Handle different response formats
        content = response.get("content", "")
        tool_calls = response.get("tool_calls", [])
        
        if tool_calls:
            # Batch tool calls detected
            return {
                "type": "tool_call",
                "content": content,
                "tool_calls": tool_calls
            }
        else:
            return {
                "type": "final_answer",
                "content": content
            }
    
    def run_single_turn(self, user_input: str) -> Dict:
        """
        Execute a single turn with auto-loop capability.
        
        This method handles:
        1. Prompt building
        2. LLM call
        3. Tool execution (parallel)
        4. Auto-continuation until final answer
        
        Args:
            user_input: User's input
            
        Returns:
            {"success": bool, "type": "final_answer"|"max_iterations", "content": str}
        """
        print(f"\n{'='*60}")
        print(f"  Turn 开始 (输入: {user_input[:50]}...)")
        print(f"{'='*60}")
        
        self.stats["iterations"] = 0
        tool_results = None
        all_tool_results = []
        
        while self.stats["iterations"] < self.max_iterations:
            self.stats["iterations"] += 1
            iteration = self.stats["iterations"]
            
            print(f"\n--- 迭代 #{iteration} ---")
            
            # Build prompt
            prompt = self.build_prompt(user_input, tool_results)
            
            # Call LLM
            response = self.call_llm(prompt)
            
            # Parse response
            parsed = self.parse_response(response)
            
            if parsed["type"] == "final_answer":
                # Done! Final answer received
                print(f"\n[AUTO] 最终回答 (迭代 #{iteration}):")
                print(f"  {parsed['content'][:200]}{'...' if len(parsed['content']) > 200 else ''}")
                
                # Save to session
                self.session.add_turn({
                    "input": user_input,
                    "llm_calls": self.stats["llm_calls"],
                    "tool_calls": len(all_tool_results),
                    "final_answer": parsed["content"]
                })
                self.session.mark_completed()
                
                return {
                    "success": True,
                    "type": "final_answer",
                    "content": parsed["content"],
                    "iterations": iteration,
                    "llm_calls": self.stats["llm_calls"],
                    "tools_called": self.stats["tools_called"]
                }
            
            elif parsed["type"] == "tool_call":
                # Execute tools and continue
                tool_calls = parsed["tool_calls"]
                print(f"\n检测到 {len(tool_calls)} 个工具调用:")
                for tc in tool_calls:
                    print(f"  - {tc['tool']}: {str(tc.get('params', {}))[:60]}")
                
                # Batch execute tools in parallel
                results = self.execute_tools_parallel(tool_calls)
                all_tool_results.extend(results)
                
                # Prepare for next iteration with tool results
                tool_results = results
                
                print(f"\n  统计: LLM调用={self.stats['llm_calls']}, 工具={self.stats['tools_called']}")
                print(f"  继续循环...")
                
                # Auto-continue to next iteration
                continue
            
                print(f"\n[ERROR] {parsed.get('content', 'Unknown')}")
                return {
                    "success": False,
                    "type": "error",
                    "content": parsed.get("content", "Unknown error")
                }
        
        print(f"\n[WARN] 达到最大迭代次数 ({self.max_iterations})")
        return {
            "success": False,
            "type": "max_iterations",
            "content": f"Reached max iterations ({self.max_iterations})",
            "iterations": self.stats["iterations"],
            "tool_results": all_tool_results
        }
    
    def run(self, user_input: str = None):
        """
        Main entry point.
        
        Args:
            user_input: Optional pre-provided input. If None, reads from io/input.json
        """
        self.initialize()
        
        # Get input
        if user_input is None:
            input_file = self._resolve_path(self.io_config["input_file"])
            if os.path.exists(input_file):
                with open(input_file, 'r', encoding='utf-8') as f:
                    user_input = f.read().strip()
        
        if not user_input:
            print("\n[Error] No input provided")
            return
        
        print(f"[用户输入] {user_input[:100]}{'...' if len(user_input) > 100 else ''}")
        
        # Execute
        result = self.run_single_turn(user_input)
        
        # Summary
        print(f"\n{'='*60}")
        print(f"  执行完成")
        print(f"{'='*60}")
        print(f"\n[统计]")
        print(f"  LLM 调用: {result.get('llm_calls', 0)}")
        print(f"  工具调用: {result.get('tools_called', 0)}")
        print(f"  迭代次数: {result.get('iterations', 0)}")
        print(f"  类型: {result.get('type', 'unknown')}")
        
        print(f"\n[手动操作计数]")
        if self.llm_client:
            print(f"  你只需要: 1 次 (输入任务)")
        else:
            print(f"  约 {result.get('llm_calls', 1) * 2 + 1} 次手动操作 (每个LLM调用需要2次文件操作)")
        
        print(f"\n[会话] 状态={self.session.status}, 轮次={self.session.turn_count}")
        
        return result


def main():
    """Demo: Direct API mode."""
    # For demo, we use direct mode with a mock LLM client
    # In production, you'd use: LLMClient(api_key=..., base_url=...)
    
    class MockLLMClient:
        """Mock LLM client for demonstration."""
        def __init__(self):
            self.call_count = 0
        
        def chat(self, messages, tools=None):
            self.call_count += 1
            print(f"  [Mock] LLM API called (call #{self.call_count})")
            
            # Simple mock: detect if there are tool_results in context
            last_msg = messages[-1]["content"] if messages else ""
            
            # Check if this is a continuation with tool results
            has_tool_results = "工具执行结果" in last_msg or "tool_results" in str(messages)
            
            if has_tool_results:
                # Second call - return final answer
                return {
                    "content": f"已完成所有工具执行。共执行了 {self.call_count} 次 LLM 调用。任务成功完成。",
                    "tool_calls": []
                }
            else:
                # First call - return tool call (simulate a read file operation)
                return {
                    "content": "我需要先读取目录结构。",
                    "tool_calls": [
                        {"tool": "file_list", "params": {"path": "tests/"}}
                    ]
                }
    
    print("=" * 60)
    print("  Hermes Agent Loop v2 - Demo Mode")
    print("=" * 60)
    
    # Create with mock client for demo
    mock_client = MockLLMClient()
    loop = AgentLoopV2(llm_client=mock_client)
    
    result = loop.run("列出 tests 目录下的所有 Python 文件")
    
    print(f"\n[结果] {result}")
    print(f"\n[对比] 手动操作次数:")
    print(f"  传统架构 (文件模式): ~{(mock_client.call_count * 2 + 1)} 次手动操作")
    print(f"  优化后架构 (直接API): 1 次手动操作")
    print(f"  节省: {(mock_client.call_count * 2 + 1) - 1} 次操作")


if __name__ == "__main__":
    main()