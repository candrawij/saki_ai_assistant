"""
Evidence Layer — Track sumber, konteks, dan validitas setiap fakta
"""

import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from pathlib import Path

class EvidenceTracker:
    """
    Track evidence untuk setiap fakta di memory Saki.
    
    Evidence menjawab:
    - Siapa yang menyatakan fakta ini? (observer)
    - Dari chat mana? (source)
    - Kapan terakhir divalidasi? (last_validated)
    - Seberapa yakin? (confidence)
    - Masih relevan? (expiry)
    """
    
    def __init__(self):
        self.evidence_file = Path("data/evidence.json")
        self._load()
    
    def _load(self):
        """Load evidence dari file."""
        if self.evidence_file.exists():
            with open(self.evidence_file, "r", encoding="utf-8") as f:
                self.evidences = json.load(f)
        else:
            self.evidences = {}
    
    def _save(self):
        """Simpan evidence ke file."""
        self.evidence_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.evidence_file, "w", encoding="utf-8") as f:
            json.dump(self.evidences, f, ensure_ascii=False, indent=2)
    
    def record(
        self,
        fact_id: int,
        observer: str = "user",
        perspective: str = "internal",
        source_chat_id: Optional[int] = None,
        source_type: str = "manual",
        confidence: float = 1.0,
        shareable: bool = False,
        agent_usable: bool = True,
        expiry_days: Optional[int] = None,
    ) -> Dict:
        """
        Record evidence untuk sebuah fakta.
        
        Args:
            fact_id: ID fakta di database
            observer: Siapa yang menyatakan (user/Orang A/Orang B)
            perspective: internal (pemilik sendiri) / external (orang lain)
            source_chat_id: ID chat sumber (kalau dari percakapan)
            source_type: manual/auto_extract/reflection/agent
            confidence: 0.0 - 1.0
            shareable: Boleh dibagi ke orang lain?
            agent_usable: Boleh dipakai Saki saat jadi delegasi?
            expiry_days: Kadaluarsa dalam N hari (None = permanen)
        
        Returns:
            Evidence record
        """
        now = datetime.now().isoformat()
        
        evidence = {
            "fact_id": fact_id,
            "observer": observer,
            "perspective": perspective,
            "source_chat_id": source_chat_id,
            "source_type": source_type,
            "confidence": confidence,
            "shareable": shareable,
            "agent_usable": agent_usable,
            "created_at": now,
            "last_validated": now,
            "validation_count": 1,
            "expiry": (datetime.now() + timedelta(days=expiry_days)).isoformat() if expiry_days else None,
            "history": [
                {
                    "action": "created",
                    "timestamp": now,
                    "detail": f"Recorded by {observer} ({perspective})"
                }
            ]
        }
        
        key = str(fact_id)
        if key in self.evidences:
            old = self.evidences[key]
            evidence["history"] = old.get("history", []) + evidence["history"]
            evidence["validation_count"] = old.get("validation_count", 0)
        
        self.evidences[key] = evidence
        self._save()
        
        return evidence
    
    def validate(self, fact_id: int, new_confidence: Optional[float] = None) -> bool:
        """
        Validasi ulang fakta — tandai masih relevan.
        """
        key = str(fact_id)
        if key not in self.evidences:
            return False
        
        now = datetime.now().isoformat()
        self.evidences[key]["last_validated"] = now
        self.evidences[key]["validation_count"] += 1
        
        if new_confidence is not None:
            self.evidences[key]["confidence"] = new_confidence
        
        self.evidences[key]["history"].append({
            "action": "validated",
            "timestamp": now,
            "detail": f"Confidence: {self.evidences[key]['confidence']}"
        })
        
        self._save()
        return True
    
    def get_evidence(self, fact_id: int) -> Optional[Dict]:
        """Get evidence untuk satu fakta."""
        return self.evidences.get(str(fact_id))
    
    def get_shareable_facts(self) -> List[int]:
        """Ambil semua fakta yang shareable."""
        return [
            int(k) for k, v in self.evidences.items()
            if v.get("shareable", False)
        ]
    
    def get_agent_usable_facts(self) -> List[int]:
        """Ambil semua fakta yang boleh dipakai agent."""
        return [
            int(k) for k, v in self.evidences.items()
            if v.get("agent_usable", True)
        ]
    
    def get_stale_facts(self, days: int = 90) -> List[int]:
        """Cari fakta yang sudah lama tidak divalidasi."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        stale = []
        
        for k, v in self.evidences.items():
            if v.get("last_validated", "") < cutoff:
                stale.append(int(k))
        
        return stale
    
    def get_expired_facts(self) -> List[int]:
        """Cari fakta yang sudah expired."""
        now = datetime.now().isoformat()
        expired = []
        
        for k, v in self.evidences.items():
            expiry = v.get("expiry")
            if expiry and expiry < now:
                expired.append(int(k))
        
        return expired
    
    def get_multi_perspective(self, subject: str) -> List[Dict]:
        """
        Dapatkan semua perspektif tentang suatu subjek.
        Ini butuh integrasi dengan database untuk cari by content.
        """
        # Placeholder — akan diimplementasi setelah DB query siap
        return []
    
    def get_stats(self) -> Dict:
        """Statistik evidence."""
        total = len(self.evidences)
        internal = sum(1 for v in self.evidences.values() if v.get("perspective") == "internal")
        external = sum(1 for v in self.evidences.values() if v.get("perspective") == "external")
        shareable = sum(1 for v in self.evidences.values() if v.get("shareable", False))
        stale = len(self.get_stale_facts(90))
        
        return {
            "total_facts": total,
            "internal_perspectives": internal,
            "external_perspectives": external,
            "shareable_facts": shareable,
            "stale_facts": stale,
            "expired_facts": len(self.get_expired_facts()),
        }