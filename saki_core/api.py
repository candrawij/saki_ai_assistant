"""
Saki Core — API Layer
FastAPI endpoints untuk monitoring & kontrol
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import yaml
from pathlib import Path

app = FastAPI(title="Saki Core API", version="1.0")

# Global references (di-set oleh service.py)
lifecycle_manager = None
system_monitor = None

@app.get("/api/status")
def get_status():
    """Status semua komponen."""
    if lifecycle_manager:
        return lifecycle_manager.health_check()
    return {"error": "Lifecycle manager not initialized"}

@app.get("/api/monitor")
def get_monitor():
    """Statistik sistem saat ini."""
    if system_monitor:
        return system_monitor.get_current_stats()
    return {"error": "Monitor not initialized"}

@app.get("/api/monitor/history")
def get_monitor_history(minutes: int = 60):
    """Data historis monitoring."""
    if system_monitor:
        return system_monitor.get_history(minutes)
    return []

@app.post("/api/start/{component}")
def start_component(component: str):
    """Start satu komponen."""
    if lifecycle_manager:
        cfg_path = "saki_core/config.yaml"
        with open(cfg_path) as f:
            config = yaml.safe_load(f)
        cfg = config.get("components", {}).get(component)
        if cfg:
            lifecycle_manager.start_component(component, cfg)
            return {"status": "started", "component": component}
    return {"error": "Component not found"}

@app.get("/api/scheduler")
def get_scheduler_status():
    """Status scheduler jobs."""
    return {"status": "running"}