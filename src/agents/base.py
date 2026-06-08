"""
BaseAgent — Class dasar untuk semua agent
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict

class BaseAgent(ABC):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.enabled = True
        self.execution_history: List[Dict] = []
    
    @abstractmethod
    def can_handle(self, message: str) -> bool:
        """Cek apakah agent ini bisa menangani pesan."""
        pass
    
    @abstractmethod
    def execute(self, message: str) -> str:
        """Eksekusi perintah, kembalikan hasil."""
        pass
    
    def get_help(self) -> str:
        """Kembalikan teks bantuan."""
        return f"**{self.name}**: {self.description}"
    
    def log_execution(self, message: str, result: str):
        """Log eksekusi agent"""
        self.execution_history.append({
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "result": result,
            "agent": self.name,
        })
        if len(self.execution_history) > 100:
            self.execution_history.pop(0)
    
    def get_history(self) -> List[Dict]:
        """Get execution history"""
        return self.execution_history
    
    def __repr__(self):
        return f"{self.name}: {self.description}"