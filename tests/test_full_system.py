"""Test Full System Integration"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 60)
print("FULL SYSTEM TEST - Fase 4")
print("=" * 60)
print()

# 1. Plugin System
print("1. Plugin System...")
from plugins.loader import load_all_plugins, get_plugin_manager
pm = load_all_plugins()
stats = pm.get_stats()
print(f"   ✅ {stats['total']} plugins loaded")
for p in stats['plugins']:
    print(f"      {p['icon']} {p['name']} - {p['status']}")
print()

# 2. Agent System
print("2. Agent System...")
from src.agents.router import AgentRouter
router = AgentRouter()
print(f"   ✅ Router ready")
print(f"   Agents: {len(router.get_agent_info())}")
print()

# 3. Model Router
print("3. Model Router...")
from src.model_router import ModelRouter
mr = ModelRouter()
models = mr.get_available_models()
print(f"   ✅ {len(models)} models available")
for m in models:
    print(f"      {m}")
print()

# 4. Permission System
print("4. Permission System...")
from src.permissions import PermissionManager
pm_perm = PermissionManager()
print(f"   ✅ Permission Manager ready")
print(f"   Delegation: {pm_perm.is_delegation_enabled()}")
print()

# 5. Memory Health
print("5. Memory Health...")
from src.memory_health import get_memory_health
mh = get_memory_health()
stats_mh = mh.get_memory_stats()
print(f"   ✅ {stats_mh['totals']['facts']} facts, {stats_mh['totals']['reflections']} reflections")
print()

# 6. Database
print("6. Database...")
from src.database import init_db, lihat_semua_fakta
init_db()
facts = lihat_semua_fakta()
print(f"   ✅ Database ready, {len(facts)} facts")
print()

print("=" * 60)
print("🎉 ALL SYSTEMS READY!")
print("=" * 60)