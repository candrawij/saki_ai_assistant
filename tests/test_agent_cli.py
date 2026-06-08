# test_agent_cli.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.router import AgentRouter

router = AgentRouter()

while True:
    try:
        pesan = input("\n👤 Kamu: ")
        if pesan.lower() in ["exit", "quit", "keluar"]:
            break
        
        agent, msg = router.route(pesan)
        
        if agent == "special":
            print(f"🤖 Special: {router.execute_special(pesan)}")
        elif agent:
            print(f"🤖 {agent.name}: {agent.execute(pesan)}")
        else:
            print("ℹ️ Bukan perintah agent (chat biasa)")
    
    except KeyboardInterrupt:
        break

print("\nBye!")