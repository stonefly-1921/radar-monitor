"""
Session management - handles session persistence for multi-turn conversations.
"""
import os
import json
import uuid
from datetime import datetime


class Session:
    """
    Manages session persistence for multi-turn conversations.
    
    A Session contains:
    - session_id: Unique identifier
    - created_at: Creation timestamp
    - updated_at: Last update timestamp
    - status: 'in_progress' or 'completed'
    - turns: List of conversation turns
    - memory: Memory state for persistence
    """
    
    def __init__(self, session_file=None):
        self.session_file = session_file or os.path.join(
            os.path.dirname(__file__), "io", "session.json"
        )
        self.session_id = None
        self.created_at = None
        self.updated_at = None
        self.status = "in_progress"
        self.turns = []
        self.memory = {
            "short_term": [],
            "long_term": [],
            "summaries": []
        }
        self.config = {}
    
    @classmethod
    def load_or_create(cls, session_file=None):
        """
        Load an existing session or create a new one.
        
        Args:
            session_file: Path to session file
            
        Returns:
            Session instance (loaded or new)
        """
        session = cls(session_file=session_file)
        
        if os.path.exists(session_file):
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                session.session_id = data.get("session_id", session._generate_id())
                session.created_at = data.get("created_at", datetime.now().isoformat())
                session.updated_at = data.get("updated_at", datetime.now().isoformat())
                session.status = data.get("status", "in_progress")
                session.turns = data.get("turns", [])
                session.memory = data.get("memory", session.memory)
                session.config = data.get("config", {})
                
                return session
            except Exception as e:
                print(f"Warning: Failed to load session, creating new: {e}")
        
        # Create new session
        session._create_new()
        return session
    
    def _generate_id(self):
        """Generate a unique session ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"session_{timestamp}_{unique_id}"
    
    def _create_new(self):
        """Initialize a new session."""
        self.session_id = self._generate_id()
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.status = "in_progress"
        self.turns = []
        self.memory = {
            "short_term": [],
            "long_term": [],
            "summaries": []
        }
    
    def add_turn(self, turn_data):
        """
        Add a turn to the session.
        
        Args:
            turn_data: dict containing turn information
                - turn: Turn number
                - input: User input
                - prompt: Generated prompt
                - response: LLM response
                - tool_calls: List of tool calls
                - tool_results: List of tool results
                - final_answer: Final answer from LLM
        """
        turn = {
            "turn": len(self.turns) + 1,
            "input": turn_data.get("input", ""),
            "prompt": turn_data.get("prompt", {}),
            "response": turn_data.get("response", {}),
            "tool_calls": turn_data.get("tool_calls", []),
            "tool_results": turn_data.get("tool_results", []),
            "final_answer": turn_data.get("final_answer", ""),
            "timestamp": datetime.now().isoformat()
        }
        
        self.turns.append(turn)
        self.updated_at = datetime.now().isoformat()
    
    def get_last_turn(self):
        """Get the last turn in the session."""
        if self.turns:
            return self.turns[-1]
        return None
    
    def get_turn_count(self):
        """Get the number of turns in the session."""
        return len(self.turns)
    
    @property
    def turn_count(self):
        """Number of turns in session (property accessor)."""
        return len(self.turns)
    
    def get_conversation_history(self):
        """
        Get conversation history as a list of user/assistant messages.
        
        Returns:
            List of dicts with 'role' and 'content' keys
        """
        history = []
        for turn in self.turns:
            if turn.get("input"):
                history.append({
                    "role": "user",
                    "content": turn["input"]
                })
            if turn.get("final_answer"):
                history.append({
                    "role": "assistant", 
                    "content": turn["final_answer"]
                })
        return history
    
    def save(self):
        """Save the session to file."""
        os.makedirs(os.path.dirname(self.session_file), exist_ok=True)
        
        data = {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status,
            "turns": self.turns,
            "memory": self.memory,
            "config": self.config
        }
        
        with open(self.session_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def mark_completed(self):
        """Mark the session as completed."""
        self.status = "completed"
        self.updated_at = datetime.now().isoformat()
        self.save()
    
    def reset(self):
        """Reset the session to start fresh."""
        self._create_new()
        self.save()
    
    def deduplicate_turns(self):
        """
        对 session.turns 去重压缩。
        规则：
        - 连续重复的 input 保留最后一个
        - 合并相同 input 的多次 tool_calls（只保留最后一次的结果）
        
        去重后保留最后一个 turn（而非第一个），因为最后的结果通常是最完整的。
        """
        if not self.turns:
            return
        
        # 建立去重后的 turns 列表
        deduped = []
        for turn in self.turns:
            input_text = turn.get('input', '').strip()
            
            # 跳过完全重复前面内容的 turn
            if deduped and deduped[-1].get('input', '').strip() == input_text:
                # 如果新 turn 有 final_answer 或 tool_results，而上一个没有，替换
                last = deduped[-1]
                has_new_content = (
                    turn.get('final_answer') and not last.get('final_answer')
                ) or (
                    turn.get('tool_results') and not last.get('tool_results')
                )
                if has_new_content:
                    deduped.pop()
                    deduped.append(turn)
                # 否则跳过（丢弃这个重复的 turn）
                continue
            
            deduped.append(turn)
        
        self.turns = deduped
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self):
        """Export session as dict."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status,
            "turns": self.turns,
            "turn_count": len(self.turns),
            "memory": self.memory
        }
    
    def __repr__(self):
        return f"Session(id={self.session_id}, turns={len(self.turns)}, status={self.status})"