"""
Base Plugin Class
Semua plugin inherit dari sini
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from enum import Enum


class PluginStatus(Enum):
    DISABLED = "disabled"
    ENABLED = "enabled"
    ERROR = "error"
    LOADING = "loading"


class BasePlugin(ABC):
    """
    Base class untuk semua plugin Saki.
    
    Setiap plugin harus implement:
    - name: str
    - description: str
    - version: str
    - on_enable()
    - on_disable()
    - get_commands() -> List[Dict]
    - execute(command: str, args: Dict) -> str
    """
    
    def __init__(self):
        self.status = PluginStatus.DISABLED
        self._config = {}
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Nama plugin."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Deskripsi plugin."""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Versi plugin."""
        pass
    
    @property
    def icon(self) -> str:
        """Icon emoji."""
        return "🔌"
    
    @abstractmethod
    def on_enable(self) -> bool:
        """
        Dipanggil saat plugin di-enable.
        Return True kalau berhasil.
        """
        pass
    
    @abstractmethod
    def on_disable(self):
        """Dipanggil saat plugin di-disable."""
        pass
    
    @abstractmethod
    def get_commands(self) -> List[Dict]:
        """
        Return list of commands yang didukung plugin.
        
        Format:
        [
            {
                "name": "speech_start",
                "description": "Mulai speech recognition",
                "keywords": ["dengarkan", "listen", "speech"],
                "handler": "start_listening",
            }
        ]
        """
        pass
    
    @abstractmethod
    def execute(self, command: str, args: Optional[Dict] = None) -> str:
        """
        Eksekusi command.
        
        Args:
            command: Nama command
            args: Argumen tambahan
        
        Returns:
            Hasil eksekusi (string)
        """
        pass
    
    def get_config(self) -> Dict:
        """Get plugin config."""
        return self._config
    
    def set_config(self, config: Dict):
        """Set plugin config."""
        self._config.update(config)
    
    def get_info(self) -> Dict:
        """Get plugin info."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "icon": self.icon,
            "status": self.status.value,
            "commands": len(self.get_commands()),
        }
    
    def enable(self) -> bool:
        """Enable plugin."""
        self.status = PluginStatus.LOADING
        try:
            if self.on_enable():
                self.status = PluginStatus.ENABLED
                return True
            else:
                self.status = PluginStatus.ERROR
                return False
        except Exception as e:
            self.status = PluginStatus.ERROR
            print(f"Plugin {self.name} error: {e}")
            return False
    
    def disable(self):
        """Disable plugin."""
        try:
            self.on_disable()
        except:
            pass
        self.status = PluginStatus.DISABLED
    
    def __repr__(self):
        return f"Plugin({self.name} v{self.version})"