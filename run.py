"""
Saki — Entry Point
Jalankan: python run.py
"""

import subprocess
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def main():
    print("=" * 50)
    print("🤖 Saki v8.1 — Starting...")
    print("=" * 50)
    
    # Jalankan Streamlit
    server_script = Path("src/server.py")
    if server_script.exists():
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", str(server_script),
            "--server.address", "0.0.0.0"
        ])
    else:
        print("❌ src/server.py not found!")

if __name__ == "__main__":
    main()