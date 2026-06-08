"""
Test untuk Fase 2A: Workspace Agents
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.router import AgentRouter
from src.agents.file_agent import FileAgent
from src.agents.note_agent import NoteAgent
from src.agents.task_agent import TaskAgent
from src.agents.project_agent import ProjectAgent


def test_router_routing():
    """Test AgentRouter routing."""
    router = AgentRouter()
    
    test_cases = [
        ("buka folder data", "file"),
        ("cari file laporan", "file"),
        ("list folder documents", "file"),
        ("ringkas folder data", "file"),
        ("catat: ide baru untuk AI", "note"),
        ("cari catatan meeting", "note"),
        ("list catatan", "note"),
        ("hapus catatan #3", "note"),
        ("task: revisi proposal, deadline Jumat", "task"),
        ("list task", "task"),
        ("deadline minggu ini", "task"),
        ("tandai task #1 selesai", "task"),
        ("update project skripsi: bab 3 done", "project"),
        ("progress project", "project"),
        ("list project", "project"),
        ("laporan project", "project"),
        ("apa kabar?", None),
        ("ceritakan tentang AI", None),
    ]
    
    for message, expected_agent in test_cases:
        agent, agent_name = router.route(message)
        
        if expected_agent is None:
            assert agent is None, f"'{message}' seharusnya bukan perintah agent, tapi di-route ke {agent}"
        else:
            assert agent is not None, f"'{message}' seharusnya di-route ke agent"
            assert agent.name.lower() == expected_agent or expected_agent in agent.name.lower(), \
                f"'{message}' di-route ke '{agent.name}', seharusnya '{expected_agent}'"
    
    print("✅ Router routing tests passed!")


def test_file_agent():
    """Test FileAgent."""
    agent = FileAgent()
    
    # Test resolve_path
    from src.agents.skills import filesystem
    assert filesystem.resolve_path("data") is not None
    assert filesystem.resolve_path("desktop") is not None
    
    # Test can_handle
    assert agent.can_handle("buka folder data") == True
    assert agent.can_handle("list task") == False  # Bukan file agent
    
    print("✅ FileAgent tests passed!")


def test_note_agent():
    """Test NoteAgent."""
    agent = NoteAgent()
    
    # Test create note
    result = agent.execute("catat: test note from unit test")
    assert "tersimpan" in result.lower()
    
    # Test list notes
    result = agent.execute("list catatan")
    assert "Catatan" in result or "catatan" in result.lower()
    
    print("✅ NoteAgent tests passed!")


def test_task_agent():
    """Test TaskAgent."""
    agent = TaskAgent()
    
    # Test add task
    result = agent.execute("task: test task, deadline besok")
    assert "ditambahkan" in result.lower()
    
    # Test list tasks
    result = agent.execute("list task")
    assert "tugas" in result.lower() or "task" in result.lower()
    
    print("✅ TaskAgent tests passed!")


def test_project_agent():
    """Test ProjectAgent."""
    agent = ProjectAgent()
    
    # Test list projects (auto-create defaults)
    result = agent.execute("list project")
    assert "project" in result.lower() or "proyek" in result.lower()
    
    print("✅ ProjectAgent tests passed!")


if __name__ == "__main__":
    print("=" * 50)
    print("Testing Fase 2A: Workspace Agents")
    print("=" * 50)
    print()
    
    try:
        test_router_routing()
        test_file_agent()
        test_note_agent()
        test_task_agent()
        test_project_agent()
        
        print()
        print("=" * 50)
        print("🎉 All tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
    except Exception as e:
        print(f"\n❌ Error: {e}")