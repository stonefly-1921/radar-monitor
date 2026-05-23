# Task: Run MyAgent with REPL simulation using Qwen desktop dialog
# Strategy:
# 1. Start loop_v2.py (it will wait for input.txt)
# 2. Generate prompt.txt
# 3. Copy prompt to Qwen dialog
# 4. Paste Qwen response to response.txt
# 5. Let loop_v2.py parse and execute tools
# 6. Repeat until final answer

import subprocess
import time
import os
import sys
import json

# Add project root to path
sys.path.insert(0, 'C:/Users/15041/.openclaw/workspace/MyAgent')

from agent.loop_v2 import AgentLoopV2

# We need to manually simulate the REPL workflow:
# Step 1: Initialize - generates prompt.txt
# Step 2: User copies prompt.txt -> pastes to Qwen desktop
# Step 3: User pastes Qwen response -> response.txt
# Step 4: Loop parses response and executes tools

# Since we can't actually read the Qwen dialog output,
# we'll run a simplified test that generates prompt.txt
# and then manually feed a simulated LLM response

# First, let's just generate the prompt.txt
loop = AgentLoopV2()
loop.initialize()

# Build prompt for our task
user_input = "请帮我统计一下 tests 目录下有多少个 Python 文件，然后把文件列表列出来。"
prompt_text = loop.build_prompt_text(user_input, turn=1, tool_results=None, conversation=[])
loop._save_prompt(prompt_text)

print("PROMPT GENERATED - saved to io/prompt.txt")
print(f"Prompt length: {len(prompt_text)} chars")
print("\n--- PROMPT CONTENT ---")
print(prompt_text[:500])
print("... [truncated]")