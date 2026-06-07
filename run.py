"""
Saki — Entry Point
Jalankan semua komponen
"""

import sys
import threading
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from saki_core.lifecycle import LifecycleManager
from saki_core.scheduler import SakiScheduler
from saki_core.monitor import SystemMonitor
import time
import uvicorn

def main():
    print("=" * 50)
    print("🤖 Saki Core v1.0 — Starting...")
    print("=" * 50)
    
    # Start lifecycle manager
    lm = LifecycleManager()
    lm.start_all()
    
    # Start scheduler
    scheduler = SakiScheduler()
    scheduler.start()
    
    # Start monitor
    monitor = SystemMonitor(collect_interval=10)
    monitor.start()
    
    # Set global references untuk API
    import saki_core.api as api_module
    api_module.lifecycle_manager = lm
    api_module.system_monitor = monitor
    
    # Start API di background thread
    def run_api():
        uvicorn.run(api_module.app, host="127.0.0.1", port=8503, log_level="info")
    
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()
    
    print("✅ All systems running!")
    print("   Chat: http://localhost:8501")
    print("   Monitor API: http://localhost:8503/api/status")
    print("   Press Ctrl+C to stop")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        monitor.stop()
        scheduler.stop()
        lm.stop_all()
        print("✅ All systems stopped")

if __name__ == "__main__":
    main()