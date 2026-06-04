"""
Saki AI Module
Semua fungsi AI: chat, ringkas, ekstrak, reflection, merge
"""

import ollama
import json
import re
import logging
from typing import Optional, List, Tuple, Dict

logger = logging.getLogger("saki")

# ========== KONFIGURASI ==========
MODEL = "qwen3:4b"
NAMA_AI = "Saki"
AUTO_EXTRACT_THRESHOLD = 0.75
SUMMARY_MAX_LENGTH = 4000
MIN_CONFIDENCE_THRESHOLD = 0.5
MIN_IMPORTANCE_FOR_TRACKING = 5

# Import database functions
from saki_database import (
    lihat_semua_fakta, lihat_fakta_by_id, simpan_fakta, simpan_reflection,
    hapus_fakta, cek_fakta_duplikat, track_access, tandai_fakta_reflected,
    ambil_fakta_belum_reflected, get_facts_for_timeline
)

# ========== SYSTEM PROMPT ==========
SYSTEM_PROMPT = f"""Kamu adalah asisten AI pribadi bernama {NAMA_AI}.
Kamu membantu merangkum dokumen, menjawab pertanyaan, dan mengingat informasi penting.
Kamu menjawab dalam Bahasa Indonesia yang natural, hangat, dan langsung ke inti.
Saat merangkum, gunakan format:
## Ringkasan
[3-5 poin utama]

## Kata Kunci
[keyword1, keyword2, keyword3]"""

# ========== FUNGSI AI DASAR ==========
def ringkas_teks(teks: str) -> str:
    """Meringkas teks panjang."""
    try:
        response = ollama.chat(model=MODEL, messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Ringkas teks berikut:\n\n{teks}"}
        ])
        return response["message"]["content"]
    except Exception as e:
        logger.error(f"Summarization failed: {str(e)}", exc_info=True)
        return f"Maaf, gagal meringkas: {type(e).__name__}"

def chat_saki(pesan: str, riwayat_chat: List[Dict] = None) -> str:
    """Chat dengan Saki, termasuk konteks fakta."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Tambah fakta sebagai konteks
    fakta = lihat_semua_fakta()
    if fakta:
        fakta_text = "\n".join([f"- [{f[1]}] {f[2]}" for f in fakta if f[4] >= MIN_CONFIDENCE_THRESHOLD])
        if fakta_text:
            messages.append({"role": "system", "content": f"Info tentang user:\n{fakta_text}"})
        # Track akses
        for f in fakta:
            if f[5] >= MIN_IMPORTANCE_FOR_TRACKING:
                track_access(f[0])
    
    # Tambah riwayat chat
    if riwayat_chat:
        for msg in riwayat_chat[-10:]:
            messages.append(msg)
    
    messages.append({"role": "user", "content": pesan})
    
    try:
        response = ollama.chat(model=MODEL, messages=messages)
        return response["message"]["content"]
    except Exception as e:
        logger.error(f"Chat failed: {str(e)}", exc_info=True)
        return f"Maaf, terjadi kesalahan: {type(e).__name__}"

# ========== AUTO-EXTRACTION ==========
def auto_ekstrak_fakta(pesan_user: str, riwayat_chat: List[Dict] = None) -> Optional[Dict]:
    """Ekstrak fakta penting dari pesan user."""
    if len(pesan_user.split()) < 3:
        return None
    
    konteks = ""
    if riwayat_chat and len(riwayat_chat) >= 2:
        last_msgs = riwayat_chat[-3:-1]
        konteks = "\n".join([f"{m['role']}: {m['content'][:200]}" for m in last_msgs])
    
    prompt = f"""Analisis pesan berikut. Apakah mengandung FAKTA PENTING TENTANG USER yang bersifat PERMANEN?

KRITERIA FAKTA PENTING (harus dicatat):
- Proyek yang sedang dikerjakan (bukan sekadar "nanti mau bikin")
- Skill atau kemampuan ("Saya bisa Python")
- Pekerjaan atau pendidikan ("Saya mahasiswa TI semester 5")
- Preferensi KUAT yang konsisten ("Saya tidak suka kopi pahit")
- Kontak atau identitas penting
- Deadline atau target serius

BUKAN FAKTA PENTING (abaikan):
- Obrolan ringan atau candaan
- Kebutuhan sesaat ("Saya butuh beli pulsa")
- Rencana belum pasti ("Saya kepikiran mau belajar X")
- Info harga atau list belanja
- Pertanyaan atau permintaan tolong
- Opini tentang sesuatu yang bukan diri user

KONTEKS PERCAKAPAN (jika ada):
{konteks}

PESAN USER:
"{pesan_user}"

Jawab JSON saja:
{{"is_fact": true/false, "confidence": 0.0-1.0, "fact": "fakta ringkas", "category": "proyek/preferensi/kontak/jadwal/akun/skill/pekerjaan/pendidikan/umum"}}

Jika ragu, pilih false."""

    try:
        response = ollama.chat(model=MODEL, messages=[
            {"role": "system", "content": "Kamu adalah filter fakta yang KETAT. Jawab HANYA JSON."},
            {"role": "user", "content": prompt}
        ])
        hasil = response["message"]["content"].strip()
        if hasil.startswith("```"):
            hasil = hasil.split("\n", 1)[1].rstrip("```")
        hasil = hasil.strip()
        
        data = json.loads(hasil)
        
        if data.get("is_fact") and data.get("confidence", 0) >= AUTO_EXTRACT_THRESHOLD:
            return {
                "fact": data["fact"],
                "category": data.get("category", "umum"),
                "confidence": data["confidence"]
            }
        return None
    except Exception as e:
        logger.error(f"Auto-extract failed: {type(e).__name__}: {str(e)}", exc_info=True)
        return None

# ========== IMPORTANCE RATING ==========
def auto_rate_importance(content: str, category: str) -> int:
    """AI menilai importance dari sebuah fakta (1-10)."""
    prompt = f"""Nilai seberapa PENTING fakta ini untuk diingat. HANYA beri angka 1-10.

PEDOMAN SKOR:
10 = Identitas, password, info kritis
8-9 = Proyek aktif, deadline, kontak penting
6-7 = Skill, pekerjaan, pendidikan
4-5 = Preferensi, hobi yang serius
1-3 = Hobi ringan, info umum, obrolan

FAKTA: "{content}"
KATEGORI: {category}

Jawab HANYA satu angka. Contoh: 8"""

    try:
        response = ollama.chat(model=MODEL, messages=[
            {"role": "system", "content": "Jawab HANYA satu angka 1-10."},
            {"role": "user", "content": prompt}
        ])
        hasil = response["message"]["content"].strip()
        
        match = re.search(r'\b(10|[1-9])\b', hasil)
        if match:
            score = int(match.group(1))
            logger.debug(f"Auto-rated importance: {score}/10 for '{content[:50]}...'")
            return score
        
        fallback = {"akun": 10, "proyek": 8, "jadwal": 7, "kontak": 7,
                    "pekerjaan": 7, "skill": 6, "pendidikan": 6,
                    "preferensi": 4, "umum": 5}
        return fallback.get(category, 5)
    except Exception as e:
        logger.error(f"Auto-rate importance failed: {str(e)}", exc_info=True)
        return 5

# ========== MERGE ==========
def merge_fakta_dengan_ai(fakta_list: List[Tuple]) -> str:
    """Gabungkan beberapa fakta dengan AI."""
    if not fakta_list:
        return "Tidak ada fakta untuk digabung."
    
    fakta_text = "\n".join([f"- {f[2]}" for f in fakta_list])
    logger.info(f"Merging {len(fakta_list)} facts: {[f[0] for f in fakta_list]}")
    
    prompt = f"""Gabungkan fakta-fakta berikut menjadi satu fakta yang padat dan koheren.
Jangan ada informasi yang hilang. Hilangkan pengulangan.
Output hanya fakta gabungannya saja, tanpa penjelasan.

{fakta_text}

Hasil gabungan:"""
    
    try:
        response = ollama.chat(model=MODEL, messages=[{"role": "user", "content": prompt}])
        hasil = response["message"]["content"].strip()
        logger.info(f"Merge result: {hasil[:100]}...")
        return hasil
    except Exception as e:
        logger.error(f"Merge failed: {str(e)}", exc_info=True)
        return f"[Gagal menggabungkan: {type(e).__name__}]"

# ========== DUPLICATE DETECTION ==========
def deteksi_duplikat_semantik() -> List[Dict]:
    """Deteksi fakta duplikat dengan AI."""
    fakta = lihat_semua_fakta()
    if len(fakta) < 2:
        return []
    
    fakta_list = "\n".join([f"- [#{f[0]}] [{f[1]}] {f[2]}" for f in fakta])
    
    prompt = f"""Analisis daftar fakta berikut. Temukan pasangan yang kemungkinan duplikat.
{fakta_list}

Jawab JSON array: [{{"id1": 1, "id2": 2, "reason": "...", "suggestion": "..."}}]
Jika tidak ada, jawab []."""

    try:
        response = ollama.chat(model=MODEL, messages=[
            {"role": "system", "content": "Jawab HANYA JSON array."},
            {"role": "user", "content": prompt}
        ])
        raw = response["message"]["content"].strip()
        
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rstrip("```")
        
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed
        except:
            pass
        
        m = re.search(r"(\[.*\])", raw, re.S)
        if m:
            try:
                parsed = json.loads(m.group(1))
                if isinstance(parsed, list):
                    return parsed
            except:
                pass
        
        logger.info("Duplicate detection: no valid results")
        return []
    except Exception as e:
        logger.error(f"Duplicate detection failed: {str(e)}", exc_info=True)
        return []

# ========== REFLECTION (V5) ==========
def generate_reflection() -> Tuple[List[Dict], str]:
    """Analisis fakta, hasilkan insight."""
    fakta = ambil_fakta_belum_reflected()
    
    if len(fakta) < 3:
        return [], f"Butuh minimal 3 fakta baru. Saat ini: {len(fakta)}"
    
    logger.info(f"Generating reflection for {len(fakta)} unreflected facts")
    
    fakta_text = "\n".join([f"[#{f[0]}] [{f[1]}] {f[2]}" for f in fakta])
    
    prompt = f"""Analisis fakta-fakta berikut. HANYA kelompokkan yang BENAR-BENAR terkait secara makna.

{fakta_text}

ATURAN KETAT:
1. Dua fakta bisa dikelompokkan jika membahas TOPIK YANG SAMA PERSIS
2. "Saya suka kopi" dan "Saya butuh mesin kopi" → BOLEH digabung
3. "Saya suka kopi" dan "Saya suka anime" → JANGAN digabung
4. Insight harus LEBIH INFORMATIF dari sekadar menggabung
5. Fakta yang tidak bisa dikelompokkan, ABAIKAN

Output JSON array:
[{{"title": "Judul", "content": "Isi insight", "source_ids": [1,3], "category": "proyek/pembelajaran/preferensi/umum"}}]
Jika tidak ada, jawab []."""

    try:
        response = ollama.chat(model=MODEL, messages=[
            {"role": "system", "content": "Kamu sistem analisis pengetahuan. Jawab HANYA JSON array."},
            {"role": "user", "content": prompt}
        ])
        raw = response["message"]["content"].strip()
        logger.debug(f"Reflection raw: {raw[:300]}")
        
        if raw.startswith("```"):
            parts = raw.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("["):
                    raw = part
                    break
        
        insights = json.loads(raw)
        
        if not isinstance(insights, list):
            return [], "AI tidak mengembalikan format yang valid."
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

# ========== TIMELINE (V5.5) ==========
def generate_timeline() -> List[Dict]:
    """Generate timeline 3 level: bulan → minggu → hari."""
    from saki_database import get_all_timeline_data
    from collections import defaultdict
    import datetime
    import calendar
    
    data = get_all_timeline_data()
    all_facts = data["facts"]
    all_reflections = data["reflections"]
    all_chats = data["chats"]
    
    if not all_facts and not all_reflections and not all_chats:
        return []
    
    # Organize data by date
    daily_data = defaultdict(lambda: {"facts": [], "insights": [], "chat_count": 0})
    
    for f in all_facts:
        try:
            dt = datetime.datetime.strptime(f[3], "%Y-%m-%d %H:%M:%S")
            date_key = dt.strftime("%Y-%m-%d")
            daily_data[date_key]["facts"].append({
                "id": f[0], "category": f[1], "content": f[2]
            })
        except:
            continue
    
    for r in all_reflections:
        try:
            dt = datetime.datetime.strptime(r[4], "%Y-%m-%d %H:%M:%S")
            date_key = dt.strftime("%Y-%m-%d")
            daily_data[date_key]["insights"].append({
                "id": r[0], "title": r[1], "content": r[2], "category": r[3]
            })
        except:
            continue
    
    for c in all_chats:
        try:
            date_key = c[0]  # Already a date string
            daily_data[date_key]["chat_count"] = c[1]
        except:
            continue
    
    # Group into weeks and months
    months = defaultdict(lambda: {"weeks": defaultdict(lambda: {"days": {}}), "total_items": 0})
    
    for date_str in sorted(daily_data.keys()):
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        month_key = dt.strftime("%Y-%m")
        month_name = dt.strftime("%B %Y")
        
        # Calculate week number within month
        first_day = dt.replace(day=1)
        week_num = ((dt - first_day).days // 7) + 1
        week_label = f"Minggu {week_num}"
        
        day_data = daily_data[date_str]
        items_count = len(day_data["facts"]) + len(day_data["insights"]) + (1 if day_data["chat_count"] > 0 else 0)
        
        months[month_key]["name"] = month_name
        months[month_key]["year"] = dt.year
        months[month_key]["month_num"] = dt.month
        months[month_key]["total_items"] += items_count
        months[month_key]["weeks"][week_label]["days"][dt.day] = {
            "date": date_str,
            "day_name": dt.strftime("%A"),
            **day_data
        }
    
    # Build result structure
    result = []
    for month_key in sorted(months.keys()):
        month_data = months[month_key]
        
        # Build weeks list
        weeks_list = []
        for week_label in sorted(month_data["weeks"].keys()):
            week_data = month_data["weeks"][week_label]
            days_list = []
            for day_num in sorted(week_data["days"].keys()):
                days_list.append(week_data["days"][day_num])
            
            weeks_list.append({
                "label": week_label,
                "days": days_list,
                "total_items": sum(
                    len(d["facts"]) + len(d["insights"]) + (1 if d["chat_count"] > 0 else 0)
                    for d in days_list
                )
            })
        
        result.append({
            "year": month_data["year"],
            "month": month_data["name"].split()[0],
            "month_name": month_data["name"],
            "total_items": month_data["total_items"],
            "summary": None,  # Will be filled by AI later
            "weeks": weeks_list
        })
    
    return result


def generate_timeline_summary(month_name: str, items: List[Dict]) -> str:
    """Generate AI summary untuk satu bulan."""
    if not items:
        return "Tidak ada aktivitas."
    
    # Build context from items
    facts_text = []
    insights_text = []
    
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
Fokus ke topik utama dan perkembangan penting.

{context}

Ringkasan:"""

    try:
        response = ollama.chat(model=MODEL, messages=[
            {"role": "system", "content": "Kamu adalah asisten yang merangkum aktivitas bulanan. Jawab dalam 1-2 kalimat Bahasa Indonesia yang natural."},
            {"role": "user", "content": prompt}
        ])
        return response["message"]["content"].strip()
    except Exception as e:
        logger.error(f"Timeline summary failed: {str(e)}", exc_info=True)
        return f"Bulan ini: {len(facts_text)} fakta, {len(insights_text)} insight."