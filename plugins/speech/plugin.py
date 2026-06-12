"""
Speech Recognition Plugin
Voice input untuk Saki — dengan auto-routing ke Agent
"""

import threading

from streamlit import text
from plugins.base import BasePlugin, PluginStatus


class Plugin(BasePlugin):
    """Plugin untuk speech recognition."""
    
    @property
    def name(self) -> str:
        return "speech_recognition"
    
    @property
    def description(self) -> str:
        return "Voice input dengan auto-routing ke Agent"
    
    @property
    def version(self) -> str:
        return "0.2.0"
    
    @property
    def icon(self) -> str:
        return "🎤"
    
    def on_enable(self) -> bool:
        try:
            import speech_recognition as sr
            self.recognizer = sr.Recognizer()
            self.is_listening = False
            
            try:
                self.microphone = sr.Microphone()
            except:
                self.microphone = None
            
            return True
        except ImportError:
            return False
    
    def on_disable(self):
        self.is_listening = False
    
    def get_commands(self) -> list:
        return [
            {
                "name": "speech_start",
                "description": "Mulai mendengarkan suara dan proses perintah",
                "keywords": ["dengarkan", "listen", "speech", "suara", "bicara", "voice"],
                "handler": "listen_and_process",
            },
            {
                "name": "speech_stop",
                "description": "Berhenti mendengarkan",
                "keywords": ["stop dengar", "berhenti dengar", "stop listen"],
                "handler": "stop_listening",
            },
        ]
    
    def execute(self, command: str, args=None) -> str:
        if command == "listen_and_process":
            result_parts = []
            for part in self._listen_and_process():
                result_parts.append(part)
            return "\n".join(result_parts)
        elif command == "stop_listening":
            self.is_listening = False
            return "🛑 Berhenti mendengarkan."
        return "❓ Perintah tidak dikenal."
    
    def _listen_and_process(self):
        """Dengarkan dan proses dengan Agent Router."""
        try:
            import speech_recognition as sr
            
            mic = self.microphone or sr.Microphone()
            
            with mic as source:
                # Adjust noise
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                try:
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                    text = self.recognizer.recognize_google(audio, language="id-ID")
                    
                    yield f"🎤 **Terdengar:** \"{text}\""
                    yield ""
                    yield self._route_to_agent(text)
                    
                except sr.WaitTimeoutError:
                    yield "⏰ Tidak ada suara terdeteksi (5 detik)."
                except sr.UnknownValueError:
                    yield "❓ Tidak bisa memahami suara. Coba lagi dengan suara lebih jelas."
                except sr.RequestError:
                    yield "🌐 Butuh koneksi internet untuk Google Speech Recognition."
        
        except ImportError:
            yield "📦 Package belum terinstall. Run: `pip install SpeechRecognition pyaudio`"
        except Exception as e:
            yield f"❌ Error: {str(e)}"
    
    def _route_to_agent(self, text: str) -> str:
        """
        Auto-route hasil speech ke Agent atau Special Command.
        """
        try:
            from src.agents.router import AgentRouter
            router = AgentRouter()
            
            msg_lower = text.lower().strip()
            
            # ✅ Cek SPECIAL dulu (sebelum agent)
            special_keywords = [
                "screenshot", "tangkapan layar", "ss",
                "info sistem", "sistem info", "system info", "info komputer",
                "buka aplikasi", "open app",
                "cmd:", "run:",
            ]
            if any(kw in msg_lower for kw in special_keywords):
                return f"🤖 **Special**\n\n{router.execute_special(text)}"
            
            # ✅ Cek Agent
            agent, routed_message = router.route(text)
            if agent is not None:
                result = agent.execute(text)
                return f"🤖 **{agent.name}**\n\n{result}"
            
            # ✅ Bukan perintah — kirim sebagai chat ke AI
            try:
                from src.ai import chat_saki
                response = chat_saki(text, [])
                return f"💬 _{text}_\n\n{response}"
            except Exception as e:
                return f"💬 \"{text}\"\n\n Chat error: {str(e)}"
        
        except Exception as e:
            return f"⚠️ Gagal routing: {str(e)}"