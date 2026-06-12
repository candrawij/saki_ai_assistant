"""
Permission System — Kontrol akses untuk agent dan multi-user
"""

from enum import IntEnum
from typing import Optional, Dict, List
from datetime import datetime
import json
from pathlib import Path


class PermissionLevel(IntEnum):
    """Level izin untuk akses data dan tindakan."""
    PUBLIC = 0       # Bisa diakses siapa aja
    SHARED = 1       # Bisa diakses orang tertentu (whitelist)
    AGENT_USE = 2    # Bisa dipakai agent (delegasi)
    PRIVATE = 3      # Hanya pemilik
    RESTRICTED = 4   # Bahkan pemilik butuh konfirmasi eksplisit


class ActionType(IntEnum):
    """Tipe tindakan yang bisa dilakukan agent."""
    READ_ONLY = 0       # cari, list, lihat
    SAFE_WRITE = 1      # catat, task (tidak merusak)
    SYSTEM_ACCESS = 2   # buka file, screenshot
    DANGEROUS = 3       # cmd, delete, kirim pesan


class PermissionManager:
    """
    Mengelola izin untuk:
    - Siapa bisa akses fakta apa
    - Agent boleh melakukan apa tanpa konfirmasi
    - Delegasi: kapan Saki boleh jadi "kamu"
    """
    
    def __init__(self, owner: str = "user"):
        self.owner = owner
        self.policy_file = Path("data/permissions.json")
        self._load()
        self._init_defaults()
    
    def _load(self):
        """Load policy dari file."""
        if self.policy_file.exists():
            with open(self.policy_file, "r", encoding="utf-8") as f:
                self.policy = json.load(f)
        else:
            self.policy = {}
    
    def _save(self):
        """Simpan policy."""
        self.policy_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.policy_file, "w", encoding="utf-8") as f:
            json.dump(self.policy, f, ensure_ascii=False, indent=2)
    
    def _init_defaults(self):
        """Set default policy kalau belum ada."""
        if "agent_policy" not in self.policy:
            self.policy["agent_policy"] = {
                ActionType.READ_ONLY.name: "auto",       # Tanpa konfirmasi
                ActionType.SAFE_WRITE.name: "auto",       # Tanpa konfirmasi
                ActionType.SYSTEM_ACCESS.name: "confirm", # Butuh konfirmasi
                ActionType.DANGEROUS.name: "confirm",     # Butuh konfirmasi
            }
        
        if "delegation" not in self.policy:
            self.policy["delegation"] = {
                "enabled": False,
                "allowed_actions": ["chat", "task_query", "project_update"],
                "signature": "[Dibalas oleh Saki]",
                "notify_owner": True,
            }
        
        if "whitelist" not in self.policy:
            self.policy["whitelist"] = {
                "users": [],  # Daftar user yang boleh akses SHARED
                "observers": [],  # Daftar orang yang fact-nya diterima
            }
        
        if "default_permissions" not in self.policy:
            self.policy["default_permissions"] = {
                "new_fact": PermissionLevel.AGENT_USE.name,
                "new_document": PermissionLevel.PRIVATE.name,
                "new_reflection": PermissionLevel.SHARED.name,
            }
        
        self._save()
    
    # ========== FACT PERMISSIONS ==========
    
    def can_access_fact(self, fact_id: int, user: str, 
                        evidence_tracker=None) -> bool:
        """
        Cek apakah user boleh akses fakta tertentu.
        
        Args:
            fact_id: ID fakta
            user: Siapa yang minta akses
            evidence_tracker: EvidenceTracker instance (optional)
        """
        # Owner selalu boleh
        if user == self.owner:
            return True
        
        # Cek evidence
        if evidence_tracker:
            evidence = evidence_tracker.get_evidence(fact_id)
            if evidence:
                level = evidence.get("shareable", False)
                if level:
                    # Cek whitelist
                    return user in self.policy["whitelist"]["users"]
        
        return False
    
    def can_agent_use_fact(self, fact_id: int, 
                           evidence_tracker=None) -> bool:
        """Cek apakah agent boleh pakai fakta ini untuk delegasi."""
        if not self.policy["delegation"]["enabled"]:
            return False
        
        if evidence_tracker:
            evidence = evidence_tracker.get_evidence(fact_id)
            if evidence:
                return evidence.get("agent_usable", False)
        
        return True  # Default: boleh
    
    # ========== AGENT ACTIONS ==========
    
    def needs_confirmation(self, action_type: ActionType) -> bool:
        """
        Cek apakah tindakan ini butuh konfirmasi user.
        
        Returns:
            True = harus konfirmasi dulu
            False = boleh langsung jalan
        """
        policy = self.policy["agent_policy"].get(action_type.name, "confirm")
        return policy == "confirm"
    
    def set_action_policy(self, action_type: ActionType, policy: str):
        """
        Set policy untuk tipe tindakan.
        
        Args:
            action_type: Tipe tindakan
            policy: "auto" atau "confirm"
        """
        valid = ["auto", "confirm"]
        if policy not in valid:
            raise ValueError(f"Policy harus salah satu dari: {valid}")
        
        self.policy["agent_policy"][action_type.name] = policy
        self._save()
    
    def get_action_level(self, action: str) -> ActionType:
        """Tentukan level tindakan berdasarkan nama action."""
        mapping = {
            "cari": ActionType.READ_ONLY,
            "list": ActionType.READ_ONLY,
            "progress": ActionType.READ_ONLY,
            "info": ActionType.READ_ONLY,
            "catat": ActionType.SAFE_WRITE,
            "note": ActionType.SAFE_WRITE,
            "task": ActionType.SAFE_WRITE,
            "tambah_task": ActionType.SAFE_WRITE,
            "update_project": ActionType.SAFE_WRITE,
            "buka": ActionType.SYSTEM_ACCESS,
            "buka_folder": ActionType.SYSTEM_ACCESS,
            "buka_file": ActionType.SYSTEM_ACCESS,
            "screenshot": ActionType.SYSTEM_ACCESS,
            "cmd": ActionType.DANGEROUS,
            "hapus": ActionType.DANGEROUS,
            "delete": ActionType.DANGEROUS,
        }
        return mapping.get(action, ActionType.READ_ONLY)
    
    # ========== DELEGATION ==========
    
    def enable_delegation(self, enabled: bool = True):
        """Enable/disable mode delegasi (Saki jadi kamu)."""
        self.policy["delegation"]["enabled"] = enabled
        self._save()
    
    def is_delegation_enabled(self) -> bool:
        """Cek apakah mode delegasi aktif."""
        return self.policy["delegation"]["enabled"]
    
    def can_delegate_action(self, action: str) -> bool:
        """Cek apakah tindakan ini boleh di-delegasi."""
        if not self.is_delegation_enabled():
            return False
        return action in self.policy["delegation"]["allowed_actions"]
    
    def get_delegation_signature(self) -> str:
        """Dapatkan tanda tangan delegasi."""
        return self.policy["delegation"]["signature"]
    
    # ========== WHITELIST ==========
    
    def add_whitelist_user(self, user: str):
        """Tambah user ke whitelist."""
        if user not in self.policy["whitelist"]["users"]:
            self.policy["whitelist"]["users"].append(user)
            self._save()
    
    def remove_whitelist_user(self, user: str):
        """Hapus user dari whitelist."""
        if user in self.policy["whitelist"]["users"]:
            self.policy["whitelist"]["users"].remove(user)
            self._save()
    
    def add_observer(self, observer: str):
        """Tambah observer yang fact-nya diterima."""
        if observer not in self.policy["whitelist"]["observers"]:
            self.policy["whitelist"]["observers"].append(observer)
            self._save()
    
    # ========== DEFAULT PERMISSIONS ==========
    
    def get_default_permission(self, item_type: str) -> str:
        """Dapatkan default permission untuk item baru."""
        return self.policy["default_permissions"].get(
            item_type, 
            PermissionLevel.PRIVATE.name
        )
    
    def set_default_permission(self, item_type: str, level: PermissionLevel):
        """Set default permission."""
        self.policy["default_permissions"][item_type] = level.name
        self._save()
    
    # ========== STATS ==========
    
    def get_stats(self) -> Dict:
        """Statistik permission."""
        return {
            "delegation_enabled": self.is_delegation_enabled(),
            "whitelist_users": len(self.policy["whitelist"]["users"]),
            "observers": len(self.policy["whitelist"]["observers"]),
            "agent_policy": self.policy["agent_policy"],
            "default_permissions": self.policy["default_permissions"],
        }