"""Test Plugin System"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from plugins.loader import load_all_plugins, get_plugin_manager

print("=" * 50)
print("Testing Plugin System")
print("=" * 50)
print()

# Load plugins
registry = load_all_plugins()
stats = registry.get_stats()

print(f"Plugins found: {stats['total']}")
for p in stats['plugins']:
    print(f"  {p['icon']} {p['name']} v{p['version']} - {p['status']}")
print()

# Enable speech plugin
print("Enabling speech_recognition...")
success = registry.enable("speech_recognition")
print(f"  Enabled: {success}")
print()

# Check commands
commands = registry.get_all_commands()
print(f"Commands from enabled plugins:")
for plugin_name, cmds in commands.items():
    for cmd in cmds:
        print(f"  {plugin_name}: {cmd['name']} - {cmd['description']}")
print()

# Test find handler
print("Testing find_handler...")
test_messages = ["dengarkan suara", "buka folder", "apa kabar"]
for msg in test_messages:
    result = registry.find_handler(msg)
    if result:
        plugin, cmd = result
        print(f"  '{msg}' -> {plugin.name}:{cmd['name']}")
    else:
        print(f"  '{msg}' -> no handler")
print()

print("=" * 50)
print("Plugin System OK!")