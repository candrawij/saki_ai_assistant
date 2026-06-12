"""
Model Router — Arahkan task ke model yang tepat
Ringan → Qwen 2.5 (cepat) | Berat → Qwen 3 (reasoning)
"""

import ollama
import time
import logging
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger("saki.router")


class TaskType(Enum):
    """Kategori task berdasarkan kompleksitas."""
    GREETING = "greeting"         # Sapaan ringan
    CHAT = "chat"                 # Percakapan umum
    AGENT = "agent"               # Perintah agent (buka, catat, task)
    KNOWLEDGE = "knowledge"       # Tanya jawab pengetahuan
    SUMMARIZE = "summarize"       # Ringkas teks
    EXTRACT = "extract"           # Ekstrak fakta
    REFLECTION = "reflection"     # Generate insight
    MERGE = "merge"               # Gabung fakta
    RELATIONSHIP = "relationship" # Analisis hubungan


class ModelRouter:
    """
    Route task ke model yang optimal.
    
    Models:
    - qwen2.5:3b → Fast (chat, agent, greeting)
    - qwen3:4b   → Reasoning (reflection, extract, merge)
    """
    
    def __init__(self):
        # Konfigurasi model
        self.models = {
            "fast": "qwen2.5:3b",
            "reasoning": "qwen3:4b",
        }
        
        # Mapping task → model
        self.routing = {
            TaskType.GREETING: "fast",
            TaskType.CHAT: "fast",
            TaskType.AGENT: "fast",
            TaskType.KNOWLEDGE: "fast",
            TaskType.SUMMARIZE: "fast",
            TaskType.EXTRACT: "fast",
            TaskType.REFLECTION: "reasoning",
            TaskType.MERGE: "reasoning",
            TaskType.RELATIONSHIP: "reasoning",
        }
        
        # Cache untuk model availability check
        self._model_cache = {}
        self._cache_time = 0
        self._cache_ttl = 300  # 5 menit
    
    def classify_task(self, message: str, context: str = "") -> TaskType:
        """
        Klasifikasi task berdasarkan isi pesan.
        
        Args:
            message: Pesan user
            context: Konteks tambahan (agent name, dll)
        
        Returns:
            TaskType
        """
        msg = message.lower().strip()
        
        # Greeting patterns
        greetings = ["halo", "hai", "hi", "pagi", "siang", "sore", "malam",
                     "apa kabar", "selamat", "assalamualaikum", "hey"]
        if any(msg == g or msg.startswith(g) for g in greetings):
            return TaskType.GREETING
        
        # Agent commands (dari context)
        if context and context in ["file", "note", "task", "project"]:
            return TaskType.AGENT
        
        # Agent keywords
        agent_kw = ["buka folder", "buka file", "catat:", "task:", "list task",
                    "progress", "screenshot", "info sistem", "cmd:"]
        if any(kw in msg for kw in agent_kw):
            return TaskType.AGENT
        
        # Summarize
        if any(kw in msg for kw in ["ringkas", "summary", "rangkum", "ringkasan"]):
            return TaskType.SUMMARIZE
        
        # Default: chat
        return TaskType.CHAT
    
    def get_model(self, task_type: TaskType) -> str:
        """
        Dapatkan model yang tepat untuk task.
        
        Args:
            task_type: Tipe task
        
        Returns:
            Nama model (qwen2.5:3b atau qwen3:4b)
        """
        tier = self.routing.get(task_type, "fast")
        return self.models[tier]
    
    def chat(
        self,
        messages: List[Dict],
        task_type: TaskType = TaskType.CHAT,
        timeout: int = 60,
    ) -> Dict:
        """
        Chat dengan model yang tepat.
        
        Args:
            messages: List pesan [{role, content}]
            task_type: Tipe task
            timeout: Timeout dalam detik
        
        Returns:
            Response dari model
        """
        model = self.get_model(task_type)
        
        logger.info(f"Routing: {task_type.value} -> {model}")
        
        start_time = time.time()
        
        try:
            response = ollama.chat(
                model=model,
                messages=messages,
                options={"temperature": 0.7}
            )
            
            elapsed = time.time() - start_time
            response_text = response["message"]["content"]
            tokens = len(response_text.split()) * 1.3
            
            logger.info(
                f"Model {model}: {tokens:.0f} tokens in {elapsed:.1f}s "
                f"({tokens/elapsed:.1f} TPS)"
            )
            
            return {
                "content": response_text,
                "model": model,
                "elapsed": elapsed,
                "tokens": tokens,
                "tps": tokens / elapsed if elapsed > 0 else 0,
            }
        
        except Exception as e:
            logger.error(f"Model {model} failed: {e}")
            
            # Fallback ke model satunya
            fallback = self.models["fast"] if model == self.models["reasoning"] else self.models["reasoning"]
            logger.warning(f"Fallback to {fallback}")
            
            try:
                response = ollama.chat(
                    model=fallback,
                    messages=messages,
                )
                elapsed = time.time() - start_time
                
                return {
                    "content": response["message"]["content"],
                    "model": f"{fallback} (fallback)",
                    "elapsed": elapsed,
                    "tokens": 0,
                    "tps": 0,
                }
            except Exception as e2:
                logger.error(f"Fallback also failed: {e2}")
                return {
                    "content": f"Maaf, kedua model sedang tidak tersedia: {e2}",
                    "model": "none",
                    "elapsed": 0,
                    "tokens": 0,
                    "tps": 0,
                }
    
    def get_available_models(self) -> List[str]:
        """Cek model apa saja yang tersedia di Ollama."""
        now = time.time()
        
        # Pakai cache
        if self._model_cache and (now - self._cache_time) < self._cache_ttl:
            return list(self._model_cache.keys())
        
        try:
            result = ollama.list()
            models = [m["name"] for m in result.get("models", [])]
            
            # Update cache
            self._model_cache = {m: True for m in models}
            self._cache_time = now
            
            return models
        except:
            return list(self.models.values())
    
    def ensure_models_available(self) -> Dict[str, bool]:
        """
        Pastikan model yang dibutuhkan tersedia.
        Pull jika belum ada.
        """
        available = {}
        
        for tier, model in self.models.items():
            try:
                models = self.get_available_models()
                model_base = model.split(":")[0]
                
                # Cek apakah model ada (full name atau base name)
                found = any(model in m or m.startswith(model_base) for m in models)
                
                if not found:
                    logger.info(f"Pulling model: {model}")
                    ollama.pull(model)
                    available[tier] = True
                else:
                    available[tier] = True
            
            except Exception as e:
                logger.error(f"Failed to ensure model {model}: {e}")
                available[tier] = False
        
        return available
    
    def get_stats(self) -> Dict:
        """Statistik router."""
        return {
            "routing_table": {
                task.value: self.models[tier]
                for task, tier in self.routing.items()
            },
            "models": self.models,
            "available": self.get_available_models(),
        }