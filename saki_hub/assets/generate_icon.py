"""
Generate Icons untuk Saki Hub
Jalankan sekali untuk generate icon.ico, icon.png
"""

from pathlib import Path

def create_icon_pillow():
    """Generate icon pakai Pillow."""
    try:
        from PIL import Image, ImageDraw
        
        size = 256
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Background circle (ungu gradient simpel)
        margin = 20
        draw.ellipse(
            [margin, margin, size - margin, size - margin],
            fill=(124, 58, 237, 255)  # #7C3AED
        )
        
        # Inner circle
        inner_margin = 50
        draw.ellipse(
            [inner_margin, inner_margin, size - inner_margin, size - inner_margin],
            fill=(30, 30, 46, 255)  # #1E1E2E
        )
        
        # "S" text-like shape (pakai lines)
        draw.text((size // 3, size // 3), "S", fill=(255, 255, 255, 255))
        
        # Simpan
        assets_path = Path(__file__).parent
        assets_path.mkdir(parents=True, exist_ok=True)
        
        # PNG
        img.save(assets_path / "icon.png")
        
        # ICO (multi-size)
        icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        img.save(assets_path / "icon.ico", format="ICO", sizes=icon_sizes)
        
        # Yellow version (warning)
        yellow = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        yellow_draw = ImageDraw.Draw(yellow)
        yellow_draw.ellipse([margin, margin, size-margin, size-margin], fill=(245, 158, 11, 255))
        yellow_draw.ellipse([inner_margin, inner_margin, size-inner_margin, size-inner_margin], fill=(30, 30, 46, 255))
        yellow.save(assets_path / "icon_yellow.png")
        yellow.save(assets_path / "icon_yellow.ico", format="ICO", sizes=icon_sizes)
        
        # Red version (error)
        red = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        red_draw = ImageDraw.Draw(red)
        red_draw.ellipse([margin, margin, size-margin, size-margin], fill=(239, 68, 68, 255))
        red_draw.ellipse([inner_margin, inner_margin, size-inner_margin, size-inner_margin], fill=(30, 30, 46, 255))
        red.save(assets_path / "icon_red.png")
        red.save(assets_path / "icon_red.ico", format="ICO", sizes=icon_sizes)
        
        print(f"✅ Icons generated in: {assets_path}")
        print(f"   icon.ico, icon.png (green/purple)")
        print(f"   icon_yellow.ico (warning)")
        print(f"   icon_red.ico (error)")
        return True
        
    except ImportError:
        print("❌ Pillow not installed. Run: pip install Pillow")
        return False


def create_simple_icon():
    """Fallback: Buat icon .ico minimal pakai built-in."""
    import struct
    import io
    
    assets_path = Path(__file__).parent
    assets_path.mkdir(parents=True, exist_ok=True)
    
    # Simple 1-pixel ICO (transparent)
    # Ini akan di-override kalau Pillow tersedia
    
    print("⚠️  Install Pillow untuk icon yang lebih baik: pip install Pillow")
    print(f"   Assets folder: {assets_path}")
    print(f"   Qt akan pakai default icon kalau .ico tidak ditemukan")


if __name__ == "__main__":
    print("=" * 50)
    print("Saki Hub — Icon Generator")
    print("=" * 50)
    
    if not create_icon_pillow():
        create_simple_icon()
    
    print("\nDone!")