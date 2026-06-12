"""
Test Permission System + Evidence Layer
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.permissions import PermissionManager, PermissionLevel, ActionType
from src.evidence import EvidenceTracker


def test_permission_levels():
    """Test basic permission levels."""
    pm = PermissionManager(owner="kamu")
    
    # Owner selalu boleh
    assert pm.can_access_fact(1, "kamu") == True
    
    # User tidak dikenal — tidak boleh
    assert pm.can_access_fact(1, "orang_asing") == False
    
    print("✅ Permission levels OK")


def test_agent_policy():
    """Test agent action policy."""
    pm = PermissionManager()
    
    # Read-only — auto (tanpa konfirmasi)
    assert pm.needs_confirmation(ActionType.READ_ONLY) == False
    
    # Dangerous — butuh konfirmasi
    assert pm.needs_confirmation(ActionType.DANGEROUS) == True
    
    # Ubah policy
    pm.set_action_policy(ActionType.DANGEROUS, "auto")
    assert pm.needs_confirmation(ActionType.DANGEROUS) == False
    
    # Kembalikan
    pm.set_action_policy(ActionType.DANGEROUS, "confirm")
    
    print("✅ Agent policy OK")


def test_action_mapping():
    """Test action → ActionType mapping."""
    pm = PermissionManager()
    
    assert pm.get_action_level("cari") == ActionType.READ_ONLY
    assert pm.get_action_level("catat") == ActionType.SAFE_WRITE
    assert pm.get_action_level("buka") == ActionType.SYSTEM_ACCESS
    assert pm.get_action_level("cmd") == ActionType.DANGEROUS
    
    print("✅ Action mapping OK")


def test_evidence_tracking():
    """Test evidence recording."""
    et = EvidenceTracker()
    
    # Record evidence
    evidence = et.record(
        fact_id=1,
        observer="kamu",
        perspective="internal",
        source_type="manual",
        confidence=0.9,
        shareable=False,
        agent_usable=True,
    )
    
    assert evidence["fact_id"] == 1
    assert evidence["observer"] == "kamu"
    assert evidence["confidence"] == 0.9
    
    # Get evidence
    retrieved = et.get_evidence(1)
    assert retrieved is not None
    assert retrieved["observer"] == "kamu"
    
    # Validate
    et.validate(1, new_confidence=0.95)
    updated = et.get_evidence(1)
    assert updated["confidence"] == 0.95
    assert updated["validation_count"] == 2
    
    print("✅ Evidence tracking OK")


def test_shareable_facts():
    """Test shareable facts filtering."""
    et = EvidenceTracker()
    
    # Record shareable fact
    et.record(fact_id=10, observer="kamu", shareable=True)
    
    # Record private fact
    et.record(fact_id=11, observer="kamu", shareable=False)
    
    shareable = et.get_shareable_facts()
    assert 10 in shareable
    assert 11 not in shareable
    
    print("✅ Shareable facts OK")


def test_delegation():
    """Test delegation mode."""
    pm = PermissionManager()
    
    # Default: delegasi disabled
    assert pm.is_delegation_enabled() == False
    assert pm.can_delegate_action("chat") == False
    
    # Enable delegasi
    pm.enable_delegation(True)
    assert pm.is_delegation_enabled() == True
    assert pm.can_delegate_action("chat") == True
    assert pm.can_delegate_action("hapus") == False  # Tidak di allowed_actions
    
    # Cek signature
    assert "[Dibalas oleh Saki]" in pm.get_delegation_signature()
    
    print("✅ Delegation OK")


def test_whitelist():
    """Test whitelist management."""
    pm = PermissionManager()
    
    pm.add_whitelist_user("Orang A")
    assert "Orang A" in pm.policy["whitelist"]["users"]
    
    pm.remove_whitelist_user("Orang A")
    assert "Orang A" not in pm.policy["whitelist"]["users"]
    
    pm.add_observer("Orang B")
    assert "Orang B" in pm.policy["whitelist"]["observers"]
    
    print("✅ Whitelist OK")


def test_stats():
    """Test statistics."""
    et = EvidenceTracker()
    pm = PermissionManager()
    
    evidence_stats = et.get_stats()
    assert "total_facts" in evidence_stats
    assert "stale_facts" in evidence_stats
    
    perm_stats = pm.get_stats()
    assert "delegation_enabled" in perm_stats
    assert "whitelist_users" in perm_stats
    
    print("✅ Stats OK")


if __name__ == "__main__":
    print("=" * 50)
    print("Testing Permission System + Evidence Layer")
    print("=" * 50)
    print()
    
    test_permission_levels()
    test_agent_policy()
    test_action_mapping()
    test_evidence_tracking()
    test_shareable_facts()
    test_delegation()
    test_whitelist()
    test_stats()
    
    print()
    print("=" * 50)
    print("🎉 All tests passed!")