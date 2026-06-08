"""
Filesystem Skills — Privacy-First, fokus ke E:\PrivBot\data\
"""

import os
from pathlib import Path
from datetime import datetime

# === PATH MAPPING ===
# Path internal Saki (auto-managed)
SAKI_DATA_PATHS = {
    "data": "E:\\PrivBot\\data",
    "documents": "E:\\PrivBot\\data\\documents",
    "dokumen": "E:\\PrivBot\\data\\documents",
    "notes": "E:\\PrivBot\\data\\notes",
    "catatan": "E:\\PrivBot\\data\\notes",
    "tasks": "E:\\PrivBot\\data\\tasks",
    "tugas": "E:\\PrivBot\\data\\tasks",
    "projects": "E:\\PrivBot\\data\\projects",
    "proyek": "E:\\PrivBot\\data\\projects",
    "ringkasan": "E:\\PrivBot\\data\\ringkasan",
    "backups": "E:\\PrivBot\\data\\backups",
    "backup": "E:\\PrivBot\\data\\backups",
    "screenshots": "E:\\PrivBot\\data\\screenshots",
    "screenshot": "E:\\PrivBot\\data\\screenshots",
    "saki": "E:\\PrivBot",
    "PrivBot": "E:\\PrivBot",
}

# ✅ TAMBAHAN: Path eksternal yang dikenal (read-only mindset)
KNOWN_EXTERNAL_PATHS = {
    "downloads": str(Path.home() / "Downloads"),
    "download": str(Path.home() / "Downloads"),
    "desktop": str(Path.home() / "Desktop"),
    "documents": str(Path.home() / "Documents"),
    "music": str(Path.home() / "Music"),
    "musik": str(Path.home() / "Music"),
    "pictures": str(Path.home() / "Pictures"),
    "gambar": str(Path.home() / "Pictures"),
    "videos": str(Path.home() / "Videos"),
    "video": str(Path.home() / "Videos"),
}

def resolve_path(name: str):
    """
    Resolve path dari nama.
    Priority: Saki data paths > External known paths > Absolute path > Relative di data/
    """
    name_lower = name.lower().strip()
    
    # 1. Cek Saki data paths
    for key, path in SAKI_DATA_PATHS.items():
        if key in name_lower or name_lower == key:
            resolved = Path(path)
            # Auto-create folder di dalam data/
            if str(resolved).startswith("E:\\PrivBot\\data\\"):
                resolved.mkdir(parents=True, exist_ok=True)
            if resolved.exists():
                return str(resolved)
    
    # 2. Cek external known paths
    for key, path in KNOWN_EXTERNAL_PATHS.items():
        if key in name_lower or name_lower == key:
            resolved = Path(path)
            if resolved.exists():
                return str(resolved)
    
    # 3. Cek absolute path
    if os.path.isabs(name) and os.path.exists(name):
        return name
    
    # 4. Cek relative di E:\PrivBot\data\
    data_path = Path("E:\\PrivBot\\data") / name
    if data_path.exists():
        return str(data_path)
    
    # 5. ✅ TAMBAHAN: Search di E:\ (limited depth)
    matched = _search_filesystem(name)
    if matched:
        return matched
    
    return None

def _search_filesystem(name: str, max_depth: int = 3) -> str | None:
    """
    Cari file/folder di filesystem dengan batasan depth.
    Hanya untuk path yang TIDAK ditemukan di mapping.
    """
    name_lower = name.lower()
    search_roots = ["E:\\", str(Path.home())]
    
    for root in search_roots:
        if not os.path.exists(root):
            continue
        try:
            for root_dir, dirs, files in os.walk(root):
                depth = root_dir.replace(root, "").count(os.sep)
                if depth > max_depth:
                    dirs.clear()
                    continue
                
                # Cek folder
                for d in dirs:
                    if name_lower in d.lower():
                        found = os.path.join(root_dir, d)
                        # ⚠️ Security: jangan buka system folders
                        if not _is_system_path(found):
                            return found
                
                # Cek file
                for f in files:
                    if name_lower in f.lower():
                        found = os.path.join(root_dir, f)
                        if not _is_system_path(found):
                            return found
                
                # Limit search
                if len(files) > 100:
                    dirs.clear()
        except (PermissionError, OSError):
            continue
    
    return None

def _is_system_path(path: str) -> bool:
    """Cegah akses ke folder sistem."""
    dangerous = ["\\Windows\\", "\\System32\\", "\\Program Files\\", "\\ProgramData\\"]
    return any(d in path for d in dangerous)

def buka_folder(path: str):
    """Buka folder di Explorer."""
    resolved = resolve_path(path)
    if resolved and os.path.isdir(resolved):
        os.startfile(resolved)
        return True, f"📂 Folder dibuka: {resolved}"
    if os.path.isdir(path):
        os.startfile(path)
        return True, f"📂 Folder dibuka: {path}"
    return False, f"❌ Folder '{path}' tidak ditemukan. Coba: buka folder data"

def buka_file(path: str):
    """Buka file dengan aplikasi default."""
    resolved = resolve_path(path)
    if resolved and os.path.isfile(resolved):
        os.startfile(resolved)
        return True, f"📄 File dibuka: {resolved}"
    # Cek di documents Saki
    docs = Path("E:\\PrivBot\\data\\documents") / path
    if docs.is_file():
        os.startfile(str(docs))
        return True, f"📄 File dibuka: {docs}"
    if os.path.isfile(path):
        os.startfile(path)
        return True, f"📄 File dibuka: {path}"
    return False, f"❌ File '{path}' tidak ditemukan"

def cari_file(nama: str, folder: str = None):
    """Cari file berdasarkan nama."""
    search_path = folder if folder else "E:\\PrivBot"
    results = []
    
    try:
        for root, dirs, files in os.walk(search_path):
            # Skip hidden/cache folders
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__' and d != 'venv']
            
            for file in files:
                if nama.lower() in file.lower():
                    full_path = os.path.join(root, file)
                    if not _is_system_path(full_path):
                        results.append(full_path)
            
            if len(results) >= 20:
                break
            
            # Limit depth
            depth = root.replace(search_path, "").count(os.sep)
            if depth > 5:
                dirs.clear()
    except PermissionError:
        pass
    
    return results

def list_folder(path: str):
    """List isi folder."""
    resolved = resolve_path(path)
    target = resolved if resolved else path
    
    if not os.path.isdir(target):
        return False, []
    
    items = []
    try:
        for item in sorted(os.listdir(target)):
            full = os.path.join(target, item)
            try:
                stat = os.stat(full)
                items.append({
                    "nama": item,
                    "tipe": "folder" if os.path.isdir(full) else "file",
                    "ukuran_mb": round(stat.st_size / (1024 * 1024), 1) if not os.path.isdir(full) else 0,
                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                })
            except OSError:
                continue
    except PermissionError:
        return False, []
    
    # Sort: folders first, then by name
    items.sort(key=lambda x: (x["tipe"] != "folder", x["nama"].lower()))
    return True, items

def ringkas_folder(path: str):
    """Ringkas isi folder (count + size)."""
    success, items = list_folder(path)
    if not success:
        return False, f"❌ Folder '{path}' tidak ditemukan"
    if not items:
        return True, "📂 Folder kosong"
    
    total_files = sum(1 for i in items if i["tipe"] == "file")
    total_folders = sum(1 for i in items if i["tipe"] == "folder")
    total_size = sum(i["ukuran_mb"] for i in items)
    
    resp = f"📂 {total_folders} folder, {total_files} file"
    if total_size > 0:
        if total_size > 1000:
            resp += f" ({total_size / 1000:.1f} GB)"
        else:
            resp += f" ({total_size:.1f} MB)"
    resp += "\n"
    
    for i in items[:15]:
        icon = "📁" if i["tipe"] == "folder" else "📄"
        resp += f"  {icon} {i['nama']}"
        if i["ukuran_mb"] > 0:
            resp += f" ({i['ukuran_mb']} MB)"
        resp += "\n"
    
    if len(items) > 15:
        resp += f"  ... dan {len(items) - 15} item lainnya"
    
    return True, resp