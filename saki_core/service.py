"""
Saki Core — Windows Service
Jalankan Saki sebagai Windows Service (auto-start saat boot)
"""

import sys
import os
import threading
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

ROOT = Path(__file__).parent.parent
os.chdir(str(ROOT))
sys.path.insert(0, str(ROOT))

import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import time
import logging
import uvicorn

from saki_core.lifecycle import LifecycleManager
from saki_core.scheduler import SakiScheduler
from saki_core.monitor import SystemMonitor

logger = logging.getLogger("saki.service")


class SakiService(win32serviceutil.ServiceFramework):
    _svc_name_ = "SakiCore"
    _svc_display_name_ = "Saki Core Service"
    _svc_description_ = "Saki Personal AI Ecosystem — Core Service"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.lm = None
        self.scheduler = None
        self.monitor = None

    def SvcStop(self):
        """Stop service."""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        
        if self.monitor:
            self.monitor.stop()
        if self.scheduler:
            self.scheduler.stop()
        if self.lm:
            self.lm.stop_all()
        
        logger.info("Saki Core Service stopped")

    def SvcDoRun(self):
        """Main service loop."""
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        
        self.main()

    def main(self):
        logger.info("=" * 50)
        logger.info("Saki Core Service starting...")
        logger.info("=" * 50)
        
        # Start lifecycle manager
        self.lm = LifecycleManager()
        self.lm.start_all()
        
        # Start scheduler
        self.scheduler = SakiScheduler()
        self.scheduler.start()
        
        # Start monitor
        self.monitor = SystemMonitor(collect_interval=10)
        self.monitor.start()
        
        # Set global references untuk API
        import saki_core.api as api_module
        api_module.lifecycle_manager = self.lm
        api_module.system_monitor = self.monitor
        
        # Start API
        def run_api():
            uvicorn.run(api_module.app, host="127.0.0.1", port=8503, log_level="warning")
        
        api_thread = threading.Thread(target=run_api, daemon=True)
        api_thread.start()
        
        logger.info("All systems running")
        
        # Tunggu stop signal
        while True:
            result = win32event.WaitForSingleObject(self.stop_event, 1000)
            if result == win32event.WAIT_OBJECT_0:
                break


if __name__ == "__main__":
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(SakiService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(SakiService)