"""
Agent Loop - The core orchestration engine.
"""
import os
import sys
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent.persona import Persona
from agent.config import AgentConfig
from memory.core import Memory
from session import Session
from tools import get_initialized_registry


class AgentLoop:
    """
    Core Agent Loop that orchestrates the entire agent system.
    
    The loop:
    1. Load or create session
    2. Read input from io/input.json
    3. Build prompt using persona + memory + history
    4. Save prompt to io/prompt.json
    5. Wait for user to paste LLM response to io/response.json
    6. Parse response (tool call or final answer)
    7. If tool call: execute tool, save result, continue
    8. If final answer: save to session, output, done
    """
    
    def __init__(self, config=None):
        self.config = config or AgentConfig()
        self.persona = Persona()
        self.registry = get_initialized_registry()
        self.session = None
        self.memory = None
        self.io_config = self.config.io or {
            "input_file": "io/input.json",
            "prompt_file": "io/prompt.json",
            "response_file": "io/response.json",
            "session_file": "io/session.json",
            "tool_result_file": "io/tool_result.json"
        }
        
        # Resolve paths relative to project root
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        
        # Statistics
        self.stats = {
            "tools_called": 0,
            "tools_succeeded": 0,
            "tools_failed": 0,
            "turns_executed": 0
        }
    
    def _resolve_path(self, filename):
        """Resolve a filename to an absolute path."""
        return os.path.join(self.base_dir, filename)
    
    def _print_header(self, text):
        """Print a section header."""
        print("\n" + "=" * 50)
        print(f"  {text}")
        print("=" * 50)
    
    def _print_step(self, step_num, text):
        """Print a numbered step."""
        print(f"\n[Step {step_num}] {text}")
    
    def initialize(self):
        """Initialize the agent loop."""
        self._print_header("Hermes Agent 启动")
        
        # Load or create session
        session_file = self._resolve_path(self.io_config.get("session_file", "io/session.json"))
        self.session = Session.load_or_create(session_file)
        
        print(f"\n[会话信息]")
        print(f"  Session ID: {self.session.session_id}")
        print(f"  状态: {self.session.status}")
        print(f"  历史轮次: {self.session.turn_count}")
        
        # Initialize memory
        memory_config = self.config.memory
        self.memory = Memory(config=memory_config)
        
        # Load memory from session if available
        if self.session.memory and any(self.session.memory.values()):
            self.memory.load_from_session(self.session.to_dict())
        
        # Register tools for display
        tools = self.registry.list_tools()
        print(f"\n[可用工具] ({len(tools)} 个)")
        for tool in sorted(tools):
            print(f"  - {tool}")
        
        # Reset stats for new run
        self.stats = {
            "tools_called": 0,
            "tools_succeeded": 0,
            "tools_failed": 0,
            "turns_executed": 0
        }
        
        print()
    
    def load_input(self):
        """Load input from io/input.json (supports plain text or JSON)."""
        input_file = self._resolve_path(self.io_config.get("input_file", "io/input.json"))
        
        if not os.path.exists(input_file):
            return None
        
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                raw_content = f.read().strip()
            
            if not raw_content:
                return None
            
            # Try to parse as JSON first
            if raw_content.startswith('{'):
                try:
                    data = json.loads(raw_content)
                    content = data.get("content", "").strip()
                except json.JSONDecodeError:
                    # If JSON parsing fails, treat the whole content as the input
                    content = raw_content
            else:
                # Plain text - treat the whole content as input
                content = raw_content
            
            if content:
                print(f"[用户输入] {content[:200]}{'...' if len(content) > 200 else ''}")
                return content
        except Exception as e:
            print(f"[Error] Failed to load input: {e}")
        
        return None
    
    def build_prompt(self, user_input):
        """
        Build the prompt for the LLM.
        
        Args:
            user_input: The user's input text
            
        Returns:
            dict: The complete prompt
        """
        # Get conversation history from session
        conversation_history = self.session.get_conversation_history()
        
        # Add current input to memory
        self.memory.add_turn("user", user_input)
        
        # Build prompt structure
        prompt = {
            "type": "prompt",
            "system": self.persona.get_system_prompt(),
            "context": {
                "session_id": self.session.session_id,
                "turn_count": self.session.turn_count + 1,
                "memory": self.memory.get_context_for_llm()
            },
            "conversation": conversation_history + [
                {"role": "user", "content": user_input}
            ],
            "tools_available": self.registry.get_all_specs(),
            "timestamp": datetime.now().isoformat()
        }
        
        return prompt
    
    def save_prompt(self, prompt):
        """Save prompt to io/prompt.json."""
        prompt_file = self._resolve_path(self.io_config.get("prompt_file", "io/prompt.json"))
        
        os.makedirs(os.path.dirname(prompt_file), exist_ok=True)
        
        with open(prompt_file, 'w', encoding='utf-8') as f:
            json.dump(prompt, f, ensure_ascii=False, indent=2)
        
        print(f"\n[提示词已生成] -> {prompt_file}")
        print(f"  System: {len(prompt['system'])} chars")
        print(f"  Conversation: {len(prompt['conversation'])} messages")
        print(f"  Tools: {len(prompt['tools_available'])} available")
    
    def load_response(self):
        """Load LLM response from io/response.json."""
        response_file = self._resolve_path(self.io_config.get("response_file", "io/response.json"))
        
        if not os.path.exists(response_file):
            return None
        
        try:
            with open(response_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception as e:
            print(f"[Error] Failed to load response: {e}")
            return None
    
    def parse_response(self, response):
        """
        Parse the LLM response.
        
        Returns:
            dict: {
                "type": "final_answer" | "tool_call",
                "content": str,
                "tool_calls": list (if tool_call)
            }
        """
        if not response:
            return None
        
        content = response.get("content", "").strip()
        tool_calls = response.get("tool_calls", [])
        
        if tool_calls:
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
    
    def execute_tool(self, tool_call):
        """
        Execute a tool call.
        
        Args:
            tool_call: dict with "tool" and "params" keys
            
        Returns:
            dict: Tool execution result
        """
        tool_name = tool_call.get("tool")
        params = tool_call.get("params", {})
        
        self.stats["tools_called"] += 1
        
        print(f"\n  ┌──────────────────────────────────────────")
        print(f"  │ [Tool #{self.stats['tools_called']}] {tool_name}")
        print(f"  │ 参数: {json.dumps(params, ensure_ascii=False)[:100]}")
        print(f"  └──────────────────────────────────────────")
        
        result = self.registry.execute(tool_name, **params)
        
        # Print result
        if result.get("success"):
            self.stats["tools_succeeded"] += 1
            result_preview = str(result.get("result", ""))[:150]
            print(f"  ✓ 成功: {result_preview}{'...' if len(str(result.get('result', ''))) > 150 else ''}")
        else:
            self.stats["tools_failed"] += 1
            print(f"  ✗ 失败: {result.get('error', 'Unknown error')}")
        
        # Save tool result
        tool_result_file = self._resolve_path(
            self.io_config.get("tool_result_file", "io/tool_result.json")
        )
        
        tool_result = {
            "type": "tool_result",
            "tool": tool_name,
            "params": params,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
        with open(tool_result_file, 'w', encoding='utf-8') as f:
            json.dump(tool_result, f, ensure_ascii=False, indent=2)
        
        return result
    
    def execute_turn(self, user_input):
        """
        Execute a single turn (input -> prompt -> response -> action).
        
        Args:
            user_input: User's input text
            
        Returns:
            dict: Turn result
        """
        self.stats["turns_executed"] += 1
        turn_num = self.session.turn_count + 1
        
        print(f"\n{'='*50}")
        print(f"  Turn {turn_num} 开始")
        print(f"{'='*50}")
        
        # Step 1: Build prompt
        self._print_step(1, "构建提示词")
        prompt = self.build_prompt(user_input)
        
        # Step 2: Save prompt
        self._print_step(2, "保存提示词")
        self.save_prompt(prompt)
        
        # Step 3: Wait for LLM response
        self._print_step(3, "等待大模型响应")
        print("\n  请将提示词复制到 Open WebUI 网页")
        print("  等待大模型响应后，将响应粘贴到 io/response.json")
        print("\n  按 Enter 继续...")
        input()
        
        # Step 4: Load and parse response
        self._print_step(4, "解析大模型响应")
        response = self.load_response()
        if not response:
            print("[Error] response.json 为空或不存在")
            return {"success": False, "error": "No response"}
        
        # Show response preview
        content = response.get("content", "")
        print(f"  LLM 文本回复 ({len(content)} 字符):")
        print(f"  {content[:200]}{'...' if len(content) > 200 else ''}")
        
        parsed = self.parse_response(response)
        
        if parsed["type"] == "tool_call":
            # Step 5: Execute tools
            self._print_step(5, "执行工具调用")
            print(f"\n  检测到 {len(parsed['tool_calls'])} 个工具调用:")
            
            tool_results = []
            for i, tool_call in enumerate(parsed["tool_calls"], 1):
                print(f"\n  [{i}] {tool_call.get('tool')}")
                result = self.execute_tool(tool_call)
                tool_results.append({
                    "tool": tool_call.get("tool"),
                    "params": tool_call.get("params"),
                    "result": result
                })
            
            # Print tool summary
            print(f"\n  ┌──────────────────────────────────────────")
            print(f"  │ 工具调用统计:")
            print(f"  │   总计: {self.stats['tools_called']}")
            print(f"  │   成功: {self.stats['tools_succeeded']}")
            print(f"  │   失败: {self.stats['tools_failed']}")
            print(f"  └──────────────────────────────────────────")
            
            # Save turn to session
            turn_data = {
                "input": user_input,
                "prompt": prompt,
                "response": response,
                "tool_calls": parsed["tool_calls"],
                "tool_results": tool_results
            }
            self.session.add_turn(turn_data)
            self.session.save()
            
            # Update memory
            self.memory.save_to_session()
            
            # Add assistant response to memory
            if parsed["content"]:
                self.memory.add_turn("assistant", parsed["content"])
            
            # Ask user to update response.json with tool results for next iteration
            print("\n" + "=" * 50)
            print("  [下一步]")
            print("  请将工具执行结果添加到 io/response.json")
            print("  格式参考 io/tool_result.json")
            print("  然后按 Enter 继续让大模型处理结果...")
            print("=" * 50)
            input()
            
            # Reload response which should now include tool results
            response = self.load_response()
            if response:
                content = response.get("content", "")
                print(f"\n  更新后的 LLM 回复 ({len(content)} 字符):")
                print(f"  {content[:200]}{'...' if len(content) > 200 else ''}")
                
                parsed = self.parse_response(response)
                
                # Check if LLM provided final answer after tool results
                if parsed["type"] == "final_answer":
                    print("\n  检测到最终回答 ✓")
                else:
                    print("\n  继续工具调用...")
            
            return {
                "success": True,
                "type": "tool_call",
                "tool_results": tool_results
            }
        
        else:
            # Final answer
            self._print_step(5, "最终回答")
            
            print(f"\n  ┌──────────────────────────────────────────")
            print(f"  │ 最终回答:")
            print(f"  └──────────────────────────────────────────")
            print(f"  {parsed['content'][:300]}{'...' if len(parsed['content']) > 300 else ''}")
            
            turn_data = {
                "input": user_input,
                "prompt": prompt,
                "response": response,
                "final_answer": parsed["content"]
            }
            self.session.add_turn(turn_data)
            self.session.mark_completed()
            
            # Update memory
            self.memory.add_turn("assistant", parsed["content"])
            self.memory.save_to_session()
            
            return {
                "success": True,
                "type": "final_answer",
                "content": parsed["content"]
            }
    
    def run(self):
        """Run the main agent loop."""
        self.initialize()
        
        # Load input
        user_input = self.load_input()
        
        if not user_input:
            print("\n[Error] io/input.json 为空或不存在")
            print("[Error] 请在 io/input.json 中写入你的任务")
            return
        
        # Execute turn
        result = self.execute_turn(user_input)
        
        # Print final summary
        self._print_header("执行完成")
        print(f"\n[统计]")
        print(f"  执行轮次: {self.stats['turns_executed']}")
        print(f"  工具调用: {self.stats['tools_called']}")
        print(f"  成功: {self.stats['tools_succeeded']}")
        print(f"  失败: {self.stats['tools_failed']}")
        print(f"\n[会话]")
        print(f"  状态: {self.session.status}")
        print(f"  历史轮次: {self.session.turn_count}")
        print(f"  Session ID: {self.session.session_id}")
        print("\n" + "=" * 50)


def main():
    """Main entry point."""
    loop = AgentLoop()
    loop.run()


if __name__ == "__main__":
    main()