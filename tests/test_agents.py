"""
Test untuk Fase 2A: Workspace Agents
"""

import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.router import AgentRouter
from src.agents.file_agent import FileAgent
from src.agents.note_agent import NoteAgent
from src.agents.task_agent import TaskAgent
from src.agents.project_agent import ProjectAgent

def test_router_routing():
    """Test AgentRouter routing"""
    router = AgentRouter()
    
    # Test file commands
    test_cases = [
        ("buka folder skripsi", "file"),
        ("cari file laporan", "file"),
        ("list folder documents", "file"),
        ("ringkas folder project", "file"),
        ("catat: ide baru untuk AI", "note"),
        ("cari catatan tentang meeting", "note"),
        ("list catatan minggu ini", "note"),
        ("hapus catatan #3", "note"),
        ("task: revisi proposal, deadline Jumat", "task"),
        ("list task", "task"),
        ("deadline minggu ini", "task"),
        ("tandai selesai task #1", "task"),
        ("update project skripsi: bab 3 done", "project"),
        ("progress project", "project"),
        ("list project", "project"),
        ("laporan project", "project"),
        ("apa kabar?", None),  # Bukan perintah agent
        ("ceritakan tentang AI", None),  # Chat biasa
    ]
    
    for message, expected_agent in test_cases:
        agent, msg = router.route(message)
        
        if expected_agent is None:
            assert agent is None, f"'{message}' seharusnya bukan perintah agent, tapi di-route ke {agent}"
        else:
            assert agent is not None, f"'{message}' seharusnya di-route ke {expected_agent}"
            assert agent.name.lower().startswith(expected_agent), f"'{message}' di-route ke {agent.name}, seharusnya {expected_agent}"
    
    print("✅ Router routing tests passed!")

def test_file_agent():
    """Test FileAgent"""
    agent = FileAgent()
    
    # Test path resolution
    assert agent.fs.resolve_path("desktop") is not None
    
    print("✅ FileAgent tests passed!")

def test_note_agent():
    """Test NoteAgent"""
    agent = NoteAgent()
    
    # Test create note
    result = agent._create_note("Test note from unit test")
    assert "tersimpan" in result
    
    # Test list notes
    result = agent._list_notes()
    assert "Catatan" in result
    
    # Test search notes
    result = agent._search_notes("test")
    assert "Ditemukan" in result or "Tidak ada" in result
    
    print("✅ NoteAgent tests passed!")

def test_task_agent():
    """Test TaskAgent"""
    agent = TaskAgent()
    
    # Test add task
    result = agent._add_task("task: test task, deadline besok")
    assert "ditambahkan" in result
    
    # Test list tasks
    result = agent._list_tasks()
    assert "Task" in result or "tidak ada" in result.lower()
    
    # Test deadlines
    result = agent._check_deadlines("minggu ini")
    assert "deadline" in result.lower() or "tidak ada" in result.lower()
    
    print("✅ TaskAgent tests passed!")

def test_project_agent():
    """Test ProjectAgent"""
    agent = ProjectAgent()
    
    # Test list projects
    result = agent._list_projects()
    assert "Project" in result or "project" in result.lower()
    
    # Test update project
    result = agent._update_project("update project Saki AI: testing agent")
    assert "diupdate" in result or "dibuat" in result
    
    # Test check progress
    result = agent._check_progress("progress")
    assert "Progress" in result
    
    print("✅ ProjectAgent tests passed!")

if __name__ == "__main__":
    print("Testing Fase 2A: Workspace Agents")
    print("=" * 40)
    
    test_router_routing()
    test_file_agent()
    test_note_agent()
    test_task_agent()
    test_project_agent()
    
    print("=" * 40)
    print("🎉 All tests passed!")