"""
Saki Core — Lifecycle Manager
Start/stop/monitor semua komponen
"""

import subprocess
import time
import sys
import os
from pathlib import Path
import logging
import requests
import yaml

logger = logging.getLogger("saki.core")

class LifecycleManager:
    def __init__(self, config_path="saki_core/config.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
        self.processes = {}
        self.root = Path(__file__).parent.parent
    
    def start_all(self):
        """Start semua komponen sesuai urutan."""
        components = self.config.get("components", {})
        ordered = sorted(
            [(name, cfg) for name, cfg in components.items() if cfg.get("enabled")],
            key=lambda x: x[1].get("startup_order", 99)
        )
        
        for name, cfg in ordered:
            self.start_component(name, cfg)
            time.sleep(2)  # Jeda antar start
    
    def start_component(self, name, cfg):
        """Start satu komponen."""
        logger.info(f"Starting {name}...")
        
        if name == "ollama":
            # Ollama biasanya sudah jalan sebagai service
            if not self._check_health(cfg.get("health_check_url")):
                logger.warning("Ollama not running. Start manually: ollama serve")
            else:
                logger.info("Ollama already running")
                
        elif name == "streamlit":
            script = self.root / cfg.get("script", "src/server.py")
            port = cfg.get("port", 8501)
            cmd = [sys.executable, "-m", "streamlit", "run", str(script), "--server.port", str(port)]
            self.processes[name] = subprocess.Popen(cmd)
            logger.info(f"Streamlit started on port {port}")
            
        elif name == "chromadb":
            # ChromaDB jalan otomatis saat diakses
            logger.info("ChromaDB ready (auto-init)")
    
    def stop_all(self):
        """Stop semua komponen."""
        for name, process in self.processes.items():
            logger.info(f"Stopping {name}...")
            process.terminate()
            process.wait(timeout=10)
        logger.info("All components stopped")
    
    def _check_health(self, url):
        """Cek health endpoint."""
        if not url:
            return False
        try:
            r = requests.get(url, timeout=5)
            return r.status_code == 200
        except:
            return False
    
    def health_check(self):
        """Cek status semua komponen."""
        status = {}
        components = self.config.get("components", {})
        
        for name, cfg in components.items():
            if not cfg.get("enabled"):
                status[name] = "disabled"
                continue
            
            if name == "ollama":
                status[name] = "running" if self._check_health(cfg.get("health_check_url")) else "down"
            elif name == "streamlit":
                url = f"http://localhost:{cfg.get('port', 8501)}"
                status[name] = "running" if self._check_health(url) else "down"
            elif name == "chromadb":
                status[name] = "running"  # Always ready
        
        return status