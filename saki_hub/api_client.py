"""
API Client — Komunikasi dengan Saki Core API
"""

import requests
import logging

logger = logging.getLogger("saki.hub")

class SakiAPIClient:
    def __init__(self, base_url: str = "http://localhost:8502"):
        self.base_url = base_url
        self.connected = False
    
    def check_connection(self) -> bool:
        """Cek apakah API tersedia."""
        try:
            r = requests.get(f"{self.base_url}/health", timeout=3)
            self.connected = r.status_code == 200
            return self.connected
        except:
            self.connected = False
            return False
    
    def get_status(self) -> dict:
        """Get status semua komponen."""
        try:
            r = requests.get(f"{self.base_url}/status", timeout=3)
            return r.json()
        except:
            return {"error": "API not available"}
    
    def get_monitor(self) -> dict:
        """Get system monitoring data (current metrics)."""
        try:
            r = requests.get(f"{self.base_url}/metrics/current", timeout=3)
            return r.json()
        except:
            return {
                "cpu": {"percent": 0},
                "ram": {"percent": 0, "used_gb": 0, "total_gb": 16},
                "disk": {"percent": 0, "free_gb": 0},
            }
    
    def get_monitor_history(self, minutes: int = 60) -> list:
        """Get monitoring history."""
        try:
            r = requests.get(
                f"{self.base_url}/metrics/history",
                params={"minutes": minutes},
                timeout=3
            )
            return r.json()
        except:
            return []
    
    def start_component(self, name: str) -> dict:
        """Start a component."""
        try:
            r = requests.post(
                f"{self.base_url}/components/start",
                json={"command": "start", "component": name},
                timeout=10
            )
            return r.json()
        except:
            return {"error": "Failed"}
    
    def stop_component(self, name: str) -> dict:
        """Stop a component."""
        try:
            r = requests.post(
                f"{self.base_url}/components/stop",
                json={"command": "stop", "component": name},
                timeout=10
            )
            return r.json()
        except:
            return {"error": "Failed"}
    
    def restart_component(self, name: str) -> dict:
        """Restart a component."""
        try:
            r = requests.post(
                f"{self.base_url}/components/restart",
                json={"command": "restart", "component": name},
                timeout=15
            )
            return r.json()
        except:
            return {"error": "Failed"}
    
    def get_scheduler(self) -> list:
        """Get scheduler jobs."""
        try:
            r = requests.get(f"{self.base_url}/scheduler/jobs", timeout=3)
            return r.json()
        except:
            return []
    
    def run_job(self, job_id: str) -> dict:
        """Run a scheduled job now."""
        try:
            r = requests.post(
                f"{self.base_url}/scheduler/run/{job_id}",
                timeout=30
            )
            return r.json()
        except:
            return {"error": "Failed"}
    
    def get_logs(self, lines: int = 100) -> dict:
        """Get recent logs."""
        try:
            r = requests.get(
                f"{self.base_url}/logs",
                params={"lines": lines},
                timeout=3
            )
            return r.json()
        except:
            return {"logs": [], "error": "Failed to fetch logs"}
    
    def create_backup(self) -> dict:
        """Create manual backup."""
        try:
            r = requests.post(f"{self.base_url}/backup/create", timeout=30)
            return r.json()
        except:
            return {"error": "Failed"}
    
    def get_config(self) -> dict:
        """Get current configuration."""
        try:
            r = requests.get(f"{self.base_url}/config", timeout=3)
            return r.json()
        except:
            return {}