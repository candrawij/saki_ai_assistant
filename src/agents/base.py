"""
BaseAgent — Class dasar untuk semua agent
"""

from abc import ABC, abstractmethod

class BaseAgent(ABC):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.enabled = True
    
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