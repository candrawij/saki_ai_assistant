"""
Plugin Registry
Manage semua plugin yang terdaftar
"""

from typing import Dict, List, Optional
from .base import BasePlugin, PluginStatus


class PluginRegistry:
    """Registry untuk semua plugin Saki."""
    
    def __init__(self):
        self._plugins: Dict[str, BasePlugin] = {}
    
    def register(self, plugin: BasePlugin) -> bool:
        """
        Register plugin ke registry.
        Return False kalau sudah ada dengan nama sama.
        """
        if plugin.name in self._plugins:
            print(f"Plugin '{plugin.name}' already registered")
            return False
        
        self._plugins[plugin.name] = plugin
        return True
    
    def unregister(self, name: str) -> bool:
        """Hapus plugin dari registry."""
        if name in self._plugins:
            plugin = self._plugins[name]
            if plugin.status == PluginStatus.ENABLED:
                plugin.disable()
            del self._plugins[name]
            return True
        return False
    
    def get(self, name: str) -> Optional[BasePlugin]:
        """Get plugin by name."""
        return self._plugins.get(name)
    
    def get_all(self) -> List[BasePlugin]:
        """Get semua plugin."""
        return list(self._plugins.values())
    
    def get_enabled(self) -> List[BasePlugin]:
        """Get plugin yang enabled."""
        return [p for p in self._plugins.values() if p.status == PluginStatus.ENABLED]
    
    def get_disabled(self) -> List[BasePlugin]:
        """Get plugin yang disabled."""
        return [p for p in self._plugins.values() if p.status == PluginStatus.DISABLED]
    
    def enable(self, name: str) -> bool:
        """Enable plugin by name."""
        plugin = self.get(name)
        if plugin:
            return plugin.enable()
        return False
    
    def disable(self, name: str) -> bool:
        """Disable plugin by name."""
        plugin = self.get(name)
        if plugin:
            plugin.disable()
            return True
        return False
    
    def get_all_commands(self) -> Dict[str, List[Dict]]:
        """
        Get semua commands dari plugin yang enabled.
        Returns: {plugin_name: [commands]}
        """
        commands = {}
        for plugin in self.get_enabled():
            cmds = plugin.get_commands()
            if cmds:
                commands[plugin.name] = cmds
        return commands
    
    def find_handler(self, user_message: str) -> Optional[tuple]:
        """
        Cari plugin yang bisa handle pesan user.
        Returns: (plugin, command_dict) atau None
        """
        msg = user_message.lower()
        
        for plugin in self.get_enabled():
            for cmd in plugin.get_commands():
                keywords = cmd.get("keywords", [])
                if any(kw in msg for kw in keywords):
                    return plugin, cmd
        
        return None
    
    def get_stats(self) -> Dict:
        """Statistik registry."""
        all_plugins = self.get_all()
        enabled = self.get_enabled()
        return {
            "total": len(all_plugins),
            "enabled": len(enabled),
            "disabled": len(all_plugins) - len(enabled),
            "plugins": [p.get_info() for p in all_plugins],
        }