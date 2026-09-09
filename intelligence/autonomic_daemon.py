# -*- coding: utf-8 -*-
"""
NEXA Living Intelligence & Autonomic Self-Governance Engine (AXE v3.0 Metacontrol)
Coldwell Banker CB VIP Ankara • Yiğit Narin

Responsibilities:
1. Continuous Market Sensing: Analyzes macro signals and news ingestion velocity to dynamically adjust market regime.
2. Self-Healing Watchdog: Identifies hanging research queue jobs, uncommitted pipelines, and dead-letter tasks.
3. Database Concurrency & Performance Caretaker: Enforces WAL checkpoints and prevents SQLite lock starvation.
4. System Vitality Index: Calculates a real-time 0-100 system intelligence and health score for observability.
"""

import os
import time
import json
import logging
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path

from intelligence.db import get_db_connection
from intelligence.market_state.engine import MarketStateEngine

logger = logging.getLogger("intelligence.autonomic_daemon")


class AutonomicSupervisor:
    """
    Autonomous governance and self-healing engine.
    Implements the Metacontrol Loop: SENSE -> ASSESS -> RECOVER -> OPTIMIZE -> REPORT.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AutonomicSupervisor, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.market_engine = MarketStateEngine()
        self._daemon_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_pulse_time: Optional[datetime] = None
        self._pulse_history: List[Dict[str, Any]] = []
        logger.info("AutonomicSupervisor initialized.")

    def maintain_database_health(self) -> Dict[str, Any]:
        """Runs non-blocking WAL checkpoints and integrity checks."""
        result = {
            "wal_checkpoint": "skipped",
            "integrity": "unknown",
            "active_tables": 0,
            "status": "ok"
        }
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("PRAGMA wal_checkpoint(PASSIVE);")
            ckpt = cur.fetchone()
            if ckpt:
                result["wal_checkpoint"] = f"busy={ckpt[0]}, log={ckpt[1]}, ckpt={ckpt[2]}"

            cur.execute("PRAGMA quick_check(1);")
            check_res = cur.fetchone()
            result["integrity"] = check_res[0] if check_res else "ok"

            cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
            t_count = cur.fetchone()
            result["active_tables"] = t_count[0] if t_count else 0
        except Exception as e:
            logger.error(f"Autonomic database maintenance error: {e}")
            result["status"] = "error"
            result["error"] = str(e)
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
        return result

    def recover_stale_tasks(self, timeout_minutes: int = 15) -> Dict[str, Any]:
        """
        Detects tasks that have been in 'processing' or 'running' for longer
        than timeout_minutes and transitions them to 'recovered_timeout'.
        """
        recovery_stats = {
            "stale_tasks_recovered": 0,
            "stale_pipeline_runs_closed": 0,
            "status": "ok"
        }
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            cutoff = (datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)).isoformat()
            cur.execute(
                """
                UPDATE research_queue 
                SET status = 'recovered_timeout' 
                WHERE status IN ('processing', 'running', 'in_progress') 
                  AND created_at < ?
                """,
                (cutoff,)
            )
            recovery_stats["stale_tasks_recovered"] = cur.rowcount

            cur.execute(
                """
                UPDATE intelligence_runs
                SET success = 0, ended_at = ?, errors_json = json_array('Recovered by Autonomic Watchdog timeout')
                WHERE ended_at IS NULL AND started_at < ?
                """,
                (datetime.now(timezone.utc).isoformat(), cutoff)
            )
            recovery_stats["stale_pipeline_runs_closed"] = cur.rowcount
            conn.commit()

            if recovery_stats["stale_tasks_recovered"] > 0 or recovery_stats["stale_pipeline_runs_closed"] > 0:
                logger.warning(
                    f"Autonomic Watchdog recovered {recovery_stats['stale_tasks_recovered']} stale tasks "
                    f"and closed {recovery_stats['stale_pipeline_runs_closed']} hanging runs."
                )
        except Exception as e:
            logger.error(f"Watchdog recovery error: {e}")
            recovery_stats["status"] = "error"
            recovery_stats["error"] = str(e)
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
        return recovery_stats

    def sense_market_shifts(self) -> Dict[str, Any]:
        """
        Extracts recent signals from published news_articles to keep the
        MarketState dynamic and aligned with current reality.
        """
        sense_summary = {
            "recent_articles_sensed": 0,
            "avg_confidence": 0.0,
            "active_regime": "STABLE",
            "status": "ok"
        }
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                """
                SELECT COUNT(*), AVG(confidence_score), AVG(quality_score)
                FROM news_articles
                WHERE status = 'published' OR status IS NULL OR status = ''
                """
            )
            row = cur.fetchone()
            if row and row[0]:
                sense_summary["recent_articles_sensed"] = row[0]
                sense_summary["avg_confidence"] = round(row[1] or 0.0, 3)
                sense_summary["avg_quality"] = round(row[2] or 0.0, 1)

            current_state = self.market_engine.get_current_state()
            if current_state:
                sense_summary["active_regime"] = getattr(current_state.regime, "value", str(current_state.regime))
                sense_summary["demand_index"] = current_state.demand
                sense_summary["price_momentum"] = current_state.price_pressure
        except Exception as e:
            logger.error(f"Market sensing error: {e}")
            sense_summary["status"] = "error"
            sense_summary["error"] = str(e)
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
        return sense_summary

    def calculate_vitality_score(
        self,
        db_health: Dict[str, Any],
        recovery_stats: Dict[str, Any],
        sensing: Dict[str, Any]
    ) -> float:
        """Computes an institutional vitality score (0-100) reflecting system self-governance."""
        score = 100.0
        if db_health.get("status") != "ok" or db_health.get("integrity") != "ok":
            score -= 30.0
        if recovery_stats.get("status") != "ok":
            score -= 15.0
        if recovery_stats.get("stale_tasks_recovered", 0) > 5:
            score -= 10.0
        if sensing.get("recent_articles_sensed", 0) == 0:
            score -= 10.0
        return max(20.0, min(100.0, round(score, 1)))

    def pulse(self) -> Dict[str, Any]:
        """Executes one complete metacontrol loop."""
        pulse_start = time.time()
        now = datetime.now(timezone.utc)
        self._last_pulse_time = now

        db_health = self.maintain_database_health()
        recoveries = self.recover_stale_tasks()
        sensing = self.sense_market_shifts()
        vitality = self.calculate_vitality_score(db_health, recoveries, sensing)

        duration_ms = round((time.time() - pulse_start) * 1000, 2)
        report = {
            "timestamp": now.isoformat(),
            "vitality_score": vitality,
            "duration_ms": duration_ms,
            "database_health": db_health,
            "recoveries": recoveries,
            "market_sensing": sensing,
            "status": "healthy" if vitality >= 80 else "degraded"
        }

        self._pulse_history.append(report)
        if len(self._pulse_history) > 20:
            self._pulse_history.pop(0)

        logger.info(f"Autonomic Pulse completed in {duration_ms}ms — Vitality: {vitality}/100")
        return report

    def start_background_loop(self, interval_seconds: int = 300):
        """Starts a non-blocking daemon thread running periodic pulses."""
        with self._lock:
            if self._daemon_thread is not None and self._daemon_thread.is_alive():
                logger.info("Autonomic background daemon already running.")
                return

            self._stop_event.clear()

            def _loop():
                logger.info(f"Autonomic Supervisor loop started with interval={interval_seconds}s")
                while not self._stop_event.is_set():
                    try:
                        self.pulse()
                    except Exception as err:
                        logger.error(f"Autonomic loop iteration exception: {err}")
                    for _ in range(interval_seconds):
                        if self._stop_event.is_set():
                            break
                        time.sleep(1)
                logger.info("Autonomic Supervisor loop stopped.")

            self._daemon_thread = threading.Thread(
                target=_loop,
                name="NEXA-AutonomicSupervisor",
                daemon=True
            )
            self._daemon_thread.start()

    def stop_background_loop(self):
        """Stops the background daemon gracefully."""
        self._stop_event.set()
        if self._daemon_thread and self._daemon_thread.is_alive():
            self._daemon_thread.join(timeout=2.0)
        logger.info("Autonomic background daemon stop requested.")

    def get_status_report(self) -> Dict[str, Any]:
        """Returns the latest status report for API and telemetry consumers."""
        latest = self._pulse_history[-1] if self._pulse_history else self.pulse()
        return {
            "daemon_running": self._daemon_thread is not None and self._daemon_thread.is_alive(),
            "last_pulse": self._last_pulse_time.isoformat() if self._last_pulse_time else None,
            "latest_report": latest,
            "history_count": len(self._pulse_history)
        }


_supervisor_instance: Optional[AutonomicSupervisor] = None

def get_supervisor() -> AutonomicSupervisor:
    global _supervisor_instance
    if _supervisor_instance is None:
        _supervisor_instance = AutonomicSupervisor()
    return _supervisor_instance
