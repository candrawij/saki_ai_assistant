"""
Saki Core — System Monitor
CPU, RAM, Disk monitoring dengan psutil
"""

import psutil
import time
import threading
import logging

logger = logging.getLogger("saki.core.monitor")

class SystemMonitor:
    def __init__(self, collect_interval=10):
        self.interval = collect_interval
        self.history = []
        self.running = False
        self.thread = None
    
    def start(self):
        """Start monitoring di background thread."""
        self.running = True
        self.thread = threading.Thread(target=self._collect_loop, daemon=True)
        self.thread.start()
        logger.info(f"Monitor started (interval: {self.interval}s)")
    
    def stop(self):
        """Stop monitoring."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Monitor stopped")
    
    def _collect_loop(self):
        """Loop pengumpulan data."""
        while self.running:
            stats = self.get_current_stats()
            self.history.append(stats)
            if len(self.history) > 1440:  # 24 jam (interval 60s)
                self.history.pop(0)
            time.sleep(self.interval)
    
    def get_current_stats(self):
        """Ambil statistik saat ini."""
        return {
            "timestamp": time.time(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "ram_percent": psutil.virtual_memory().percent,
            "ram_used_gb": round(psutil.virtual_memory().used / (1024**3), 1),
            "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 1),
            "disk_percent": psutil.disk_usage('/').percent,
            "disk_free_gb": round(psutil.disk_usage('/').free / (1024**3), 1),
            "uptime_hours": round((time.time() - psutil.boot_time()) / 3600, 1)
        }
    
    def get_history(self, minutes=60):
        """Ambil data historis."""
        cutoff = time.time() - (minutes * 60)
        return [h for h in self.history if h["timestamp"] >= cutoff]