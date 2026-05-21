"""
Memory core - Three-layer memory management.
"""
import os
import json
from datetime import datetime
from .storage import MemoryStorage
from .context import ContextWindow


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
            max_turns=self.config.get("short_term_max", 20)
        )
        self.summary_threshold = self.config.get("summary_threshold", 10)
        
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
        
        Args:
            role: "user" or "assistant"
            content: Message content
            metadata: Optional metadata dict
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
        
        # Check if summarization is needed
        if len(self.data["short_term"]) >= self.summary_threshold:
            self._auto_summarize()
        
        self._save()
    
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
        
        Args:
            query: Search query string
            
        Returns:
            List of relevant memory entries
        """
        results = []
        query_lower = query.lower()
        
        # Search short-term
        for turn in self.data["short_term"]:
            if query_lower in turn.get("content", "").lower():
                results.append({
                    "source": "short_term",
                    "content": turn["content"],
                    "timestamp": turn.get("timestamp")
                })
        
        # Search long-term
        for entry in self.data["long_term"]:
            if query_lower in entry.get("content", "").lower():
                results.append({
                    "source": "long_term",
                    "content": entry["content"],
                    "tags": entry.get("tags", []),
                    "timestamp": entry.get("timestamp")
                })
        
        # Search summaries
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
        
        Returns:
            dict with system context, recent conversation, and relevant memories
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
        
        Args:
            summary_text: Summary content
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
    
    def _auto_summarize(self):
        """
        Auto-summarize when conversation gets too long.
        This is a placeholder - actual summarization should be done by LLM.
        """
        # Mark that we need summarization
        # The LLM will handle actual summary generation
        pass
    
    def compress_conversation(self, summary_text):
        """
        Compress conversation history with a summary.
        
        Args:
            summary_text: Summary to replace old turns
        """
        self.summarize(summary_text)
        # Keep only the most recent turns
        keep = min(3, len(self.data["short_term"]))
        self.data["short_term"] = self.data["short_term"][-keep:]
        self._save()
    
    def load_from_session(self, session_data):
        """Load memory from session data."""
        if "memory" in session_data:
            self.data = session_data["memory"]
        else:
            # Try to restore from turns
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