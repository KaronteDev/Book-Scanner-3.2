
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scheduler.py — "cron" interno para ejecutar lotes de control de calidad.
Lee calidad_scheduler.json o geodocs_config.json para intervalos.
"""
import threading, time, json, sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
GLOBAL_DB = BASE_DIR / "data" / "geodocs.db"
CFG_PATH = BASE_DIR / "quality_scheduler.json"

DEFAULT_CFG = {"enabled": True, "interval_hours": 24, "max_pages_per_cycle": 500}

class QualityScheduler:
    def __init__(self):
        self.cfg = DEFAULT_CFG.copy()
        if CFG_PATH.exists():
            try:
                self.cfg.update(json.loads(CFG_PATH.read_text(encoding="utf-8")))
            except Exception:
                pass
        self._stop = threading.Event()
        self._th = None

    def start(self):
        if not self.cfg.get("enabled", True):
            return
        if self._th and self._th.is_alive():
            return
        self._th = threading.Thread(target=self._run, daemon=True)
        self._th.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        interval = max(1, int(self.cfg.get("interval_hours", 24))) * 3600
        while not self._stop.is_set():
            try:
                self._cycle()
            except Exception as ex:
                # write a minimal log
                pass
            # Sleep until next run or stop
            for _ in range(interval//5):
                if self._stop.is_set():
                    break
                time.sleep(5)

    def _cycle(self):
        # Import here to avoid heavy deps on import time
        from modules.quality_engine import set_env, run_quality_batch
        set_env(GLOBAL_DB, BASE_DIR)
        # Find a recent document or run globally limited
        with sqlite3.connect(GLOBAL_DB) as con:
            row = con.execute("SELECT id FROM document ORDER BY id DESC LIMIT 1").fetchone()
            doc_id = row[0] if row else None
        res = run_quality_batch(doc_id=doc_id, limit=self.cfg.get("max_pages_per_cycle", 500))
        # Persist a small status file
        status = {"last_run": time.time(), "result": res}
        (BASE_DIR/"quality_scheduler_status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")

SCHEDULER = QualityScheduler()
