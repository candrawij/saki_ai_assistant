"""
Saki Server - Streamlit UI
AI Pribadi v5.0 — Reflection Engine
"""

import streamlit as st
import datetime
import os
import json
import tempfile
import shutil
import logging
from pathlib import Path
from dotenv import load_dotenv
import ollama
import re

# Load environment
load_dotenv()

# Import modul Saki
from saki_database import (
    init_db, simpan_chat, simpan_fakta, lihat_semua_fakta, lihat_fakta_by_id,
    edit_fakta, hapus_fakta, cek_fakta_duplikat, update_importance,
    lihat_semua_reflections, lihat_reflection_by_id, hapus_reflection,
    edit_reflection, get_reflection_stats,
    lihat_semua_dokumen, lihat_dokumen_by_id, hapus_dokumen,
    simpan_dokumen, tambah_ke_chroma, cari_dokumen_semantik,
    init_chroma, get_db
)
from saki_ai import (
    NAMA_AI, MODEL, SYSTEM_PROMPT, SUMMARY_MAX_LENGTH,
    ringkas_teks, chat_saki, auto_ekstrak_fakta, auto_rate_importance,
    merge_fakta_dengan_ai, deteksi_duplikat_semantik,
    generate_reflection, save_reflections, generate_timeline
)
from saki_files import (
    ekstrak_teks_dari_pdf, ekstrak_teks_dari_docx, ekstrak_teks_dari_txt, proses_upload
)

# ========== SETUP LOGGING ==========

LOGS_FOLDER = Path(os.getenv("LOGS_FOLDER", "logs"))

def setup_logging():
    logger = logging.getLogger("saki")
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)
    log_dir = LOGS_FOLDER

    log_dir.mkdir(exist_ok=True)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "saki.log", maxBytes=10*1024*1024, backupCount=5)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'))
    
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / "saki_errors.log", maxBytes=5*1024*1024, backupCount=3)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_handler.formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    logger.propagate = False
    
    return logger

logger = setup_logging()

# ========== KONFIGURASI UI ==========
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "saki2024")

DATA_FOLDER = Path(os.getenv("DATA_FOLDER", "data"))
DOCUMENTS_FOLDER = str(DATA_FOLDER / os.getenv("DOCUMENTS_FOLDER", "documents"))
EXPORT_FOLDER = str(DATA_FOLDER / os.getenv("EXPORT_FOLDER", "exports"))
SAVE_FOLDER = str(DATA_FOLDER / os.getenv("SAVE_FOLDER", "ringkasan"))
CHROMA_FOLDER = str(DATA_FOLDER / os.getenv("CHROMA_FOLDER", "chroma_db"))

DAYS_UNUSED_WARNING = 30


st.set_page_config(page_title=f"{NAMA_AI} - AI Pribadi", page_icon="🤖", layout="wide")

# ========== AUTENTIKASI ==========
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

with st.sidebar:
    if not st.session_state.authenticated:
        st.title(f"🔐 Login {NAMA_AI}")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if password == ADMIN_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Password salah!")
        st.stop()
    else:
        st.title(f"🤖 {NAMA_AI} v5.0")
        st.caption("AI Pribadi — Reflection Engine")
        
        menu = st.radio("Menu", [
            "💬 Chat", "📝 Ringkasan", "📚 Memory", "📄 Dokumen",
            "🧠 Intelligence", "🧠 Reflection", "⚙️ Pengaturan"
        ])
        
        if st.button("🚪 Logout"):
            st.session_state.authenticated = False
            st.session_state.chat_history = []
            st.rerun()

# ========== HALAMAN UTAMA ==========
if st.session_state.authenticated:
    init_db()
    
    # Startup log sekali saja
    if "startup_logged" not in st.session_state:
        logger.info("=" * 50)
        logger.info(f"Saki v5.0 starting — Reflection Engine")
        logger.info(f"Model: {MODEL}")
        logger.info("=" * 50)
        st.session_state.startup_logged = True
    
    # ===== CHAT =====
    if menu == "💬 Chat":
        st.title("💬 Chat dengan Saki")
        st.caption("Saki otomatis mencatat fakta penting 🤖")
        
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
        
        if prompt := st.chat_input("Ketik pesan..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            simpan_chat("USER", prompt)
            
            with st.spinner("Berpikir..."):
                jawaban = chat_saki(prompt, st.session_state.chat_history)
                st.session_state.chat_history.append({"role": "assistant", "content": jawaban})
                simpan_chat(NAMA_AI.upper(), jawaban)
                
                hasil = auto_ekstrak_fakta(prompt, st.session_state.chat_history)
                if hasil:
                    existing = cek_fakta_duplikat(hasil["fact"])
                    if not existing:
                        importance = auto_rate_importance(hasil["fact"], hasil["category"])
                        success, error = simpan_fakta(hasil["category"], hasil["fact"], "auto", hasil["confidence"], importance)
                        if not success:
                            logger.warning(f"Auto-save failed: {error}")
            
            st.rerun()
    
    # ===== RINGKASAN =====
    elif menu == "📝 Ringkasan":
        st.title("📝 Ringkasan Teks")
        
        tab1, tab2 = st.tabs(["✏️ Paste Teks", "📤 Upload File"])
        
        with tab1:
            teks = st.text_area("Masukkan teks:", height=350, placeholder="Paste teks di sini...")
            if st.button("🔍 Ringkas", type="primary") and teks and teks.strip():
                with st.spinner(f"Meringkas... ({len(teks)} karakter)"):
                    hasil = ringkas_teks(teks)
                    st.markdown("### 📋 Hasil")
                    st.markdown(hasil)
                    
                    os.makedirs(SAVE_FOLDER, exist_ok=True)
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filepath = f"{SAVE_FOLDER}/ringkasan_{timestamp}.txt"
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(f"{hasil}\n\n=== TEKS ASLI ===\n{teks[:1000]}...")
                    st.success(f"💾 Tersimpan: `{filepath}`")
        
                with tab2:
                    st.subheader("📅 Timeline Aktivitas")
                    
                    # Level selector
                    view_level = st.radio(
                        "Tampilan:",
                        ["📅 Bulanan", "📆 Mingguan", "📋 Harian"],
                        horizontal=True
                    )
                    
                    timeline = generate_timeline()
                    
                    if not timeline:
                        st.info("Belum ada data timeline.")
                    else:
                        # BULANAN
                        if view_level == "📅 Bulanan":
                            for month_entry in timeline:
                                # Generate summary if not cached
                                if month_entry["summary"] is None and month_entry["total_items"] >= 3:
                                    with st.spinner(f"Meringkas {month_entry['month_name']}..."):
                                        month_entry["summary"] = generate_timeline_summary(
                                            month_entry["month_name"],
                                            month_entry["weeks"]
                                        )
                                
                                with st.expander(
                                    f"📅 {month_entry['month_name']} ({month_entry['total_items']} aktivitas)"
                                ):
                                    # AI Summary
                                    if month_entry["summary"]:
                                        st.info(f"💡 {month_entry['summary']}")
                                    
                                    # Highlight insights
                                    insights_this_month = []
                                    for week in month_entry["weeks"]:
                                        for day in week["days"]:
                                            for ins in day.get("insights", []):
                                                insights_this_month.append(ins)
                                    
                                    if insights_this_month:
                                        st.write("**🔍 Insight bulan ini:**")
                                        for ins in insights_this_month[:3]:
                                            st.write(f"- [{ins['category']}] {ins['title']}")
                                    
                                    # Per minggu
                                    st.write("**📆 Per Minggu:**")
                                    for week in month_entry["weeks"]:
                                        st.write(
                                            f"- {week['label']}: "
                                            f"{week['total_items']} aktivitas, "
                                            f"{len(week['days'])} hari aktif"
                                        )
                                    
                                    # Stats
                                    total_facts = sum(
                                        len(d["facts"]) 
                                        for w in month_entry["weeks"] 
                                        for d in w["days"]
                                    )
                                    total_insights = sum(
                                        len(d["insights"]) 
                                        for w in month_entry["weeks"] 
                                        for d in w["days"]
                                    )
                                    st.caption(f"📊 {total_facts} fakta | 💡 {total_insights} insight")
                        
                        # MINGGUAN
                        elif view_level == "📆 Mingguan":
                            all_weeks = []
                            for month_entry in timeline:
                                for week in month_entry["weeks"]:
                                    all_weeks.append({
                                        "label": f"{week['label']} - {month_entry['month_name']}",
                                        "data": week,
                                        "month": month_entry
                                    })
                            
                            for week_entry in all_weeks:
                                week = week_entry["data"]
                                if week["total_items"] > 0:
                                    with st.expander(
                                        f"📆 {week_entry['label']} ({week['total_items']} aktivitas)"
                                    ):
                                        for day in week["days"]:
                                            day_items = len(day["facts"]) + len(day["insights"])
                                            chat_info = f" | 💬 {day['chat_count']} chat" if day["chat_count"] > 0 else ""
                                            st.write(
                                                f"**{day['day_name']}, {day['date']}**: "
                                                f"{day_items} item{chat_info}"
                                            )
                                            
                                            for f in day["facts"]:
                                                st.write(f"  📝 [#{f['id']}] [{f['category']}] {f['content'][:80]}")
                                            for ins in day["insights"]:
                                                st.write(f"  💡 [#{ins['id']}] [{ins['category']}] {ins['title']}")
                        
                        # HARIAN
                        elif view_level == "📋 Harian":
                            # Build all days list
                            all_days = []
                            for month_entry in timeline:
                                for week in month_entry["weeks"]:
                                    for day in week["days"]:
                                        all_days.append({
                                            "date": day["date"],
                                            "day_name": day["day_name"],
                                            "data": day,
                                            "month": month_entry["month_name"]
                                        })
                            
                            # Sort by date descending
                            all_days.sort(key=lambda x: x["date"], reverse=True)
                            
                            # Show last 30 days
                            for day_entry in all_days[:30]:
                                day = day_entry["data"]
                                total = len(day["facts"]) + len(day["insights"]) + (1 if day["chat_count"] > 0 else 0)
                                
                                if total > 0:
                                    with st.expander(
                                        f"📋 {day_entry['day_name']}, {day_entry['date']} "
                                        f"({day_entry['month']}) — {total} item"
                                    ):
                                        if day["chat_count"] > 0:
                                            st.write(f"💬 {day['chat_count']} pesan chat")
                                        
                                        if day["facts"]:
                                            st.write("**📝 Fakta:**")
                                            for f in day["facts"]:
                                                st.write(f"- [#{f['id']}] [{f['category']}] {f['content'][:100]}")
                                        
                                        if day["insights"]:
                                            st.write("**💡 Insight:**")
                                            for ins in day["insights"]:
                                                st.write(f"- [#{ins['id']}] [{ins['category']}] {ins['title']}")
                                                st.write(f"  {ins['content'][:150]}")
    
    # ===== MEMORY =====
    elif menu == "📚 Memory":
        st.title("📚 Memory Control Center")
        
        fakta = lihat_semua_fakta()
        
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("Total", len(fakta))
        with col2: st.metric("Manual 👤", sum(1 for f in fakta if f[3] == "manual"))
        with col3: st.metric("Auto 🤖", sum(1 for f in fakta if f[3] == "auto"))
        
        st.divider()
        
        # Form catat fakta
        with st.form("catat_fakta", clear_on_submit=True):
            kategori = st.selectbox("Kategori", ["proyek", "preferensi", "kontak", "jadwal", "akun", "skill", "pekerjaan", "pendidikan", "umum"])
            fakta_text = st.text_area("Fakta:", height=100)
            if st.form_submit_button("📝 Catat"):
                if fakta_text and fakta_text.strip():
                    importance = auto_rate_importance(fakta_text, kategori)
                    success, error = simpan_fakta(kategori, fakta_text, "manual", 1.0, importance)
                    if success:
                        st.success(f"✅ Tersimpan (Importance: {importance}/10)")
                        st.rerun()
                    else:
                        st.error(f"❌ {error}")
        
        st.divider()
        
        filter_mode = st.selectbox("Filter", ["Semua", "Manual", "Auto"])
        if filter_mode == "Manual":
            fakta = [f for f in fakta if f[3] == "manual"]
        elif filter_mode == "Auto":
            fakta = [f for f in fakta if f[3] == "auto"]
        
        for f in fakta:
            source_icon = "🤖" if f[3] == "auto" else "👤"
            stars = "⭐" * min(f[5], 5)
            
            with st.expander(f"{source_icon} {stars} [#{f[0]}] [{f[1]}] {f[2][:80]}..."):
                st.write(f"**Isi:** {f[2]}")
                st.write(f"**Importance:** {f[5]}/10 | **Diakses:** {f[6]}x")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button(f"✏️ Edit #{f[0]}", key=f"edit_{f[0]}"):
                        st.session_state[f"edit_mode_{f[0]}"] = True
                with col_b:
                    if st.button(f"🗑️ Hapus #{f[0]}", key=f"hapus_{f[0]}"):
                        hapus_fakta(f[0])
                        st.rerun()
                
                if st.session_state.get(f"edit_mode_{f[0]}"):
                    baru = st.text_input("Edit:", value=f[2], key=f"input_{f[0]}")
                    if st.button("Simpan", key=f"save_{f[0]}"):
                        edit_fakta(f[0], baru)
                        st.session_state[f"edit_mode_{f[0]}"] = False
                        st.rerun()
    
    # ===== DOKUMEN =====
    elif menu == "📄 Dokumen":
        st.title("📄 Knowledge Base")
        
        tab1, tab2 = st.tabs(["Upload", "Daftar Dokumen"])
        
        with tab1:
            uploaded = st.file_uploader("Upload dokumen", type=["pdf", "docx", "txt", "md"], key="doc_upload")
            if uploaded and st.button("Upload"):
                with st.spinner("Memproses dokumen..."):
                    doc_id, ringkasan = proses_upload(uploaded)
                    if doc_id:
                        st.success(f"Berhasil! ID: #{doc_id}")
                        st.markdown(ringkasan)
                    else:
                        st.error(ringkasan)
        
        with tab2:
            docs = lihat_semua_dokumen()
            
            cari = st.text_input("🔍 Cari dokumen...")
            if cari:
                docs = [d for d in docs if cari.lower() in d[1].lower() or (d[3] and cari.lower() in d[3].lower())]
            
            for d in docs:
                with st.expander(f"📄 [#{d[0]}] {d[1]} ({d[2]})"):
                    st.write(f"**Upload:** {d[4]}")
                    if d[3]:
                        st.write("**Ringkasan:**")
                        st.write(d[3])
                    
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        if st.button(f"📖 Baca #{d[0]}", key=f"baca_{d[0]}"):
                            doc = lihat_dokumen_by_id(d[0])
                            if doc:
                                st.session_state[f"show_doc_{d[0]}"] = True
                    
                    with col_b:
                        pertanyaan = st.text_input("Tanya:", key=f"tanya_{d[0]}")
                        if st.button(f"❓ Tanya #{d[0]}", key=f"btn_tanya_{d[0]}"):
                            if pertanyaan:
                                doc = lihat_dokumen_by_id(d[0])
                                if doc:
                                    prompt = f"DOKUMEN: {doc[1]}\n\nISI:\n{doc[5][:3000]}\n\nPERTANYAAN: {pertanyaan}"
                                    response = ollama.chat(model=MODEL, messages=[
                                        {"role": "system", "content": "Jawab berdasarkan dokumen."},
                                        {"role": "user", "content": prompt}
                                    ])
                                    st.info(response["message"]["content"])
                    
                    with col_c:
                        if st.button(f"🗑️ Hapus #{d[0]}", key=f"hapusdoc_{d[0]}"):
                            try:
                                collection = init_chroma()
                                all_ids = collection.get()['ids']
                                ids_to_delete = [i for i in all_ids if i.startswith(f"{d[0]}_")]
                                if ids_to_delete:
                                    collection.delete(ids=ids_to_delete)
                            except Exception as e:
                                logger.error(f"Failed cleaning chroma entries for doc {d[0]}: {type(e).__name__}: {str(e)}", exc_info=True)
                            hapus_dokumen(d[0])
                            if os.path.exists(d[2]):
                                os.remove(d[2])
                            st.rerun()
                    
                    if st.session_state.get(f"show_doc_{d[0]}"):
                        doc = lihat_dokumen_by_id(d[0])
                        if doc:
                            st.text_area("Isi Dokumen:", doc[5], height=300)
                            if st.button("Tutup", key=f"close_{d[0]}"):
                                st.session_state[f"show_doc_{d[0]}"] = False
                                st.rerun()

    # ===== INTELLIGENCE =====
    elif menu == "🧠 Intelligence":
        st.title("🧠 Memory Intelligence")
        st.caption("Saki menganalisis kualitas dan kesehatan memory")
        
        fakta = lihat_semua_fakta()
        
        # === HEALTH DASHBOARD ===
        st.subheader("📊 Memory Health Dashboard")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Fakta", len(fakta))
        with col2:
            high_importance = sum(1 for f in fakta if f[5] >= 7)
            st.metric("🔥 High Importance (7+)", high_importance)
        with col3:
            low_importance = sum(1 for f in fakta if f[5] <= 3)
            st.metric("💤 Low Importance (≤3)", low_importance)
        with col4:
            never_accessed = sum(1 for f in fakta if f[6] == 0)
            st.metric("📭 Never Accessed", never_accessed)
        
        st.divider()
        
        # === PERINGATAN ===
        st.subheader("⚠️ Peringatan")
        
        # 1. Fakta yang BELUM PERNAH diakses (baru)
        never_accessed = [f for f in fakta if f[7] is None]
        if never_accessed:
            with st.expander(f"🆕 {len(never_accessed)} fakta baru (belum pernah diakses)"):
                st.caption("Fakta-fakta ini baru dibuat dan belum pernah digunakan dalam percakapan.")
                for f in never_accessed[:10]:
                    st.write(f"- [#{f[0]}] {f[2][:100]}")
        
        # 2. Fakta yang SUDAH LAMA tidak diakses (> 30 hari)
        now = datetime.datetime.now()
        old_unused = []
        for f in fakta:
            if f[7] is not None:
                try:
                    last_access = datetime.datetime.strptime(f[7], "%Y-%m-%d %H:%M:%S")
                    days_since = (now - last_access).days
                    if days_since > DAYS_UNUSED_WARNING:
                        old_unused.append((f, days_since))
                except Exception:
                    pass
        
        if old_unused:
            with st.expander(f"💤 {len(old_unused)} fakta tidak diakses > {DAYS_UNUSED_WARNING} hari"):
                for f, days in old_unused[:10]:
                    st.write(f"- [#{f[0]}] {f[2][:100]} ({days} hari)")
        
        # 3. Fakta dengan importance rendah
        low_importance = [f for f in fakta if f[5] <= 3]
        if len(low_importance) > len(fakta) * 0.3 and len(fakta) > 5:
            st.warning(f"⚠️ {len(low_importance)} fakta memiliki importance rendah (≤3). Pertimbangkan untuk membersihkan.")
        
        st.divider()
        
        # === DUPLICATE DETECTION ===
        st.subheader("🔍 Duplicate Detection")
        
        if "duplicate_results" not in st.session_state:
            st.session_state.duplicate_results = None
        if "merge_message" not in st.session_state:
            st.session_state.merge_message = None
        
        if st.button("🔎 Cari Duplikat (AI Analysis)"):
            with st.spinner("Menganalisis kemiripan fakta..."):
                st.session_state.duplicate_results = deteksi_duplikat_semantik()
                st.session_state.merge_message = None
            st.rerun()
        
        if st.session_state.duplicate_results is not None:
            duplikat = st.session_state.duplicate_results
            if not duplikat:
                st.success("✅ Tidak ada duplikat terdeteksi!")
            else:
                st.info(f"Ditemukan {len(duplikat)} potensi duplikat:")
                for i, d in enumerate(duplikat):
                    with st.container():
                        st.warning(f"**#{d['id1']}** ↔ **#{d['id2']}**")
                        st.write(f"Alasan: {d.get('reason', 'Tidak ada alasan')}")
                        st.write(f"Saran: {d.get('suggestion', 'Merge jika sama')}")
                        with st.form(key=f"merge_form_{d['id1']}_{d['id2']}_{i}"):
                            submitted = st.form_submit_button(f"🔗 Merge #{d['id1']} + #{d['id2']}", use_container_width=True)
                            if submitted:
                                logger.info(f"User clicked merge: {d['id1']} + {d['id2']}")
                                f1 = lihat_fakta_by_id(d['id1'])
                                f2 = lihat_fakta_by_id(d['id2'])
                                if not f1:
                                    st.session_state.merge_message = f"❌ Fakta #{d['id1']} tidak ditemukan."
                                    logger.error(f"Merge failed: fact {d['id1']} not found")
                                elif not f2:
                                    st.session_state.merge_message = f"❌ Fakta #{d['id2']} tidak ditemukan."
                                    logger.error(f"Merge failed: fact {d['id2']} not found")
                                else:
                                    logger.info(f"Merging: [{f1[1]}] {f1[2][:50]} + [{f2[1]}] {f2[2][:50]}")
                                    hasil = merge_fakta_dengan_ai([f1, f2])
                                    if isinstance(hasil, str) and hasil.startswith("[Gagal"):
                                        st.session_state.merge_message = f"❌ {hasil}"
                                        logger.error(f"Merge AI failed: {hasil}")
                                    else:
                                        kategori = f1[1]
                                        imp1 = f1[5] if len(f1) > 5 else 5
                                        imp2 = f2[5] if len(f2) > 5 else 5
                                        new_importance = max(imp1, imp2)
                                        logger.info(f"Saving merged fact: [{kategori}] {hasil[:50]}... (imp={new_importance})")
                                        success, error = simpan_fakta(kategori, hasil, "manual", 1.0, new_importance)
                                        if success:
                                            hapus_fakta(d['id1'])
                                            hapus_fakta(d['id2'])
                                            logger.info(f"Merge complete: {d['id1']} + {d['id2']} -> new fact saved")
                                            st.session_state.merge_message = f"✅ Berhasil merge! Fakta #{d['id1']} + #{d['id2']} digabung."
                                            st.session_state.duplicate_results = None
                                        else:
                                            logger.error(f"Merge save failed: {error}")
                                            st.session_state.merge_message = f"❌ Gagal menyimpan: {error}"
                                st.rerun()
                        st.divider()
        
        if st.session_state.merge_message:
            if "✅" in st.session_state.merge_message:
                st.success(st.session_state.merge_message)
            else:
                st.error(st.session_state.merge_message)
            if st.button("OK"):
                st.session_state.merge_message = None
                st.rerun()

        st.divider()

        # === FAKTA TERURUT IMPORTANCE ===
        st.subheader("📋 Fakta Berdasarkan Importance")
        
        sort_by = st.selectbox("Urutkan", ["Importance (tinggi ke rendah)", "Akses terbanyak", "Terbaru", "Terlama tidak diakses"])
        
        if sort_by == "Importance (tinggi ke rendah)":
            sorted_facts = sorted(fakta, key=lambda x: x[5], reverse=True)
        elif sort_by == "Akses terbanyak":
            sorted_facts = sorted(fakta, key=lambda x: x[6], reverse=True)
        elif sort_by == "Terbaru":
            sorted_facts = sorted(fakta, key=lambda x: x[8], reverse=True)
        else:
            sorted_facts = sorted(fakta, key=lambda x: x[7] if x[7] else "2000-01-01")
        
        for f in sorted_facts[:30]:
            importance_bar = "█" * f[5] + "░" * (10 - f[5])
            
            with st.expander(f"⭐ {f[5]}/10 | [#{f[0]}] [{f[1]}] {f[2][:80]}..."):
                st.write(f"**Konten:** {f[2]}")
                st.write(f"**Kategori:** {f[1]}")
                st.write(f"**Importance:** {importance_bar} ({f[5]}/10)")
                st.write(f"**Diakses:** {f[6]} kali")
                st.write(f"**Terakhir diakses:** {f[7] if f[7] else 'Belum pernah'}")
                st.write(f"**Dibuat:** {f[8]}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    new_score = st.slider("Importance", 1, 10, f[5], key=f"imp_{f[0]}")
                    if new_score != f[5]:
                        if st.button(f"Update #{f[0]}", key=f"upd_{f[0]}"):
                            update_importance(f[0], new_score)
                            st.rerun()
                with col2:
                    if st.button(f"✏️ Edit #{f[0]}", key=f"edit_intel_{f[0]}"):
                        st.session_state[f"edit_intel_{f[0]}"] = True
                with col3:
                    if st.button(f"🗑️ Hapus #{f[0]}", key=f"hapus_intel_{f[0]}"):
                        hapus_fakta(f[0])
                        st.rerun()
                
                if st.session_state.get(f"edit_intel_{f[0]}"):
                    baru = st.text_area("Edit:", value=f[2], key=f"input_intel_{f[0]}")
                    if st.button("Simpan", key=f"save_intel_{f[0]}"):
                        edit_fakta(f[0], baru)
                        try:
                            with get_db() as conn:
                                c = conn.cursor()
                                c.execute("UPDATE facts SET source = 'manual', confidence = 1.0 WHERE id = ?", (f[0],))
                                conn.commit()
                        except Exception as e:
                            logger.error(f"Failed to update metadata for fact {f[0]}: {str(e)}", exc_info=True)
                        st.session_state[f"edit_intel_{f[0]}"] = False
                        st.rerun()
    
    # ===== REFLECTION =====
    elif menu == "🧠 Reflection":
        st.title("🧠 Reflection Engine")
        
        stats = get_reflection_stats()
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("💡 Insight", stats["total_reflections"])
        with col2: st.metric("📝 Belum Di-reflect", stats["unreflected_facts"])
        with col3: st.metric("✅ Sudah Di-reflect", stats["reflected_facts"])
        
        st.divider()
        
        # Generate
        if st.button("🧠 Generate Reflection", type="primary"):
            with st.spinner("Menganalisis fakta..."):
                insights, error = generate_reflection()
                if error:
                    st.warning(error)
                elif insights:
                    saved = save_reflections(insights)
                    st.success(f"✅ {saved} insight disimpan!")
                    st.rerun()
                else:
                    st.info("Tidak ada insight yang bisa dibuat.")
        
        st.divider()
        
        # Timeline tab
        tab1, tab2 = st.tabs(["💡 Insights", "📅 Timeline"])
        
        with tab1:
            reflections = lihat_semua_reflections()
            if not reflections:
                st.info("Belum ada insight.")
            else:
                for r in reflections:
                    try:
                        source_ids = json.loads(r[3]) if isinstance(r[3], str) else r[3]
                        source_text = ", ".join([f"#{s}" for s in source_ids])
                    except:
                        source_text = str(r[3])
                    
                    with st.expander(f"⭐ [{r[4]}] {r[1]} (dari {source_text})"):
                        st.write(r[2])
                        st.write(f"📅 {r[6]}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button(f"✏️ Edit #{r[0]}", key=f"edit_ref_{r[0]}"):
                                st.session_state[f"edit_ref_{r[0]}"] = True
                        with col2:
                            if st.button(f"🗑️ Hapus #{r[0]}", key=f"hapus_ref_{r[0]}"):
                                hapus_reflection(r[0])
                                st.rerun()
                        
                        if st.session_state.get(f"edit_ref_{r[0]}"):
                            with st.form(key=f"edit_ref_form_{r[0]}"):
                                new_title = st.text_input("Judul:", value=r[1])
                                new_content = st.text_area("Insight:", value=r[2], height=150)
                                if st.form_submit_button("Simpan"):
                                    edit_reflection(r[0], new_title, new_content)
                                    st.session_state[f"edit_ref_{r[0]}"] = False
                                    st.rerun()
        
        with tab2:
            st.subheader("📅 Timeline Fakta")
            timeline = generate_timeline()
            
            if not timeline:
                st.info("Belum ada data timeline.")
            else:
                for entry in timeline:
                    with st.expander(f"📅 {entry['month']} ({entry['count']} fakta)"):
                        for f in entry['facts']:
                            st.write(f"- [#{f['id']}] [{f['category']}] {f['content']}")
    
    # ===== PENGATURAN =====
    elif menu == "⚙️ Pengaturan":
        st.title("⚙️ Pengaturan")
        
        st.subheader("📊 Status Server")
        
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**Model AI:** {MODEL}")
            st.info(f"**Database:** data/saki_memory.db")
        with col2:
            st.info(f"**Dokumen:** data/documents/")
            st.info(f"**ChromaDB:** data/{os.getenv('CHROMA_FOLDER', 'chroma_db')}/")

        
        st.divider()
        
        st.subheader("📤 Ekspor Memory")
        if st.button("Ekspor ke JSON"):
            fakta = lihat_semua_fakta()
            if fakta:
                os.makedirs(EXPORT_FOLDER, exist_ok=True)
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                
                json_data = []
                for f in fakta:
                    json_data.append({
                        "id": f[0],
                        "category": f[1],
                        "content": f[2],
                        "source": f[3],
                        "confidence": f[4],
                        "importance": f[5],
                        "access_count": f[6],
                        "last_accessed": f[7],
                        "created_at": f[8]
                    })
                
                json_path = f"{EXPORT_FOLDER}/memory_{timestamp}.json"
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(json_data, f, indent=2, ensure_ascii=False)
                
                st.success(f"✅ Ekspor berhasil: `{json_path}`")
                st.download_button(
                    "📥 Download JSON",
                    json.dumps(json_data, indent=2, ensure_ascii=False),
                    f"memory_{timestamp}.json",
                    "application/json"
                )
            else:
                st.warning("Tidak ada fakta untuk diekspor.")
        
        st.divider()
        
        st.subheader("📥 Impor Memory")
        st.caption("Upload file JSON hasil ekspor sebelumnya.")
        
        imported_file = st.file_uploader("Upload file JSON", type=["json"], key="import_json")
        if imported_file and st.button("📥 Impor"):
            try:
                data = json.loads(imported_file.read())
                imported = 0
                skipped = 0
                
                for item in data:
                    content = item.get("content", "")
                    category = item.get("category", "umum")
                    
                    existing = cek_fakta_duplikat(content)
                    if existing:
                        skipped += 1
                        continue
                    
                    # Auto-rate importance
                    try:
                        importance = auto_rate_importance(content, category)
                    except Exception:
                        importance = 5
                    
                    success, error = simpan_fakta(
                        category=category,
                        content=content,
                        source=item.get("source", "imported"),
                        confidence=item.get("confidence", 1.0),
                        importance=importance
                    )
                    
                    if success:
                        imported += 1
                    else:
                        skipped += 1
                        logger.warning(f"Import skipped: {error}")
                
                st.success(f"✅ Impor selesai: {imported} baru, {skipped} dilewati")
                
            except json.JSONDecodeError:
                st.error("❌ File bukan JSON yang valid.")
                logger.error("Import failed: invalid JSON")
            except Exception as e:
                st.error(f"❌ Gagal impor: {type(e).__name__}")
                logger.error(f"Import failed: {str(e)}", exc_info=True)
        
        st.divider()
        
        st.subheader("📊 Statistik")
        
        fakta = lihat_semua_fakta()
        docs = lihat_semua_dokumen()
        reflections = lihat_semua_reflections()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Fakta", len(fakta))
        with col2:
            st.metric("Dokumen", len(docs))
        with col3:
            st.metric("Insight", len(reflections))
        
        st.divider()
        st.caption(f"🤖 {NAMA_AI} v5.0 — Reflection Engine | Streamlit + Ollama")
        
# ========== FOOTER ==========
st.sidebar.divider()
st.sidebar.caption(f"🤖 {NAMA_AI} v5.0 — Reflection Engine")