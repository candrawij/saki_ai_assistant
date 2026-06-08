"""
API Client — Komunikasi dengan Saki Core API
"""

import requests
import logging

logger = logging.getLogger("saki.hub")

class SakiAPIClient:
    def __init__(self, base_url: str = "http://localhost:8503"):
        self.base_url = base_url
        self.connected = False
    
    def check_connection(self) -> bool:
        """Cek apakah API tersedia."""
        try:
            r = requests.get(f"{self.base_url}/api/status", timeout=3)
            self.connected = r.status_code == 200
            return self.connected
        except:
            self.connected = False
            return False
    
    def get_status(self) -> dict:
        """Get status semua komponen."""
        try:
            r = requests.get(f"{self.base_url}/api/status", timeout=3)
            return r.json()
        except:
            return {"error": "API not available"}
    
    def get_monitor(self) -> dict:
        """Get system monitoring data."""
        try:
            r = requests.get(f"{self.base_url}/api/monitor", timeout=3)
            return r.json()
        except:
            return {
                "cpu_percent": 0,
                "ram_percent": 0,
                "ram_used_gb": 0,
                "ram_total_gb": 16,
                "disk_percent": 0,
                "disk_free_gb": 0,
                "uptime_hours": 0,
            }
    
    def get_monitor_history(self, minutes: int = 60) -> list:
        """Get monitoring history."""
        try:
            r = requests.get(f"{self.base_url}/api/monitor/history?minutes={minutes}", timeout=3)
            return r.json()
        except:
            return []
    
    def start_component(self, name: str) -> dict:
        """Start a component."""
        try:
            r = requests.post(f"{self.base_url}/api/start/{name}", timeout=5)
            return r.json()
        except:
            return {"error": "Failed"}
    
    def stop_component(self, name: str) -> dict:
        """Stop a component."""
        try:
            r = requests.post(f"{self.base_url}/api/stop/{name}", timeout=5)
            return r.json()
        except:
            return {"error": "Failed"}
    
    def get_scheduler(self) -> dict:
        """Get scheduler status."""
        try:
            r = requests.get(f"{self.base_url}/api/scheduler", timeout=3)
            return r.json()
        except:
            return {"error": "API not available"}