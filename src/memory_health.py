"""
Memory Health System
Monitor kesehatan memory: stale facts, duplicates, confidence decay
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger("saki.health")


class MemoryHealth:
    """Monitor dan kelola kesehatan memory Saki."""
    
    def __init__(self):
        self.stats_file = Path("data/memory_health.json")
        self._load()
    
    def _load(self):
        if self.stats_file.exists():
            with open(self.stats_file, "r", encoding="utf-8") as f:
                self.history = json.load(f)
        else:
            self.history = []
    
    def _save(self):
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.stats_file, "w", encoding="utf-8") as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)
    
    # ========== STALE FACTS ==========
    
    def find_stale_facts(self, days: int = 90) -> List[Dict]:
        """
        Cari fakta yang sudah lama tidak diakses.
        
        Args:
            days: Batas hari tidak diakses
        
        Returns:
            List fakta stale dengan info days_since_access
        """
        from src.database import lihat_semua_fakta
        
        all_facts = lihat_semua_fakta()
        now = datetime.now()
        stale = []
        
        for f in all_facts:
            fact_id = f[0]
            category = f[1]
            content = f[2]
            last_accessed = f[7]  # Index 7 = last_accessed
            created_at = f[8]     # Index 8 = created_at
            
            # Tentukan last activity
            last_active = last_accessed if last_accessed else created_at
            
            if last_active:
                try:
                    dt = datetime.strptime(last_active, "%Y-%m-%d %H:%M:%S")
                    days_since = (now - dt).days
                    
                    if days_since > days:
                        stale.append({
                            "id": fact_id,
                            "category": category,
                            "content": content[:100],
                            "days_since_access": days_since,
                            "last_accessed": last_accessed,
                            "importance": f[5],
                            "access_count": f[6],
                        })
                except:
                    continue
        
        # Sort: paling lama tidak diakses dulu
        stale.sort(key=lambda x: x["days_since_access"], reverse=True)
        
        return stale
    
    # ========== DUPLICATE FINDER ==========
    
    def find_duplicates(self) -> List[Dict]:
        """
        Cari fakta yang kemungkinan duplikat.
        Simple string similarity check.
        """
        from src.database import lihat_semua_fakta
        
        all_facts = lihat_semua_fakta()
        duplicates = []
        
        for i, f1 in enumerate(all_facts):
            for j, f2 in enumerate(all_facts):
                if j <= i:
                    continue
                
                content1 = (f1[2] or "").lower().strip()
                content2 = (f2[2] or "").lower().strip()
                
                # Skip kalau terlalu pendek
                if len(content1) < 10 or len(content2) < 10:
                    continue
                
                # Cek similarity sederhana
                if content1 in content2 or content2 in content1:
                    duplicates.append({
                        "id1": f1[0],
                        "id2": f2[0],
                        "content1": content1[:80],
                        "content2": content2[:80],
                        "category1": f1[1],
                        "category2": f2[1],
                        "reason": "Satu mengandung yang lain",
                        "confidence": 0.9,
                    })
                elif self._similarity(content1, content2) > 0.8:
                    duplicates.append({
                        "id1": f1[0],
                        "id2": f2[0],
                        "content1": content1[:80],
                        "content2": content2[:80],
                        "category1": f1[1],
                        "category2": f2[1],
                        "reason": "Sangat mirip",
                        "confidence": 0.7,
                    })
        
        return duplicates
    
    def _similarity(self, a: str, b: str) -> float:
        """Simple word overlap similarity."""
        words_a = set(a.split())
        words_b = set(b.split())
        
        if not words_a or not words_b:
            return 0.0
        
        intersection = words_a & words_b
        union = words_a | words_b
        
        return len(intersection) / len(union)
    
    # ========== CONFIDENCE DECAY ==========
    
    def apply_confidence_decay(self, days_threshold: int = 30, decay_rate: float = 0.05) -> int:
        """
        Turunkan confidence fakta yang sudah lama tidak divalidasi.
        
        Args:
            days_threshold: Mulai decay setelah N hari
            decay_rate: Penurunan per 30 hari (0.05 = 5%)
        
        Returns:
            Jumlah fakta yang di-decay
        """
        from src.database import lihat_semua_fakta, lihat_fakta_by_id, edit_fakta
        from src.evidence import EvidenceTracker
        
        et = EvidenceTracker()
        all_facts = lihat_semua_fakta()
        now = datetime.now()
        decayed = 0
        
        for f in all_facts:
            fact_id = f[0]
            evidence = et.get_evidence(fact_id)
            
            if not evidence:
                continue
            
            last_validated = evidence.get("last_validated", "")
            if not last_validated:
                continue
            
            try:
                dt = datetime.fromisoformat(last_validated)
                days_since = (now - dt).days
            except:
                continue
            
            if days_since > days_threshold:
                # Hitung decay
                periods = days_since // 30
                new_confidence = max(0.1, evidence.get("confidence", 1.0) - (decay_rate * periods))
                
                # Update evidence
                et.validate(fact_id, new_confidence)
                decayed += 1
        
        logger.info(f"Confidence decay applied to {decayed} facts")
        return decayed
    
    # ========== MEMORY STATS ==========
    
    def get_memory_stats(self) -> Dict:
        """
        Dapatkan statistik memory lengkap.
        """
        from src.database import (
            lihat_semua_fakta, lihat_semua_reflections, 
            lihat_semua_dokumen, get_daily_stats, get_weekly_stats
        )
        from src.evidence import EvidenceTracker
        
        et = EvidenceTracker()
        
        # Basic counts
        all_facts = lihat_semua_fakta()
        total_facts = len(all_facts)
        total_reflections = len(lihat_semua_reflections())
        total_docs = len(lihat_semua_dokumen())
        
        # Category distribution
        categories = {}
        for f in all_facts:
            cat = f[1]
            categories[cat] = categories.get(cat, 0) + 1
        
        # Importance distribution
        importance_dist = {"high": 0, "medium": 0, "low": 0}
        for f in all_facts:
            imp = f[5]
            if imp >= 8:
                importance_dist["high"] += 1
            elif imp >= 5:
                importance_dist["medium"] += 1
            else:
                importance_dist["low"] += 1
        
        # Evidence coverage
        evidence_coverage = sum(1 for f in all_facts if et.get_evidence(f[0])) if total_facts > 0 else 0
        
        # Stale facts
        stale = self.find_stale_facts(90)
        
        # Duplicates
        duplicates = self.find_duplicates()
        
        # Daily & weekly
        daily = get_daily_stats()
        weekly = get_weekly_stats()
        
        # Growth (dari history)
        self.history.append({
            "date": datetime.now().isoformat(),
            "total_facts": total_facts,
            "total_reflections": total_reflections,
            "total_docs": total_docs,
        })
        # Keep last 365 entries
        if len(self.history) > 365:
            self.history.pop(0)
        self._save()
        
        # Growth rate (7 hari terakhir)
        growth_rate = 0
        if len(self.history) >= 7:
            week_ago_count = self.history[-7]["total_facts"]
            growth_rate = total_facts - week_ago_count
        
        return {
            "totals": {
                "facts": total_facts,
                "reflections": total_reflections,
                "documents": total_docs,
                "relationships": 0,  # Placeholder
            },
            "categories": categories,
            "importance": importance_dist,
            "evidence_coverage": {
                "with_evidence": evidence_coverage,
                "total": total_facts,
                "percentage": round(evidence_coverage / total_facts * 100, 1) if total_facts > 0 else 0,
            },
            "health": {
                "stale_facts": len(stale),
                "duplicates": len(duplicates),
                "stale_details": stale[:5],  # Top 5
                "duplicate_details": duplicates[:5],  # Top 5
            },
            "growth": {
                "daily_new": daily.get("new_facts", 0),
                "weekly_new": weekly.get("week_facts", 0),
                "weekly_growth_rate": growth_rate,
            },
            "history": self.history[-30:],  # Last 30 days
        }
    
    def get_health_report(self) -> str:
        """
        Generate laporan kesehatan memory dalam format text.
        """
        stats = self.get_memory_stats()
        
        report = "📊 MEMORY HEALTH REPORT\n"
        report += "═" * 40 + "\n\n"
        
        # Totals
        t = stats["totals"]
        report += f"📦 Total: {t['facts']} fakta | {t['reflections']} insight | {t['documents']} dokumen\n\n"
        
        # Categories
        report += "📂 Kategori:\n"
        for cat, count in sorted(stats["categories"].items(), key=lambda x: x[1], reverse=True):
            bar = "█" * min(count, 20)
            report += f"  {cat:15} {bar} {count}\n"
        report += "\n"
        
        # Importance
        imp = stats["importance"]
        report += "⭐ Importance:\n"
        report += f"  🔴 High:   {imp['high']}\n"
        report += f"  🟡 Medium: {imp['medium']}\n"
        report += f"  🟢 Low:    {imp['low']}\n\n"
        
        # Evidence
        ev = stats["evidence_coverage"]
        report += f"🔍 Evidence coverage: {ev['with_evidence']}/{ev['total']} ({ev['percentage']}%)\n\n"
        
        # Health
        h = stats["health"]
        report += "🏥 Health:\n"
        if h["stale_facts"] > 0:
            report += f"  ⚠️  {h['stale_facts']} stale facts (>90 hari)\n"
        else:
            report += f"  ✅ No stale facts\n"
        
        if h["duplicates"] > 0:
            report += f"  ⚠️  {h['duplicates']} possible duplicates\n"
        else:
            report += f"  ✅ No duplicates\n"
        report += "\n"
        
        # Growth
        g = stats["growth"]
        report += "📈 Growth:\n"
        report += f"  Hari ini: +{g['daily_new']} fakta\n"
        report += f"  Minggu ini: +{g['weekly_new']} fakta\n"
        report += f"  7-day growth: {g['weekly_growth_rate']}\n"
        
        return report


# Singleton
_memory_health = None

def get_memory_health() -> MemoryHealth:
    global _memory_health
    if _memory_health is None:
        _memory_health = MemoryHealth()
    return _memory_health