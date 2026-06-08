"""
Saki — Entry Point
Jalankan Saki Core (backend)
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
    print("🤖 Saki Core v8.2 — Starting...")
    print("=" * 50)
    
    # Start lifecycle manager
    print("[1/4] Starting Lifecycle Manager...")
    lm = LifecycleManager()
    lm.start_all()
    
    # Start scheduler
    print("[2/4] Starting Scheduler...")
    scheduler = SakiScheduler()
    scheduler.start()
    
    # Start monitor
    print("[3/4] Starting System Monitor...")
    monitor = SystemMonitor(collect_interval=10)
    monitor.start()
    
    # Set global references untuk API
    import saki_core.api as api_module
    api_module.lifecycle_manager = lm
    api_module.system_monitor = monitor
    
    # Start API di background thread
    print("[4/4] Starting API Server...")
    def run_api():
        uvicorn.run(api_module.app, host="127.0.0.1", port=8502, log_level="info")
    
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()
    
    print()
    print("✅ All systems running!")
    print(f"   Chat UI:    http://localhost:8501")
    print(f"   Hub API:    http://localhost:8502")
    print(f"   API Docs:   http://localhost:8502/docs")
    print()
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