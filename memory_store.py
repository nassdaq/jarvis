import os
import json
from datetime import datetime
from typing import List, Dict, Optional

MEMORY_DIR = "memory"
MEMORY_FILE = os.path.join(MEMORY_DIR, "memory.jsonl")

os.makedirs(MEMORY_DIR, exist_ok=True)

class MemoryStore:
    def __init__(self, path: str = MEMORY_FILE):
        self.path = path

    def add(self, role: str, content: str, meta: Optional[Dict] = None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "content": content,
            "meta": meta or {}
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def get_recent(self, limit: int = 20) -> List[Dict]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return [json.loads(line) for line in lines[-limit:]]

    def summarize(self, limit: int = 50) -> str:
        # Simple concatenation for now; can be replaced with LLM summarization
        history = self.get_recent(limit)
        return "\n".join(f"{e['role']}: {e['content']}" for e in history)

# Usage:
# memory = MemoryStore()
# memory.add("user", "Hello, JARVIS!")
# memory.add("assistant", "Hello! How can I help?")
# print(memory.summarize())