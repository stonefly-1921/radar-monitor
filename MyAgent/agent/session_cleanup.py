# -*- coding: utf-8 -*-
"""
Session deduplication and cleanup utility.

Run standalone: python -m agent.session_cleanup
Or import: from agent.session_cleanup import cleanup_sessions
"""
import os
import sys
import json
import hashlib
import datetime
import pathlib
from typing import List, Dict, Tuple

SESSION_DIR = pathlib.Path('C:/Users/15041/.openclaw/agents/main/sessions')
MEMORY_DIR = pathlib.Path('C:/Users/15041/.openclaw/workspace/memory')

def get_content_hash(content: str) -> str:
    """Get SHA256 hash of message content."""
    if isinstance(content, dict):
        content = json.dumps(content, sort_keys=True)
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def load_session_messages(session_file: pathlib.Path) -> List[Dict]:
    """Load messages from a .jsonl session file."""
    messages = []
    try:
        with open(session_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        messages.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except (IOError, OSError):
        pass
    return messages

def deduplicate_messages(messages: List[Dict]) -> Tuple[List[Dict], int]:
    """Remove consecutive duplicate USER/AGENT pairs.

    Returns (deduplicated_messages, removed_count).
    """
    if not messages:
        return [], 0

    deduplicated = []
    removed = 0
    last_user_hash = None
    last_agent_hash = None

    for msg in messages:
        content_hash = get_content_hash(msg.get('content', ''))

        if msg.get('role') == 'user':
            if content_hash == last_user_hash:
                removed += 1
            else:
                deduplicated.append(msg)
                last_user_hash = content_hash
                last_agent_hash = None  # Reset on new user message
        elif msg.get('role') == 'assistant':
            if content_hash == last_agent_hash:
                removed += 1
            else:
                deduplicated.append(msg)
                last_agent_hash = content_hash
        else:
            deduplicated.append(msg)

    return deduplicated, removed

def cleanup_sessions() -> Dict:
    """Main cleanup function.

    Returns dict with:
      - sessions_found: int
      - total_messages: int
      - unique_messages: int
      - duplicates_removed: int
      - sessions_saved: int
      - memory_file: str
    """
    if not SESSION_DIR.exists():
        return {'error': 'Session directory not found'}

    # Find all .jsonl files
    session_files = list(SESSION_DIR.glob('*.jsonl'))
    if not session_files:
        return {'sessions_found': 0, 'total_messages': 0, 'unique_messages': 0,
                'duplicates_removed': 0, 'sessions_saved': 0}

    # Sort by modification time (oldest first)
    session_files.sort(key=lambda f: f.stat().st_mtime)

    all_unique_messages = []
    total_messages = 0
    duplicates_removed = 0
    processed_files = []

    for session_file in session_files:
        messages = load_session_messages(session_file)
        if not messages:
            continue

        total_messages += len(messages)
        deduped, removed = deduplicate_messages(messages)
        duplicates_removed += removed
        all_unique_messages.extend(deduped)
        if deduped:
            processed_files.append(session_file)

    # Write consolidated messages to memory
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    memory_file = MEMORY_DIR / f'{today}-session-dedup.md'
    MEMORY_DIR.mkdir(exist_ok=True)

    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    lines = [
        f"## Session deduplication saved at {timestamp}",
        "",
        f"Original: {len(session_files)} sessions, {total_messages} total messages",
        f"After dedup: {len(all_unique_messages)} unique messages",
        f"Removed: {duplicates_removed} duplicate messages",
        "",
        "### Unique session messages:",
        ""
    ]

    for msg in all_unique_messages[:100]:  # First 100 to keep file manageable
        role = msg.get('role', 'unknown')
        content = msg.get('content', '')
        if isinstance(content, str):
            preview = content[:100] + ('...' if len(content) > 100 else '')
        else:
            preview = str(content)[:100]
        lines.append(f"- [{role}] {preview}")

    if len(all_unique_messages) > 100:
        lines.append(f"... and {len(all_unique_messages) - 100} more messages")

    memory_file.write_text('\n'.join(lines), encoding='utf-8')

    # Delete processed session files
    for session_file in processed_files:
        try:
            session_file.unlink()
        except OSError:
            pass

    return {
        'sessions_found': len(session_files),
        'total_messages': total_messages,
        'unique_messages': len(all_unique_messages),
        'duplicates_removed': duplicates_removed,
        'sessions_saved': len(processed_files),
        'memory_file': str(memory_file)
    }

if __name__ == '__main__':
    result = cleanup_sessions()
    print('Session cleanup results:')
    for key, value in result.items():
        print(f'  {key}: {value}')