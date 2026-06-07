"""
Saki Core — Scheduler
APScheduler jobs untuk backup, reflection, cleanup
"""

import datetime
import shutil
import os
from pathlib import Path
import logging
from apscheduler.schedulers.background import BackgroundScheduler
import yaml

logger = logging.getLogger("saki.core.scheduler")

class SakiScheduler:
    def __init__(self, config_path="saki_core/config.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
        self.scheduler = BackgroundScheduler()
        self.root = Path(__file__).parent.parent
        self.data_folder = self.root / "data"
    
    def start(self):
        """Start scheduler dengan jobs dari config."""
        if not self.config.get("scheduler", {}).get("enabled"):
            logger.info("Scheduler disabled")
            return
        
        jobs = self.config.get("scheduler", {}).get("jobs", [])
        
        for job in jobs:
            if not job.get("enabled", True):
                continue
            
            task = getattr(self, job["task"], None)
            if task:
                self.scheduler.add_job(
                    task,
                    'cron',
                    hour=job["cron"].split()[1],
                    minute=job["cron"].split()[0],
                    id=job["name"],
                    name=job["name"]
                )
                logger.info(f"Scheduled: {job['name']} ({job['cron']})")
        
        self.scheduler.start()
        logger.info("Scheduler started")
    
    def stop(self):
        """Stop scheduler."""
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")
    
    def backup_database(self):
        """Backup database + ChromaDB."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_folder = self.data_folder / "backups" / timestamp
        backup_folder.mkdir(parents=True, exist_ok=True)
        
        # Backup SQLite
        db_path = self.data_folder / "saki_memory.db"
        if db_path.exists():
            shutil.copy2(db_path, backup_folder / "saki_memory.db")
        
        # Backup ChromaDB
        chroma_path = self.data_folder / "chroma_db"
        if chroma_path.exists():
            shutil.copytree(chroma_path, backup_folder / "chroma_db", dirs_exist_ok=True)
        
        # Hapus backup lama (>7 hari)
        cutoff = datetime.datetime.now() - datetime.timedelta(days=7)
        for old_backup in (self.data_folder / "backups").iterdir():
            if old_backup.is_dir():
                try:
                    dt = datetime.datetime.strptime(old_backup.name, "%Y%m%d_%H%M%S")
                    if dt < cutoff:
                        shutil.rmtree(old_backup)
                        logger.info(f"Deleted old backup: {old_backup.name}")
                except:
                    continue
        
        logger.info(f"Backup completed: {backup_folder}")
    
    def run_reflection(self):
        """Jalankan reflection otomatis."""
        sys.path.insert(0, str(self.root))
        try:
            from src.ai import generate_reflection, save_reflections
            insights, error = generate_reflection()
            if insights:
                saved = save_reflections(insights)
                logger.info(f"Weekly reflection: {saved} insights saved")
            else:
                logger.info(f"Weekly reflection: {error}")
        except Exception as e:
            logger.error(f"Weekly reflection failed: {str(e)}")
    
    def cleanup_temp_files(self):
        """Bersihkan file temporary."""
        temp_patterns = ["*.tmp", "*.temp", "~*"]
        for pattern in temp_patterns:
            for f in self.root.rglob(pattern):
                try:
                    f.unlink()
                    logger.debug(f"Cleaned: {f}")
                except:
                    pass
        logger.info("Temp cleanup completed")