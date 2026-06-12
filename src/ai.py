"""
Saki AI Module
Semua fungsi AI: chat, ringkas, ekstrak, reflection, merge
Dengan Model Router untuk performa optimal
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import ollama
import json
import re
import logging
from typing import Optional, List, Tuple, Dict
import datetime
import os
import time

# Fix encoding untuk Windows
sys.stdout.reconfigure(encoding='utf-8')

from src.model_router import ModelRouter, TaskType

# Inisialisasi Model Router (sekali aja)
_model_router = None

def get_router() -> ModelRouter:
    """Lazy init Model Router."""
    global _model_router
    if _model_router is None:
        _model_router = ModelRouter()
    return _model_router

logger = logging.getLogger("saki")

# ========== KONFIGURASI ==========
MODEL = "qwen3:4b"  # Default model (fallback)
NAMA_AI = "Saki"
AUTO_EXTRACT_THRESHOLD = 0.65
SUMMARY_MAX_LENGTH = 4000
MIN_CONFIDENCE_THRESHOLD = 0.5
MIN_IMPORTANCE_FOR_TRACKING = 5

# Import database functions
from src.database import (
    lihat_semua_fakta, lihat_fakta_by_id, simpan_fakta, simpan_reflection,
    hapus_fakta, cek_fakta_duplikat, track_access, tandai_fakta_reflected,
    ambil_fakta_belum_reflected, get_facts_for_timeline,
    cari_dokumen_semantik, lihat_semua_dokumen
)

# ========== SYSTEM PROMPT ==========
self_text = ""
self_path = "SAKI_SELF.md"
if os.path.exists(self_path):
    try:
        with open(self_path, "r", encoding="utf-8") as f:
            self_text = f.read()
        logger.debug("Loaded SAKI_SELF.md for system prompt")
    except Exception as e:
        logger.warning(f"Failed to load SAKI_SELF.md: {str(e)}")

SYSTEM_PROMPT = f"""Kamu adalah asisten AI pribadi bernama {NAMA_AI}.

{self_text}

Kamu membantu merangkum dokumen, menjawab pertanyaan, dan mengingat informasi penting.
Kamu menjawab dalam Bahasa Indonesia yang natural, hangat, dan langsung ke inti.
Saat merangkum, gunakan format:
## Ringkasan
[3-5 poin utama]

## Kata Kunci
[keyword1, keyword2, keyword3]"""


# ========== JSON PARSER ==========

def _parse_json_response(raw: str) -> Optional[List[Dict]]:
    """
    Parse JSON dari response AI dengan multiple fallback.
    Return None kalau gagal total.
    """
    # Method 1: Direct parse
    try:
        data = json.loads(raw)
        if isinstance(data, list): return data
        if isinstance(data, dict): return [data]
    except: pass
    
    # Method 2: Strip markdown code blocks
    cleaned = raw
    if "```" in cleaned:
        parts = cleaned.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"): part = part[4:].strip()
            if part.startswith("["):
                try:
                    data = json.loads(part)
                    if isinstance(data, list): return data
                except: continue
            if part.startswith("{"):
                try:
                    data = json.loads(part)
                    if isinstance(data, dict): return [data]
                except: continue
    
    # Method 3: Extract first JSON array
    match = re.search(r'\[.*\]', raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, list): return data
        except: pass
    
    # Method 4: Extract first JSON object
    match = re.search(r'\{[^{}]*\}', raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict): return [data]
        except: pass
    
    # Method 5: Fix trailing commas
    try:
        fixed = re.sub(r',\s*\]', ']', raw)
        fixed = re.sub(r',\s*\}', '}', fixed)
        data = json.loads(fixed)
        if isinstance(data, list): return data
    except: pass
    
    # Method 6: Parse Markdown numbered list
    # Format: 1. **Title** (Fakta #1, #2, #3)
    insights = []
    lines = raw.strip().split('\n')
    for line in lines:
        line = line.strip()
        # Match: "1. **Title** (Fakta #1, #2)" atau "1. **Title** (Fakta #1, #2, #3)"
        match = re.match(r'\d+\.\s*\*\*(.+?)\*\*\s*\(Fakta\s+(.+?)\)', line)
        if match:
            title = match.group(1).strip()
            ids_str = match.group(2)
            # Extract IDs
            ids = [int(x.strip().replace('#', '')) for x in re.findall(r'#?\d+', ids_str)]
            if title and ids:
                insights.append({
                    "title": title,
                    "content": title,
                    "source_ids": ids,
                    "category": "insight"
                })
    
    if insights:
        logger.info(f"Parsed {len(insights)} insights from Markdown list")
        return insights
    
    # Method 7: Parse text format relationships
    # Format: "**(23, 29)**", "(#23, #29)", "ID 23 dan 29"
    pairs = re.findall(r'\*?\*?\s*\(?\s*#?(\d+)\s*[,;]\s*#?(\d+)\s*\)?\s*\*?\*?', raw)
    if not pairs:
        # Also try: "ID 23 dan 29" atau "fakta 23 dengan 29"
        pairs = re.findall(r'(?:ID|fakta|#)\s*(\d+)\s*(?:dan|dengan|,)\s*(?:ID|fakta|#)?\s*(\d+)', raw, re.IGNORECASE)
    
    if pairs:
        insights = []
        for id1, id2 in pairs:
            insights.append({
                "source_id": int(id1),
                "target_id": int(id2),
                "relation_type": "related",
                "confidence": 0.8
            })
        if insights:
            logger.info(f"Parsed {len(insights)} relationships from text format")
            return insights
    
    return None

# ========== FUNGSI AI DASAR ==========

def ringkas_teks(teks: str) -> str:
    """Meringkas teks panjang — pakai Model Router."""
    try:
        router = get_router()
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Ringkas teks berikut:\n\n{teks}"}
        ]
        result = router.chat(messages, task_type=TaskType.SUMMARIZE)
        return result["content"]
    except Exception as e:
        logger.error(f"Summarization failed: {str(e)}", exc_info=True)
        return f"Maaf, gagal meringkas: {type(e).__name__}"


def chat_saki(pesan: str, riwayat_chat: List[Dict] = None) -> str:
    """Chat dengan Saki — pakai Model Router + Agent Router."""
    
    # === AGENT ROUTER CHECK ===
    try:
        from src.agents.router import AgentRouter
        router = AgentRouter()
        agent, routed_message = router.route(pesan)
        
        if agent == "special":
            result = router.execute_special(routed_message)
            return result
        
        if agent is not None:
            result = agent.execute(routed_message)
            return f"🤖 **{agent.name}**\n\n{result}"
    except Exception as e:
        logger.debug(f"Agent routing skipped: {str(e)}")
    
    # === BUILD MESSAGES ===
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Tambah fakta sebagai konteks
    fakta = lihat_semua_fakta()
    if fakta:
        fakta_text = "\n".join([
            f"- [{f[1]}] {f[2]}"
            for f in fakta if f[4] >= MIN_CONFIDENCE_THRESHOLD
        ])
        if fakta_text:
            messages.append({
                "role": "system",
                "content": f"Info tentang user:\n{fakta_text}"
            })
        for f in fakta:
            if f[5] >= MIN_IMPORTANCE_FOR_TRACKING:
                track_access(f[0])
    
    # === SEMANTIC SEARCH (dengan skip logic) ===
    dokumen_relevan = []
    total_docs = len(lihat_semua_dokumen())
    
    if total_docs > 0:
        if len(pesan.split()) > 5 or total_docs > 5:
            try:
                dokumen_relevan = cari_dokumen_semantik(pesan, n_results=2)
            except Exception as e:
                logger.warning(f"Document search failed (non-critical): {str(e)}")
        else:
            logger.debug(f"Semantic search SKIPPED: short query + few docs ({total_docs} docs)")
    
    if dokumen_relevan:
        docs_text = []
        for doc in dokumen_relevan:
            nama = doc[1]
            ringkasan = doc[4] if doc[4] else "Tidak ada ringkasan"
            docs_text.append(f"📄 {nama}\n{ringkasan[:200]}")
        if docs_text:
            messages.insert(1, {
                "role": "system",
                "content": "Dokumen relevan:\n\n" + "\n\n".join(docs_text)
            })
    
    # Tambah riwayat chat
    if riwayat_chat:
        for msg in riwayat_chat[-6:]:
            messages.append(msg)
    
    messages.append({"role": "user", "content": pesan})
    
    # === MODEL ROUTER ===
    try:
        router = get_router()
        task_type = router.classify_task(pesan)
        result = router.chat(messages, task_type=task_type)
        return result["content"]
    except Exception as e:
        logger.error(f"Chat failed: {str(e)}", exc_info=True)
        try:
            response = ollama.chat(model=MODEL, messages=messages)
            return response["message"]["content"]
        except:
            return f"Maaf, terjadi kesalahan: {type(e).__name__}"


def auto_ekstrak_fakta(pesan_user: str, riwayat_chat: List[Dict] = None) -> Optional[Dict]:
    """Ekstrak fakta penting dari pesan user — pakai Model Router."""
    if len(pesan_user.split()) < 5:
        logger.debug(f"Auto-extract SKIPPED: chat terlalu pendek ({len(pesan_user.split())} kata)")
        return None
    
    konteks = ""
    if riwayat_chat and len(riwayat_chat) >= 2:
        last_msgs = riwayat_chat[-3:-1]
        konteks = "\n".join([f"{m['role']}: {m['content'][:200]}" for m in last_msgs])
    
    prompt = f"""Analisis pesan berikut. Apakah mengandung FAKTA PENTING TENTANG USER yang bersifat PERMANEN?

KRITERIA FAKTA PENTING:
- Proyek yang sedang dikerjakan
- Skill atau kemampuan
- Pekerjaan atau pendidikan
- Preferensi KUAT yang konsisten
- Kontak atau identitas penting
- Deadline atau target serius

BUKAN FAKTA PENTING:
- Obrolan ringan atau candaan
- Kebutuhan sesaat
- Rencana belum pasti
- Pertanyaan atau permintaan tolong

KONTEKS:
{konteks}

PESAN USER:
"{pesan_user}"

Jawab JSON saja:
{{"is_fact": true/false, "confidence": 0.0-1.0, "fact": "fakta ringkas", "category": "proyek/preferensi/kontak/jadwal/akun/skill/pekerjaan/pendidikan/umum"}}
Jika ragu, pilih false."""

    try:
        router = get_router()
        result = router.chat(
            messages=[
                {"role": "system", "content": "Kamu adalah filter fakta yang KETAT. Jawab HANYA JSON."},
                {"role": "user", "content": prompt}
            ],
            task_type=TaskType.EXTRACT
        )
        hasil = result["content"].strip()
        
        if hasil.startswith("```"):
            hasil = hasil.split("\n", 1)[1].rstrip("```")
        hasil = hasil.strip()
        
        data = json.loads(hasil)
        
        if data.get("is_fact") and data.get("confidence", 0) >= AUTO_EXTRACT_THRESHOLD:
            logger.info(f"Auto-extract ACCEPTED: [{data.get('category')}] {data.get('fact')}")
            return {
                "fact": data["fact"],
                "category": data.get("category", "umum"),
                "confidence": data["confidence"]
            }
        return None
        
    except json.JSONDecodeError:
        logger.warning(f"Auto-extract JSON parse failed")
        return None
    except Exception as e:
        logger.error(f"Auto-extract failed: {str(e)}", exc_info=True)
        return None


def auto_rate_importance(content: str, category: str) -> int:
    """AI menilai importance (1-10) — pakai Model Router."""
    prompt = f"""Nilai seberapa PENTING fakta ini untuk diingat. HANYA beri angka 1-10.

10 = Identitas, password, info kritis
8-9 = Proyek aktif, deadline, kontak penting
6-7 = Skill, pekerjaan, pendidikan
4-5 = Preferensi, hobi yang serius
1-3 = Hobi ringan, info umum

FAKTA: "{content}"
KATEGORI: {category}

Jawab HANYA satu angka."""

    try:
        router = get_router()
        result = router.chat(
            messages=[
                {"role": "system", "content": "Jawab HANYA satu angka 1-10."},
                {"role": "user", "content": prompt}
            ],
            task_type=TaskType.EXTRACT
        )
        hasil = result["content"].strip()
        
        match = re.search(r'\b(10|[1-9])\b', hasil)
        if match:
            return int(match.group(1))
        
        fallback = {"akun": 10, "proyek": 8, "jadwal": 7, "kontak": 7,
                    "pekerjaan": 7, "skill": 6, "pendidikan": 6,
                    "preferensi": 4, "umum": 5}
        return fallback.get(category, 5)
    except:
        return 5


def merge_fakta_dengan_ai(fakta_list: List[Tuple]) -> str:
    """Gabungkan fakta dengan AI — pakai Model Router."""
    if not fakta_list:
        return "Tidak ada fakta untuk digabung."
    
    fakta_text = "\n".join([f"- {f[2]}" for f in fakta_list])
    logger.info(f"Merging {len(fakta_list)} facts")
    
    prompt = f"""Gabungkan fakta-fakta berikut menjadi satu fakta yang padat dan koheren.
Jangan ada informasi yang hilang. Hilangkan pengulangan.
Output hanya fakta gabungannya saja.

{fakta_text}

Hasil gabungan:"""
    
    try:
        router = get_router()
        result = router.chat(
            messages=[{"role": "user", "content": prompt}],
            task_type=TaskType.MERGE
        )
        return result["content"].strip()
    except Exception as e:
        logger.error(f"Merge failed: {str(e)}")
        return f"[Gagal menggabungkan: {type(e).__name__}]"


def deteksi_duplikat_semantik() -> List[Dict]:
    """Deteksi fakta duplikat — pakai Model Router."""
    fakta = lihat_semua_fakta()
    if len(fakta) < 2:
        return []
    
    fakta_list = "\n".join([f"- [#{f[0]}] [{f[1]}] {f[2]}" for f in fakta])
    
    prompt = f"""Analisis daftar fakta berikut. Temukan pasangan yang kemungkinan duplikat.
{fakta_list}

Jawab JSON array: [{{"id1": 1, "id2": 2, "reason": "..."}}]
Jika tidak ada, jawab []."""

    try:
        router = get_router()
        result = router.chat(
            messages=[
                {"role": "system", "content": "Jawab HANYA JSON array."},
                {"role": "user", "content": prompt}
            ],
            task_type=TaskType.RELATIONSHIP
        )
        raw = result["content"].strip()
        
        parsed = _parse_json_response(raw)
        if parsed:
            return parsed
        return []
    except:
        return []


# ========== REFLECTION ==========

def generate_reflection() -> Tuple[List[Dict], str]:
    """Analisis fakta, hasilkan insight."""
    fakta = ambil_fakta_belum_reflected()
    
    if len(fakta) < 3:
        return [], f"Butuh minimal 3 fakta baru. Saat ini: {len(fakta)}"
    
    # ✅ Batasi 15 fakta
    total_unreflected = len(fakta)
    if len(fakta) > 15:
        fakta = fakta[:15]
    
    logger.info(f"Generating reflection for {len(fakta)}/{total_unreflected} unreflected facts")
    
    fakta_text = "\n".join([f"[#{f[0]}] [{f[1]}] {f[2]}" for f in fakta])
    
    prompt = f"""Analisis fakta-fakta berikut. KELOMPOKKAN yang terkait.

{fakta_text}

ATURAN:
1. HANYA kelompokkan fakta yang membahas TOPIK SAMA
2. Maksimal 5 insight
3. Fakta tidak terkait → ABAIKAN

Output HARUS JSON array:
[{{"title": "Judul", "content": "Isi insight", "source_ids": [1,3], "category": "proyek"}}]
Kalau tidak ada, jawab: []"""

    try:
        router = get_router()
        result = router.chat(
            messages=[
                {"role": "system", "content": "Jawab HANYA JSON array. Tidak boleh ada teks lain."},
                {"role": "user", "content": prompt}
            ],
            task_type=TaskType.REFLECTION
        )
        raw = result["content"].strip()
        logger.info(f"Reflection: model={result['model']}, {result['tokens']:.0f} tokens in {result['elapsed']:.1f}s")
        logger.debug(f"Reflection raw ({len(raw)} chars): {raw[:300]}")
        
        # ✅ Pakai parser dengan fallback
        insights = _parse_json_response(raw)
        
        if insights is None:
            logger.error(f"Failed to parse reflection JSON. Raw: {raw[:500]}")
            return [], f"Gagal memproses hasil AI. Raw: {raw[:100]}..."
        
        if len(insights) == 0:
            return [], "Tidak ada pengelompokan yang bisa dibuat."
        
        logger.info(f"Reflection generated {len(insights)} insights")
        return insights, ""
    
    except json.JSONDecodeError as e:
        logger.error(f"Reflection JSON parse failed: {str(e)}")
        return [], f"Gagal memproses hasil AI. Coba lagi."
    except Exception as e:
        logger.error(f"Reflection failed: {str(e)}", exc_info=True)
        return [], f"Gagal generate reflection: {type(e).__name__}"


def save_reflections(insights: List[Dict]) -> int:
    """Simpan hasil reflection ke database."""
    saved = 0
    all_source_ids = []
    
    for insight in insights:
        title = insight.get("title", "Untitled")
        content = insight.get("content", "")
        source_ids = insight.get("source_ids", [])
        category = insight.get("category", "insight")
        
        if not content or not source_ids:
            continue
        
        reflection_id = simpan_reflection(title, content, source_ids, category, importance=9)
        if reflection_id:
            saved += 1
            all_source_ids.extend(source_ids)
    
    if all_source_ids:
        tandai_fakta_reflected(list(set(all_source_ids)))
    
    logger.info(f"Saved {saved} reflections")
    return saved


# ========== TIMELINE ==========

def generate_timeline() -> List[Dict]:
    """Generate timeline 3 level: bulan -> minggu -> hari."""
    from src.database import get_all_timeline_data
    from collections import defaultdict
    import datetime
    
    data = get_all_timeline_data()
    all_facts = data["facts"]
    all_reflections = data["reflections"]
    all_chats = data["chats"]
    
    if not all_facts and not all_reflections and not all_chats:
        return []
    
    daily_data = defaultdict(lambda: {"facts": [], "insights": [], "chat_count": 0})
    
    for f in all_facts:
        try:
            dt = datetime.datetime.strptime(f[3], "%Y-%m-%d %H:%M:%S")
            date_key = dt.strftime("%Y-%m-%d")
            daily_data[date_key]["facts"].append({"id": f[0], "category": f[1], "content": f[2]})
        except:
            continue
    
    for r in all_reflections:
        try:
            dt = datetime.datetime.strptime(r[4], "%Y-%m-%d %H:%M:%S")
            date_key = dt.strftime("%Y-%m-%d")
            daily_data[date_key]["insights"].append({"id": r[0], "title": r[1], "content": r[2], "category": r[3]})
        except:
            continue
    
    for c in all_chats:
        try:
            daily_data[c[0]]["chat_count"] = c[1]
        except:
            continue
    
    all_documents = lihat_semua_dokumen()
    for d in all_documents:
        try:
            dt = datetime.datetime.strptime(d[4], "%Y-%m-%d %H:%M:%S")
            date_key = dt.strftime("%Y-%m-%d")
            if "documents" not in daily_data[date_key]:
                daily_data[date_key]["documents"] = []
            daily_data[date_key]["documents"].append({"id": d[0], "filename": d[1], "type": d[2]})
        except:
            continue
    
    months = defaultdict(lambda: {"weeks": defaultdict(lambda: {"days": {}}), "total_items": 0})
    
    for date_str in sorted(daily_data.keys()):
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        month_key = dt.strftime("%Y-%m")
        month_name = dt.strftime("%B %Y")
        first_day = dt.replace(day=1)
        week_num = ((dt - first_day).days // 7) + 1
        week_label = f"Minggu {week_num}"
        
        day_data = daily_data[date_str]
        items_count = (
            len(day_data.get("facts", [])) + 
            len(day_data.get("insights", [])) + 
            len(day_data.get("documents", [])) +
            (1 if day_data.get("chat_count", 0) > 0 else 0)
        )
        
        months[month_key]["name"] = month_name
        months[month_key]["year"] = dt.year
        months[month_key]["month_num"] = dt.month
        months[month_key]["total_items"] += items_count
        months[month_key]["weeks"][week_label]["days"][dt.day] = {
            "date": date_str, "day_name": dt.strftime("%A"), **day_data
        }
    
    result = []
    for month_key in sorted(months.keys()):
        month_data = months[month_key]
        weeks_list = []
        for week_label in sorted(month_data["weeks"].keys()):
            week_data = month_data["weeks"][week_label]
            days_list = [week_data["days"][d] for d in sorted(week_data["days"].keys())]
            weeks_list.append({
                "label": week_label, "days": days_list,
                "total_items": sum(len(d["facts"]) + len(d["insights"]) + (1 if d["chat_count"] > 0 else 0) for d in days_list)
            })
        result.append({
            "year": month_data["year"], "month": month_data["name"].split()[0],
            "month_name": month_data["name"], "total_items": month_data["total_items"],
            "summary": None, "weeks": weeks_list
        })
    
    return result


def generate_timeline_summary(month_name: str, items: List[Dict]) -> str:
    """Generate AI summary untuk satu bulan."""
    if not items:
        return "Tidak ada aktivitas."
    
    facts_text, insights_text = [], []
    for week in items:
        for day in week.get("days", []):
            for f in day.get("facts", []):
                facts_text.append(f"- [{f['category']}] {f['content'][:100]}")
            for ins in day.get("insights", []):
                insights_text.append(f"- [{ins['category']}] {ins['title']}: {ins['content'][:100]}")
    
    context = ""
    if facts_text:
        context += "FAKTA:\n" + "\n".join(facts_text[:20]) + "\n\n"
    if insights_text:
        context += "INSIGHT:\n" + "\n".join(insights_text[:10])
    
    if not context.strip():
        return "Aktivitas ringan."
    
    prompt = f"""Ringkas aktivitas user selama {month_name} dalam 1-2 kalimat Bahasa Indonesia.
{context}
Ringkasan:"""

    try:
        router = get_router()
        result = router.chat(
            messages=[
                {"role": "system", "content": "Kamu merangkum aktivitas bulanan."},
                {"role": "user", "content": prompt}
            ],
            task_type=TaskType.SUMMARIZE
        )
        return result["content"].strip()
    except:
        return f"Bulan ini: {len(facts_text)} fakta, {len(insights_text)} insight."


def generate_morning_greeting() -> str:
    """Generate sapaan pagi."""
    from src.database import get_daily_stats
    import datetime
    
    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    stats = get_daily_stats(yesterday)
    
    hour = datetime.datetime.now().hour
    greeting = "Selamat pagi" if hour < 11 else "Selamat siang" if hour < 15 else "Selamat sore" if hour < 19 else "Selamat malam"
    
    parts = [f"{greeting}!"]
    if stats.get("new_facts", 0) > 0 or stats.get("new_insights", 0) > 0:
        parts.append(f"Kemarin: {stats['new_facts']} fakta, {stats['new_insights']} insight, {stats['chat_count']} chat.")
    parts.append(f"Total: {stats.get('total_facts', 0)} fakta, {stats.get('total_insights', 0)} insight.")
    
    return " ".join(parts)


# ========== RELATIONSHIPS ==========

def extract_relationships() -> Tuple[int, str]:
    from src.database import lihat_semua_fakta, simpan_relationship, hapus_semua_relationships
    
    fakta = lihat_semua_fakta()
    if len(fakta) < 3:
        return 0, "Minimal 3 fakta."
    
    hapus_semua_relationships()
    
    # ✅ Kirim SEMUA fakta, tapi prompt lebih simpel
    fakta_text = "\n".join([f"[#{f[0]}] [{f[1]}] {f[2][:60]}" for f in fakta])
    
    prompt = f"""Temukan PASANGAN yang terkait. Output HARUS JSON array.
    
{fakta_text}

[{{"source_id": 1, "target_id": 3, "relation_type": "related", "confidence": 0.9}}]
Kalau tidak ada: []"""

    try:
        router = get_router()
        result = router.chat(
            messages=[
                {"role": "system", "content": "Jawab HANYA JSON array."},
                {"role": "user", "content": prompt}
            ],
            task_type=TaskType.RELATIONSHIP
        )
        raw = result["content"].strip()
        logger.debug(f"Relationship raw: {raw[:300]}")
        
        relationships = _parse_json_response(raw)
        
        if relationships is None:
            return 0, f"Parse gagal. Raw: {raw[:100]}"
        
        saved = 0
        for rel in relationships:
            sid = rel.get("source_id") or rel.get("id1")
            tid = rel.get("target_id") or rel.get("id2")
            if not sid or not tid:
                continue
            
            # ✅ Validasi: cek fakta beneran ada
            from src.database import lihat_fakta_by_id
            if not lihat_fakta_by_id(int(sid)) or not lihat_fakta_by_id(int(tid)):
                logger.warning(f"Skip invalid relationship: {sid} <-> {tid}")
                continue
            
            rtype = rel.get("relation_type", "related")
            conf = rel.get("confidence", 0.7)
            
            try:
                rid = simpan_relationship(int(sid), int(tid), rtype, float(conf))
                if rid: saved += 1
            except: continue
        
        logger.info(f"Extracted {saved} relationships")
        return saved, ""
    
    except Exception as e:
        logger.error(f"Relationship failed: {e}")
        return 0, str(e)

def build_knowledge_graph() -> Dict:
    """Bangun knowledge graph dari relationships."""
    from src.database import lihat_semua_relationships, lihat_semua_fakta
    
    relationships = lihat_semua_relationships()
    fakta_list = lihat_semua_fakta()
    fakta = {f[0]: f for f in fakta_list}
    
    nodes = {f_id: {"id": f_id, "category": f_data[1], "content": f_data[2][:80], "importance": f_data[5]} for f_id, f_data in fakta.items()}
    edges = [{"id": rel["id"], "source": rel["source_id"], "target": rel["target_id"], "type": rel["relation_type"], "confidence": rel["confidence"]} for rel in relationships]
    
    clusters, visited = [], set()
    for node_id in nodes:
        if node_id not in visited:
            cluster, queue = set(), [node_id]
            while queue:
                current = queue.pop(0)
                if current not in visited:
                    visited.add(current)
                    cluster.add(current)
                    for edge in edges:
                        if edge["source"] == current and edge["target"] not in visited:
                            queue.append(edge["target"])
                        if edge["target"] == current and edge["source"] not in visited:
                            queue.append(edge["source"])
            if len(cluster) >= 2:
                clusters.append(cluster)
    
    return {"nodes": nodes, "edges": edges, "clusters": clusters, "total_nodes": len(nodes), "total_edges": len(edges), "total_clusters": len(clusters)}


def generate_weekly_summary_v2() -> str:
    """Generate ringkasan mingguan."""
    from src.database import get_weekly_stats, lihat_semua_fakta
    
    stats = get_weekly_stats()
    if stats.get("week_facts", 0) == 0:
        return "Minggu ini belum ada aktivitas."
    
    week_start = stats["week_start"]
    fakta_minggu_ini = [f for f in lihat_semua_fakta() if f[8] and f[8] >= week_start]
    
    if not fakta_minggu_ini:
        return "Tidak ada fakta baru minggu ini."
    
    fakta_text = "\n".join([f"- [{f[1]}] {f[2][:100]}" for f in fakta_minggu_ini[:20]])
    
    prompt = f"""Buat ringkasan mingguan yang SPESIFIK dan INFORMATIF.

{fakta_text}

Tulis dalam 3-4 kalimat Bahasa Indonesia yang natural. Sebutkan topik spesifik, aktivitas penting, dan fokus utama."""

    try:
        router = get_router()
        result = router.chat(
            messages=[{"role": "system", "content": "Kamu merangkum aktivitas mingguan."}, {"role": "user", "content": prompt}],
            task_type=TaskType.SUMMARIZE
        )
        return result["content"].strip()
    except:
        return "Gagal membuat ringkasan."


# ========== PROACTIVE ASSISTANT ==========

def check_proactive_triggers() -> List[Dict]:
    """Cek semua trigger proaktif."""
    from src.database import cek_proyek_mengendap, cek_deadline_mendekat, ambil_fakta_belum_reflected, simpan_alert, lihat_active_alerts
    
    for p in cek_proyek_mengendap(30):
        simpan_alert("stale_project", f"📌 Proyek '{p['content'][:80]}' sudah {p['days']} hari tidak dibahas.", "medium", p["id"])
    for d in cek_deadline_mendekat(14):
        simpan_alert("upcoming_deadline", f"⏰ Deadline: '{d['content'][:80]}' — perlu action segera.", "high", d["id"])
    unreflected = ambil_fakta_belum_reflected()
    if len(unreflected) >= 10:
        simpan_alert("insight_pending", f"💡 {len(unreflected)} fakta belum di-reflect.", "low", None)
    
    return lihat_active_alerts()


def generate_proactive_greeting() -> str:
    """Generate sapaan pagi dengan info proaktif."""
    from src.database import get_daily_stats, lihat_active_alerts
    import datetime
    
    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    stats = get_daily_stats(yesterday)
    alerts = lihat_active_alerts()
    
    hour = datetime.datetime.now().hour
    greeting = "Selamat pagi" if hour < 11 else "Selamat siang" if hour < 15 else "Selamat sore" if hour < 19 else "Selamat malam"
    
    parts = [f"{greeting}!"]
    if stats.get("new_facts", 0) > 0 or stats.get("new_insights", 0) > 0:
        parts.append(f"Kemarin: {stats['new_facts']} fakta, {stats['new_insights']} insight, {stats['chat_count']} chat.")
    high_alerts = [a for a in alerts if a["priority"] == "high"]
    if high_alerts:
        parts.append(f"⚠️ {len(high_alerts)} hal butuh perhatian.")
    
    return " ".join(parts)


def answer_task_query() -> str:
    """Jawab pertanyaan tugas."""
    from src.database import get_tasks_by_status
    
    active_tasks = get_tasks_by_status('active')
    if not active_tasks:
        return "Tidak ada tugas aktif. Semua sudah selesai! 🎉"
    
    tasks_by_cat = {}
    for t in active_tasks:
        cat = t[1]
        tasks_by_cat.setdefault(cat, []).append(t)
    
    parts = [f"Ada {len(active_tasks)} hal yang masih aktif:\n"]
    for cat, tasks in tasks_by_cat.items():
        parts.append(f"\n**{cat.upper()}** ({len(tasks)}):")
        for t in tasks[:5]:
            parts.append(f"- [#{t[0]}] {t[2][:100]}")
    
    return "\n".join(parts)


def generate_graph_summary(cluster_facts: List[str]) -> str:
    """Generate nama cluster."""
    if len(cluster_facts) < 2:
        return cluster_facts[0] if cluster_facts else "Cluster"
    
    prompt = f"""Beri nama singkat (2-4 kata) untuk kelompok fakta berikut:
{chr(10).join(cluster_facts)}
Nama:"""

    try:
        router = get_router()
        result = router.chat(
            messages=[{"role": "system", "content": "Jawab HANYA 2-4 kata."}, {"role": "user", "content": prompt}],
            task_type=TaskType.SUMMARIZE
        )
        return result["content"].strip()
    except:
        return "Topik Terkait"