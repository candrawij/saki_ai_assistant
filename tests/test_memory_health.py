"""Test Memory Health System"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.memory_health import get_memory_health


def test_stale_facts():
    """Test stale facts detection."""
    mh = get_memory_health()
    stale = mh.find_stale_facts(days=0)  # Semua fakta
    print(f"✅ Stale facts: {len(stale)} found (days=0)")

def test_duplicates():
    """Test duplicate detection."""
    mh = get_memory_health()
    dupes = mh.find_duplicates()
    print(f"✅ Duplicates: {len(dupes)} found")

def test_similarity():
    """Test similarity function."""
    mh = get_memory_health()
    
    # Identical
    assert mh._similarity("saya suka kopi", "saya suka kopi") == 1.0
    
    # Similar
    sim = mh._similarity("saya suka kopi pahit", "saya suka kopi manis")
    assert sim > 0.5
    
    # Different
    sim = mh._similarity("saya suka kopi", "machine learning keren")
    assert sim < 0.3
    
    print("✅ Similarity function OK")

def test_memory_stats():
    """Test memory statistics."""
    mh = get_memory_health()
    stats = mh.get_memory_stats()
    
    assert "totals" in stats
    assert "categories" in stats
    assert "health" in stats
    assert "growth" in stats
    
    print(f"✅ Stats: {stats['totals']['facts']} facts, {stats['totals']['reflections']} reflections")

def test_health_report():
    """Test health report generation."""
    mh = get_memory_health()
    report = mh.get_health_report()
    
    assert "MEMORY HEALTH REPORT" in report
    assert len(report) > 100
    
    print("✅ Health report generated")
    print()
    print(report[:500])


if __name__ == "__main__":
    print("=" * 50)
    print("Testing Memory Health System")
    print("=" * 50)
    print()
    
    test_similarity()
    test_stale_facts()
    test_duplicates()
    test_memory_stats()
    test_health_report()
    
    print()
    print("=" * 50)
    print("🎉 All tests passed!")