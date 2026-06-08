#!/usr/bin/env python3
"""
Saki Hub Launcher
Shortcut untuk menjalankan Saki Hub Desktop
Pastikan Saki Core sudah berjalan (python run.py)
"""

import sys
from pathlib import Path

# Add project root ke path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from saki_hub.main import main

if __name__ == "__main__":
    print("=" * 50)
    print("🤖 Saki Hub Desktop v8.2")
    print("   Fase 2B: Desktop Control Panel")
    print("=" * 50)
    print()
    print("   ⚠️  Pastikan Saki Core sudah berjalan:")
    print("      python run.py")
    print()
    print("   Memulai Saki Hub...")
    print("   System tray akan muncul di taskbar")
    print()
    
    main()