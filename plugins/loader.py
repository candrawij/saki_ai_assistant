"""
Plugin Loader
Auto-load plugins dari folder plugins/
"""

import os
import importlib
import logging
from pathlib import Path
from typing import List

from .registry import PluginRegistry
from .base import BasePlugin

logger = logging.getLogger("saki.plugins")

# Global registry
_registry = PluginRegistry()


def get_plugin_manager() -> PluginRegistry:
    """Get global plugin registry."""
    return _registry


def load_plugin_from_path(plugin_path: Path) -> List[BasePlugin]:
    """
    Load plugin dari folder.
    
    Struktur folder:
    plugins/speech/
        __init__.py
        plugin.py  (ada class Plugin)
    """
    plugins = []
    
    if not plugin_path.is_dir():
        return plugins
    
    # Cek plugin.py
    plugin_file = plugin_path / "plugin.py"
    if not plugin_file.exists():
        return plugins
    
    try:
        # Import module
        module_name = f"plugins.{plugin_path.name}.plugin"
        module = importlib.import_module(module_name)
        
        # Cari class Plugin
        if hasattr(module, "Plugin"):
            plugin_class = getattr(module, "Plugin")
            plugin_instance = plugin_class()
            
            if isinstance(plugin_instance, BasePlugin):
                plugins.append(plugin_instance)
                logger.info(f"Loaded plugin: {plugin_instance.name}")
            else:
                logger.warning(f"Plugin class in {plugin_path.name} doesn't inherit BasePlugin")
        
    except Exception as e:
        logger.error(f"Failed to load plugin from {plugin_path}: {e}")
    
    return plugins


def load_all_plugins() -> PluginRegistry:
    """
    Load semua plugin dari folder plugins/.
    Skip folder yang diawali underscore.
    """
    global _registry
    
    plugins_dir = Path(__file__).parent
    
    # Cari semua subfolder (kecuali yang diawali _)
    for item in plugins_dir.iterdir():
        if item.is_dir() and not item.name.startswith("_") and not item.name.startswith("__"):
            loaded = load_plugin_from_path(item)
            for plugin in loaded:
                if not _registry.get(plugin.name):
                    _registry.register(plugin)
    
    if not hasattr(load_all_plugins, "_logged"):
        logger.info(f"Plugin system initialized: {_registry.get_stats()['total']} plugins found")
        load_all_plugins._logged = True
    
    return _registry