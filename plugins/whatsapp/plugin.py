"""WhatsApp Bot Plugin - Auto reply & read messages"""
from plugins.base import BasePlugin
import threading
import time
import re
from datetime import datetime
import os
import json

class Plugin(BasePlugin):
    
    def __init__(self):
        super().__init__()
        self.driver = None
        self.is_running = False
        self.listener_thread = None
        self.config_file = "whatsapp_config.json"
        self.config = self._load_config()
        self.auto_reply_rules = []
        
    @property
    def name(self): return "whatsapp_bot"
    
    @property
    def description(self): return "Auto-reply, baca chat, balas pesan WhatsApp"
    
    @property
    def version(self): return "1.0.0"
    
    @property
    def icon(self): return "💬"
    
    # ========== CONFIG MANAGEMENT ==========
    def _load_config(self):
        """Load konfigurasi dari file"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {
            "target_number": None,
            "auto_reply_enabled": False,
            "default_reply": "🤖 Bot: Pesan diterima, akan dibalas nanti.",
            "monitored_chats": []
        }
    
    def _save_config(self):
        """Simpan konfigurasi ke file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    # ========== LIFECYCLE ==========
    def on_enable(self) -> bool:
        """Enable plugin - cek dependencies"""
        try:
            # Cek required packages
            import pywhatkit
            import selenium
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            print("✅ WhatsApp Bot dependencies OK")
            print("📌 Untuk membaca chat, perlu install Chrome & ChromeDriver")
            print("📌 Install: pip install pywhatkit selenium webdriver-manager")
            
            # Load auto-reply rules contoh
            self.auto_reply_rules = [
                {"keyword": "halo", "reply": "Halo juga! Ada yang bisa dibantu?"},
                {"keyword": "help", "reply": "Perintah: !status, !balas [pesan], !stop"},
                {"keyword": "!status", "reply": "Bot aktif ✅"},
            ]
            
            return True
            
        except ImportError as e:
            print(f"❌ Missing dependency: {e}")
            print("Jalankan: pip install pywhatkit selenium webdriver-manager")
            return False
    
    def on_disable(self):
        """Cleanup saat plugin di-disable"""
        self.stop_listener()
        if self.driver:
            self.driver.quit()
    
    # ========== WHATSAPP SENDER (pywhatkit) ==========
    def _send_whatsapp_message(self, phone_number: str, message: str) -> bool:
        """Kirim pesan WhatsApp menggunakan pywhatkit"""
        try:
            import pywhatkit
            now = datetime.now()
            # Kirim 2 menit dari sekarang (minimal waktu untuk scan QR)
            send_time = now.minute + 2
            
            if send_time >= 60:
                # Adjust hour if minute >= 60
                hour = (now.hour + 1) % 24
                minute = send_time - 60
            else:
                hour = now.hour
                minute = send_time
            
            pywhatkit.sendwhatmsg(
                phone_number, 
                message,
                hour, 
                minute,
                wait_time=15  # Wait 15 seconds before sending
            )
            return True
        except Exception as e:
            print(f"Send error: {e}")
            return False
    
    # ========== WHATSAPP LISTENER (Selenium) ==========
    def _init_driver(self):
        """Inisialisasi Chrome driver untuk WhatsApp Web"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service
            
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            # chrome_options.add_argument("--headless")  # Nonaktifkan jika ingin lihat window
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.get("https://web.whatsapp.com")
            print("📱 Scan QR Code WhatsApp Web dalam 30 detik...")
            time.sleep(30)  # Beri waktu scan QR
            return True
        except Exception as e:
            print(f"Driver init error: {e}")
            return False
    
    def _get_unread_messages(self):
        """Baca pesan yang belum dibaca"""
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            # Cari chat dengan notifikasi
            unread_chats = self.driver.find_elements(By.XPATH, "//div[contains(@class, '_akbu')]")
            messages = []
            
            for chat in unread_chats[:5]:  # Max 5 chat per loop
                try:
                    chat.click()
                    time.sleep(2)
                    
                    # Ambil pesan terakhir
                    last_msg = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'message-in')]//div[contains(@class, 'copyable-text')]"))
                    )
                    
                    sender_name = chat.find_element(By.XPATH, ".//span[@title]").get_attribute("title")
                    message_text = last_msg.text
                    
                    messages.append({
                        "sender": sender_name,
                        "message": message_text,
                        "timestamp": datetime.now()
                    })
                except:
                    continue
            
            return messages
            
        except Exception as e:
            print(f"Read error: {e}")
            return []
    
    def _auto_reply(self, message: str) -> str:
        """Generate auto-reply berdasarkan rules"""
        message_lower = message.lower()
        
        for rule in self.auto_reply_rules:
            if rule["keyword"].lower() in message_lower:
                return rule["reply"]
        
        if self.config.get("auto_reply_enabled", False):
            return self.config.get("default_reply", "Pesan diterima ✅")
        
        return None
    
    def _listen_loop(self):
        """Loop utama untuk listen WhatsApp"""
        print("🎧 WhatsApp listener started...")
        
        while self.is_running:
            try:
                if not self.driver:
                    if not self._init_driver():
                        time.sleep(30)
                        continue
                
                # Baca pesan baru
                messages = self._get_unread_messages()
                
                for msg in messages:
                    print(f"📩 From {msg['sender']}: {msg['message']}")
                    
                    # Auto reply
                    reply = self._auto_reply(msg['message'])
                    if reply:
                        print(f"🤖 Auto-reply: {reply}")
                        # Balas via pywhatkit (perlu nomor, ini limitation)
                        # Untuk demo, kita simpan ke log dulu
                        self._save_to_log(msg['sender'], msg['message'], reply)
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                print(f"Listener error: {e}")
                time.sleep(10)
    
    def _save_to_log(self, sender, message, reply):
        """Simpan chat ke file log"""
        log_file = "whatsapp_chat_log.txt"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] {sender}: {message}\n")
            f.write(f"[{datetime.now()}] BOT: {reply}\n")
            f.write("-" * 50 + "\n")
    
    def start_listener(self):
        """Start listener thread"""
        if not self.is_running:
            self.is_running = True
            self.listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.listener_thread.start()
            return "✅ WhatsApp listener started"
        return "⚠️ Listener already running"
    
    def stop_listener(self):
        """Stop listener thread"""
        self.is_running = False
        if self.driver:
            self.driver.quit()
            self.driver = None
        return "🛑 WhatsApp listener stopped"
    
    # ========== COMMAND HANDLERS ==========
    def _send_message_handler(self, text: str) -> str:
        """Kirim pesan WhatsApp"""
        # Format: "628123456789|Halo ini pesan"
        parts = text.split("|", 1)
        if len(parts) < 2:
            return "❌ Format: nomor|pesan\nContoh: 628123456789|Halo selamat pagi"
        
        phone, message = parts[0].strip(), parts[1].strip()
        
        # Clean phone number
        phone = re.sub(r'[^0-9]', '', phone)
        if not phone.startswith('62') and not phone.startswith('08'):
            return "❌ Nomor harus format Indonesia: 628xxx atau 08xxx"
        
        if phone.startswith('08'):
            phone = '62' + phone[1:]
        
        if self._send_whatsapp_message(phone, message):
            return f"✅ Pesan terkirim ke {phone}\n📝 Pesan: {message[:50]}..."
        return "❌ Gagal mengirim pesan"
    
    def _set_target_handler(self, text: str) -> str:
        """Set target nomor WhatsApp"""
        phone = re.sub(r'[^0-9]', '', text)
        if not phone:
            return "❌ Masukkan nomor WhatsApp\nContoh: set_target 628123456789"
        
        if phone.startswith('08'):
            phone = '62' + phone[1:]
        
        self.config["target_number"] = phone
        self._save_config()
        return f"✅ Target nomor diset: {phone}"
    
    def _status_handler(self) -> str:
        """Cek status bot"""
        status = f"""
📊 **Status WhatsApp Bot**
━━━━━━━━━━━━━━━━━━━━━
📱 Target nomor: {self.config.get('target_number', 'Belum diset')}
🤖 Auto-reply: {'✅ Aktif' if self.config.get('auto_reply_enabled') else '❌ Nonaktif'}
🎧 Listener: {'✅ Running' if self.is_running else '❌ Stopped'}
📝 Default reply: {self.config.get('default_reply', '-')}

**Perintah:**
• wa_send|Halo — Kirim pesan
• wa_set_target 628xxx — Set nomor target  
• wa_auto_reply on/off — Aktifkan auto-reply
• wa_listener start/stop — Start/stop listener
• wa_rules — Lihat rules auto-reply
        """
        return status.strip()
    
    def _auto_reply_toggle(self, text: str) -> str:
        """Toggle auto-reply"""
        if "on" in text.lower():
            self.config["auto_reply_enabled"] = True
            self._save_config()
            return "✅ Auto-reply diaktifkan"
        elif "off" in text.lower():
            self.config["auto_reply_enabled"] = False
            self._save_config()
            return "❌ Auto-reply dinonaktifkan"
        return f"Status auto-reply: {'ON' if self.config['auto_reply_enabled'] else 'OFF'}"
    
    def _listener_handler(self, text: str) -> str:
        """Control listener"""
        if "start" in text.lower():
            return self.start_listener()
        elif "stop" in text.lower():
            return self.stop_listener()
        return "Gunakan: wa_listener start/stop"
    
    def _add_rule_handler(self, text: str) -> str:
        """Tambah rule auto-reply"""
        # Format: keyword|reply
        parts = text.split("|", 1)
        if len(parts) < 2:
            return "❌ Format: kata_kunci|balasan\nContoh: assalamualaikum|Waalaikumsalam"
        
        keyword, reply = parts[0].strip(), parts[1].strip()
        self.auto_reply_rules.append({"keyword": keyword, "reply": reply})
        return f"✅ Rule ditambahkan: '{keyword}' → '{reply[:50]}'"
    
    def _show_rules_handler(self) -> str:
        """Tampilkan semua rules"""
        if not self.auto_reply_rules:
            return "📭 Belum ada rules auto-reply"
        
        rules_text = "📜 **Auto-reply Rules:**\n"
        for i, rule in enumerate(self.auto_reply_rules, 1):
            rules_text += f"{i}. '{rule['keyword']}' → {rule['reply'][:40]}\n"
        return rules_text
    
    # ========== COMMAND REGISTRATION ==========
    def get_commands(self) -> list:
        return [
            {
                "name": "wa_send",
                "description": "Kirim pesan WhatsApp (format: nomor|pesan)",
                "keywords": ["kirim wa", "whatsapp", "wa ke", "send wa"],
                "handler": "send_message"
            },
            {
                "name": "wa_set_target",
                "description": "Set nomor tujuan utama",
                "keywords": ["set target wa", "target wa", "set nomor wa"],
                "handler": "set_target"
            },
            {
                "name": "wa_status",
                "description": "Cek status bot WhatsApp",
                "keywords": ["status wa", "cek wa", "wa status"],
                "handler": "status"
            },
            {
                "name": "wa_auto_reply",
                "description": "Aktifkan/nonaktifkan auto-reply",
                "keywords": ["auto reply wa", "wa auto", "balas otomatis"],
                "handler": "auto_reply_toggle"
            },
            {
                "name": "wa_listener",
                "description": "Start/stop listener chat masuk",
                "keywords": ["listen wa", "baca wa", "wa listener"],
                "handler": "listener"
            },
            {
                "name": "wa_add_rule",
                "description": "Tambah rule auto-reply (keyword|balasan)",
                "keywords": ["tambah rule wa", "rule wa", "add rule"],
                "handler": "add_rule"
            },
            {
                "name": "wa_rules",
                "description": "Lihat semua auto-reply rules",
                "keywords": ["lihat rule wa", "rules wa", "daftar rule"],
                "handler": "show_rules"
            }
        ]
    
    def execute(self, command: str, args=None) -> str:
        """Eksekusi command"""
        if command == "send_message":
            return self._send_message_handler(args or "")
        elif command == "set_target":
            return self._set_target_handler(args or "")
        elif command == "status":
            return self._status_handler()
        elif command == "auto_reply_toggle":
            return self._auto_reply_toggle(args or "")
        elif command == "listener":
            return self._listener_handler(args or "")
        elif command == "add_rule":
            return self._add_rule_handler(args or "")
        elif command == "show_rules":
            return self._show_rules_handler()
        return "❓ Command tidak dikenal"