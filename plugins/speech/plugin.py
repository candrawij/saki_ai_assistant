"""
Speech Recognition Plugin
Voice input untuk Saki
"""

import threading
from plugins.base import BasePlugin, PluginStatus


class Plugin(BasePlugin):
    """Plugin untuk speech recognition."""
    
    @property
    def name(self) -> str:
        return "speech_recognition"
    
    @property
    def description(self) -> str:
        return "Voice input menggunakan speech recognition"
    
    @property
    def version(self) -> str:
        return "0.1.0"
    
    @property
    def icon(self) -> str:
        return "🎤"
    
    def on_enable(self) -> bool:
        """Check dependencies — jangan gagal kalau gak ada mic."""
        try:
            import speech_recognition as sr
            self.recognizer = sr.Recognizer()
            self.is_listening = False
            
            # Cek mic — tapi jangan gagal
            try:
                self.microphone = sr.Microphone()
            except:
                self.microphone = None
                print("⚠️ No microphone detected. Speech recognition will use default.")
            
            return True
        except ImportError:
            print("SpeechRecognition not installed.")
            return False
        except Exception as e:
            print(f"Speech init error: {e}")
            return False
    
    def on_disable(self):
        """Stop listening."""
        self.is_listening = False
    
    def get_commands(self) -> list:
        return [
            {
                "name": "speech_start",
                "description": "Mulai mendengarkan suara",
                "keywords": ["dengarkan", "listen", "speech", "suara", "bicara"],
                "handler": "start_listening",
            },
            {
                "name": "speech_stop",
                "description": "Berhenti mendengarkan",
                "keywords": ["stop dengar", "berhenti dengar", "stop listen"],
                "handler": "stop_listening",
            },
        ]
    
    def execute(self, command: str, args=None) -> str:
        if command == "start_listening":
            return self._listen_once()
        elif command == "stop_listening":
            self.is_listening = False
            return "🛑 Berhenti mendengarkan."
        return "❓ Perintah tidak dikenal."
    
    def _listen_once(self) -> str:
        """Dengarkan satu kali."""
        try:
            import speech_recognition as sr
            
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                print("🎤 Mendengarkan...")
                
                try:
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                    text = self.recognizer.recognize_google(audio, language="id-ID")
                    return f"🎤 Terdengar: \"{text}\""
                except sr.WaitTimeoutError:
                    return "⏰ Tidak ada suara terdeteksi."
                except sr.UnknownValueError:
                    return "❓ Tidak bisa memahami suara."
                except sr.RequestError:
                    return "🌐 Gagal connect ke Google Speech (butuh internet)."
        
        except ImportError:
            return "📦 Install SpeechRecognition dulu: pip install SpeechRecognition pyaudio"
        except Exception as e:
            return f"❌ Error: {str(e)}"