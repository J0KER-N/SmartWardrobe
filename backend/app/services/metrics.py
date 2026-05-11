from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_METRICS_PATH = Path(__file__).resolve().parents[2] / "data" / "metrics.log"


def _ensure_parent() -> None:
    _METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)


def log_event(event_name: str, user_id: Optional[int] = None, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """记录一条轻量事件日志。"""
    event = {
        "event": event_name,
        "user_id": user_id,
        "payload": payload or {},
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    _ensure_parent()
    with _METRICS_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=False) + "\n")
    logger.info("metrics event recorded: %s", event_name)
    return event


def log_recommendation_show(user_id: int, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return log_event("recommendation_show", user_id=user_id, payload=payload)


def log_recommendation_accept(user_id: int, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return log_event("recommendation_accept", user_id=user_id, payload=payload)


def log_tryon_request(user_id: int, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return log_event("tryon_request", user_id=user_id, payload=payload)


def read_metrics(limit: int = 100) -> list[Dict[str, Any]]:
    """读取最近的指标事件，便于测试与调试。"""
    if not _METRICS_PATH.exists():
        return []

    with _METRICS_PATH.open("r", encoding="utf-8") as file:
        lines = [line.strip() for line in file if line.strip()]

    events: list[Dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events