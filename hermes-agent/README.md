# Hermes Agent

A Hermes-like Agent framework for Windows 7 with Python 3.7. Designed for air-gapped (offline) environments where you manually interact with a web-based LLM.

## Features

- **Persona**: Customizable agent personality and behavior
- **Memory**: Three-layer memory (short-term, long-term, summaries)
- **Session Persistence**: Multi-turn conversations persist across restarts
- **Tools**: File operations, shell commands, Python execution, document/wiki management
- **Manual LLM Integration**: Designed for environments where you copy prompts to a web interface

## Project Structure

```
hermes-agent/
├── agent/
│   ├── persona.py      # Agent personality
│   ├── config.py       # Configuration
│   └── loop.py         # Core agent loop
├── memory/
│   ├── core.py         # Memory management
│   ├── storage.py      # JSON storage
│   └── context.py      # Context window
├── tools/
│   ├── base.py         # Tool base class
│   ├── registry.py     # Tool registry
│   ├── file_ops.py     # File operations
│   ├── shell.py        # Shell commands
│   ├── python_exec.py  # Python execution
│   └── doc_wiki.py     # Document/wiki tools
├── config/
│   ├── agent_config.json
│   ├── tools_config.json
│   └── persona.json
├── io/                  # Input/output files
│   ├── input.json       # Your task goes here
│   ├── prompt.json      # Generated prompt (copy to LLM)
│   ├── response.json    # Paste LLM response here
│   └── session.json     # Session persistence
├── wiki/                # Knowledge base
└── run.bat              # Windows launcher
```

## Quick Start

### 1. Setup

```bash
# Create conda environment (if needed)
conda create -n hermes python=3.7.4
conda activate hermes

# Install dependencies
pip install -r requirements.txt
```

### 2. Run the Agent

```bash
# Option 1: Double-click run.bat
# Option 2: Command line
python agent\loop.py
```

### 3. Use the Agent

1. **Edit `io/input.json`**:
```json
{
  "type": "input",
  "content": "读取当前目录下的 README.md 文件",
  "timestamp": "2026-05-22T00:00:00+08:00"
}
```

2. **Run the agent**: `python agent\loop.py`

3. **Copy `io/prompt.json`** content to your web-based LLM interface (Open WebUI)

4. **Paste the LLM response** into `io/response.json`:
```json
{
  "type": "response",
  "content": "Here's the file content...",
  "tool_calls": [],
  "timestamp": "2026-05-22T00:00:00+08:00"
}
```

5. **Press Enter** to continue. The agent will:
   - Execute any tools called by the LLM
   - Save results to `io/tool_result.json`
   - Generate the next prompt or output the final answer

6. **Repeat** steps 3-5 until the task is complete

### 4. Multi-turn Conversation

The agent automatically saves conversation history to `io/session.json`. 
To continue a conversation, just add your next input to `io/input.json` and run again.

## Available Tools

| Tool | Description |
|------|-------------|
| `file_read` | Read file contents |
| `file_write` | Write content to file |
| `file_edit` | Replace text in file |
| `file_list` | List directory contents |
| `shell_run` | Execute shell commands |
| `python_run` | Execute Python scripts |
| `doc_read` | Read documents |
| `doc_write` | Write documents |
| `wiki_search` | Search knowledge base |
| `wiki_update` | Create/update wiki entries |

## Configuration

Edit `config/agent_config.json` to customize:
- Memory limits
- Session settings
- Loop parameters

Edit `config/persona.json` to customize:
- Agent name and role
- Guidelines
- Style

## Troubleshooting

**Import errors**: Make sure you're in the hermes-agent directory and have installed requirements.

**JSON parse errors**: Ensure your JSON files are valid (use a JSON validator).

**Tool execution fails**: Check that the file paths and parameters are correct.

## Development

Run tests:
```bash
python tests/test_persona.py
python tests/test_memory.py
python tests/test_tools.py
python tests/test_file_ops.py
python tests/test_shell.py
python tests/test_doc_wiki.py
python tests/test_session.py
python tests/test_loop.py
```

Or run all tests:
```bash
python -m pytest tests/ -v
```
