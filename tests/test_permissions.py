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
    import random
    et = EvidenceTracker()

    # Pakai ID random biar gak conflict dengan data lama
    test_id = random.randint(10000, 99999)
    
    # Record evidence
    evidence = et.record(
        fact_id=test_id,
        observer="kamu",
        perspective="internal",
        source_type="manual",
        confidence=0.9,
        shareable=False,
        agent_usable=True,
    )
    
    assert evidence["fact_id"] == test_id
    assert evidence["observer"] == "kamu"
    assert evidence["confidence"] == 0.9
    assert evidence["validation_count"] == 1
    
    # Get evidence
    retrieved = et.get_evidence(test_id)
    assert retrieved is not None
    assert retrieved["observer"] == "kamu"
    
    # Validate
    current_count = retrieved["validation_count"]
    et.validate(test_id, new_confidence=0.95)
    updated = et.get_evidence(test_id)
    assert updated["confidence"] == 0.95
    assert updated["validation_count"] == current_count + 1
    
    print("✅ Evidence tracking OK")


def test_shareable_facts():
    """Test shareable facts filtering."""
    import random
    et = EvidenceTracker()

    id_a = random.randint(10000, 99999)
    id_b = random.randint(10000, 99999)
    
    # Record shareable fact
    et.record(fact_id=id_a, observer="kamu", shareable=True)
    
    # Record private fact
    et.record(fact_id=id_b, observer="kamu", shareable=False)
    
    shareable = et.get_shareable_facts()
    assert id_a in shareable
    assert id_b not in shareable
    
    print("✅ Shareable facts OK")


def test_delegation():
    """Test delegation mode."""
    pm = PermissionManager()
    
    # Default: delegasi disabled
    pm.enable_delegation(False)
    assert pm.is_delegation_enabled() == False
    assert pm.can_delegate_action("chat") == False
    
    # Enable delegasi
    pm.enable_delegation(True)
    assert pm.is_delegation_enabled() == True
    assert pm.can_delegate_action("chat") == True
    assert pm.can_delegate_action("hapus") == False  # Tidak di allowed_actions
    
    # Cek signature
    assert "[Dibalas oleh Saki]" in pm.get_delegation_signature()
    
    pm.enable_delegation(False)

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