"""
Filesystem Skills — Fokus ke E:\Priv Bot\data\
"""
import os
from pathlib import Path
from datetime import datetime

KNOWN_PATHS = {
    "data": "E:\\Priv Bot\\data",
    "documents": "E:\\Priv Bot\\data\\documents",
    "dokumen": "E:\\Priv Bot\\data\\documents",
    "notes": "E:\\Priv Bot\\data\\notes",
    "catatan": "E:\\Priv Bot\\data\\notes",
    "tasks": "E:\\Priv Bot\\data\\tasks",
    "tugas": "E:\\Priv Bot\\data\\tasks",
    "projects": "E:\\Priv Bot\\data\\projects",
    "proyek": "E:\\Priv Bot\\data\\projects",
    "ringkasan": "E:\\Priv Bot\\data\\ringkasan",
    "backups": "E:\\Priv Bot\\data\\backups",
    "backup": "E:\\Priv Bot\\data\\backups",
    "screenshots": "E:\\Priv Bot\\data\\screenshots",
    "screenshot": "E:\\Priv Bot\\data\\screenshots",
    "saki": "E:\\Priv Bot",
    "priv bot": "E:\\Priv Bot",
    "downloads": str(Path.home() / "Downloads"),
    "download": str(Path.home() / "Downloads"),
    "desktop": str(Path.home() / "Desktop"),
}

def resolve_path(name: str):
    name_lower = name.lower().strip()
    for key, path in KNOWN_PATHS.items():
        if key in name_lower or name_lower == key:
            resolved = Path(path)
            if str(resolved).startswith("E:\\Priv Bot\\data\\"):
                resolved.mkdir(parents=True, exist_ok=True)
            if resolved.exists():
                return str(resolved)
    if os.path.exists(name):
        return name
    data_path = Path("E:\\Priv Bot\\data") / name
    if data_path.exists():
        return str(data_path)
    return None

def buka_folder(path: str):
    resolved = resolve_path(path)
    if resolved and os.path.isdir(resolved):
        os.startfile(resolved)
        return True, f"Folder dibuka: {resolved}"
    if os.path.isdir(path):
        os.startfile(path)
        return True, f"Folder dibuka: {path}"
    return False, f"Folder '{path}' tidak ditemukan. Coba: buka folder data"

def buka_file(path: str):
    resolved = resolve_path(path)
    if resolved and os.path.isfile(resolved):
        os.startfile(resolved)
        return True, f"File dibuka: {resolved}"
    docs = Path("E:\\Priv Bot\\data\\documents") / path
    if docs.is_file():
        os.startfile(str(docs))
        return True, f"File dibuka: {docs}"
    if os.path.isfile(path):
        os.startfile(path)
        return True, f"File dibuka: {path}"
    return False, f"File '{path}' tidak ditemukan"

def cari_file(nama: str, folder: str = None):
    search_path = folder if folder else "E:\\Priv Bot"
    results = []
    try:
        for root, dirs, files in os.walk(search_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for file in files:
                if nama.lower() in file.lower():
                    results.append(os.path.join(root, file))
            if len(results) >= 10:
                break
    except PermissionError:
        pass
    return results

def list_folder(path: str):
    resolved = resolve_path(path)
    target = resolved if resolved else path
    if not os.path.isdir(target):
        return False, []
    items = []
    try:
        for item in os.listdir(target):
            full = os.path.join(target, item)
            stat = os.stat(full)
            items.append({
                "nama": item,
                "tipe": "folder" if os.path.isdir(full) else "file",
                "ukuran_mb": round(stat.st_size / (1024*1024), 1) if not os.path.isdir(full) else 0,
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
            })
    except PermissionError:
        pass
    items.sort(key=lambda x: (x["tipe"] != "folder", x["nama"].lower()))
    return True, items

def ringkas_folder(path: str):
    success, items = list_folder(path)
    if not success:
        return False, f"Folder '{path}' tidak ditemukan"
    if not items:
        return True, f"Folder kosong"
    total_files = sum(1 for i in items if i["tipe"] == "file")
    total_folders = sum(1 for i in items if i["tipe"] == "folder")
    total_size = sum(i["ukuran_mb"] for i in items)
    resp = f"{total_folders} folder, {total_files} file"
    if total_size > 0:
        resp += f" ({total_size:.1f} MB)"
    resp += "\n"
    for i in items[:15]:
        icon = "📁" if i["tipe"] == "folder" else "📄"
        resp += f"  {icon} {i['nama']}"
        if i["ukuran_mb"] > 0:
            resp += f" ({i['ukuran_mb']} MB)"
        resp += "\n"
    if len(items) > 15:
        resp += f"  ... dan {len(items)-15} lainnya"
    return True, resp