"""
Context window management - controls how much context is sent to LLM.
"""
from datetime import datetime


class ContextWindow:
    """Manages context window size and truncation."""
    
    def __init__(self, max_turns=20):
        self.max_turns = max_turns
    
    def truncate(self, conversation):
        """
        Truncate conversation to fit within max_turns.
        
        Args:
            conversation: List of conversation turns
            
        Returns:
            Truncated conversation list
        """
        if len(conversation) <= self.max_turns:
            return conversation
        
        # Keep recent turns, discard older ones
        return conversation[-self.max_turns:]
    
    def truncate_with_summary(self, conversation, summary):
        """
        Truncate conversation but prepend summary.
        
        Args:
            conversation: List of conversation turns
            summary: Summary text to prepend
            
        Returns:
            List with summary prepended
        """
        recent = self.truncate(conversation)
        return [{
            "role": "system",
            "content": f"[历史摘要] {summary}",
            "timestamp": datetime.now().isoformat()
        }] + recent