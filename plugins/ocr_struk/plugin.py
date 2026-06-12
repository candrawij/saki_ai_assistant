"""OCR Struk Plugin (Placeholder)"""
from plugins.base import BasePlugin

class Plugin(BasePlugin):
    @property
    def name(self): return "ocr_struk"
    @property
    def description(self): return "Ekstrak data dari struk belanja"
    @property
    def version(self): return "0.1.0"
    @property
    def icon(self): return "📄"
    
    def on_enable(self) -> bool: return True
    def on_disable(self): pass
    
    def get_commands(self) -> list:
        return [
            {"name": "ocr_scan", "description": "Scan struk belanja", "keywords": ["struk", "ocr", "scan struk", "baca struk"], "handler": "scan"},
        ]
    
    def execute(self, command: str, args=None) -> str:
        return "📄 OCR Struk — coming soon.\nFitur: foto struk → data otomatis tercatat."