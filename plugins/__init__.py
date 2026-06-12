"""
Saki Plugin System
Fase 4: Extensible plugin architecture
"""

from .base import BasePlugin
from .registry import PluginRegistry
from .loader import load_all_plugins, get_plugin_manager

__all__ = ['BasePlugin', 'PluginRegistry', 'load_all_plugins', 'get_plugin_manager']