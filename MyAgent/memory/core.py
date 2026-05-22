"""
Memory core - Three-layer memory management.
"""
import os
import json
from datetime import datetime
from .storage import MemoryStorage
from .context import ContextWindow
from .token_count import total_tokens


class Memory:
    """
    Three-layer memory architecture:
    - Short-term: Current conversation turns
    - Long-term: Persistent knowledge
    - Summary: Compressed context
    """

    def __init__(self, config=None):
        self.config = config or {}
        self.storage = MemoryStorage()
        self.context_window = ContextWindow(
            max_turns=self.config.get("short_term_max", 100)
        )
        self.summary_threshold = self.config.get("summary_threshold", 80)
        # Token compression threshold (200K default, 20% buffer)
        self.max_tokens = self.config.get("max_tokens", 200000)
        self._needs_summary = False  # Flag: LLM summary needed

        # Load existing memory
        self.data = self.storage.load()

        # Initialize if empty
        if "short_term" not in self.data:
            self.data = self._default_data()

    def _default_data(self):
        return {
            "short_term": [],
            "long_term": [],
            "summaries": [],
            "updated_at": datetime.now().isoformat()
        }

    def add_turn(self, role, content, metadata=None):
        """
        Add a conversation turn to short-term memory.
        """
        turn = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        if metadata:
            turn["metadata"] = metadata

        self.data["short_term"].append(turn)
        self.data["updated_at"] = datetime.now().isoformat()

        # Check token-based compression trigger
        if self._should_compress():
            self._needs_summary = True

        self._save()

    def _should_compress(self) -> bool:
        """Check if compression is needed (token-based, not turn-based)."""
        tokens = total_tokens(self.data["short_term"])
        return tokens > self.max_tokens

    def _auto_summarize(self):
        """
        Token limit reached - flag for LLM summarization.
        Actual summarization is deferred to AgentLoop which calls LLM.
        """
        self._needs_summary = True

    def set_needs_summary(self, value: bool):
        self._needs_summary = value

    def get_needs_summary(self) -> bool:
        return self._needs_summary

    def get_summary_context(self) -> dict:
        """
        Returns history content for LLM to generate summary.
        Called by AgentLoop when _needs_summary is True.
        """
        short_term = self.data["short_term"]
        # Exclude last 3 turns (still in short_term after compression)
        material = short_term[:-3] if len(short_term) > 3 else short_term
        history_lines = []
        for t in material:
            role = "用户" if t["role"] == "user" else "助手"
            content = t["content"][:200]
            history_lines.append(f"[{role}]: {content}")
        history_text = "\n".join(history_lines) if history_lines else "(无历史)"
        tokens_est = total_tokens(short_term)
        return {
            "history_text": history_text,
            "history_lines": len(material),
            "current_tokens": tokens_est,
            "threshold_tokens": self.max_tokens
        }

    def add_long_term(self, content, tags=None):
        """Add content to long-term memory."""
        entry = {
            "content": content,
            "tags": tags or [],
            "timestamp": datetime.now().isoformat()
        }
        self.data["long_term"].append(entry)
        self._save()

    def search(self, query):
        """
        Search memory for relevant content.
        """
        results = []
        query_lower = query.lower()

        for turn in self.data["short_term"]:
            if query_lower in turn.get("content", "").lower():
                results.append({
                    "source": "short_term",
                    "content": turn["content"],
                    "timestamp": turn.get("timestamp")
                })

        for entry in self.data["long_term"]:
            if query_lower in entry.get("content", "").lower():
                results.append({
                    "source": "long_term",
                    "content": entry["content"],
                    "tags": entry.get("tags", []),
                    "timestamp": entry.get("timestamp")
                })

        for summary in self.data["summaries"]:
            if query_lower in summary.get("summary", "").lower():
                results.append({
                    "source": "summary",
                    "content": summary["summary"],
                    "timestamp": summary.get("timestamp")
                })

        return results

    def get_conversation(self):
        """Get current conversation history."""
        return self.data["short_term"].copy()

    def get_context_for_llm(self):
        """
        Get formatted context for LLM prompt.
        """
        conversation = self.context_window.truncate(self.data["short_term"])

        return {
            "conversation": conversation,
            "recent_summaries": self.data["summaries"][-3:] if self.data["summaries"] else [],
            "long_term_count": len(self.data["long_term"])
        }

    def summarize(self, summary_text):
        """
        Add a summary to memory.
        """
        self.data["summaries"].append({
            "summary": summary_text,
            "timestamp": datetime.now().isoformat(),
            "turns_before": len(self.data["short_term"])
        })

        # Keep only recent summaries
        if len(self.data["summaries"]) > 5:
            self.data["summaries"] = self.data["summaries"][-5:]

        self._save()

    def compress_conversation(self, summary_text):
        """
        Compress conversation history with a summary.
        """
        self.summarize(summary_text)
        # Keep only the most recent turns (3 by default)
        keep = min(3, len(self.data["short_term"]))
        self.data["short_term"] = self.data["short_term"][-keep:]
        self._save()

    def load_from_session(self, session_data):
        """Load memory from session data."""
        if "memory" in session_data:
            self.data = session_data["memory"]
        else:
            if "turns" in session_data:
                self.data["short_term"] = []
                for turn in session_data.get("turns", []):
                    if "input" in turn:
                        self.add_turn("user", turn["input"])
                    if "final_answer" in turn:
                        self.add_turn("assistant", turn["final_answer"])

    def save_to_session(self):
        """Export memory data for session storage."""
        return self.data.copy()

    def _save(self):
        """Save memory to storage."""
        self.storage.save(self.data)

    def clear(self):
        """Clear all memory."""
        self.data = self._default_data()
        self._save()

    @property
    def turn_count(self):
        """Get current turn count."""
        return len(self.data["short_term"])