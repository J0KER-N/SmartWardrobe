from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..models import Feedback, Garment, TryonRecord, User


def increment_garment_counter(db: Session, garment_id: int, field_name: str, delta: int = 1) -> None:
    garment = db.query(Garment).filter(Garment.id == garment_id).first()
    if not garment:
        return

    current_value = int(getattr(garment, field_name, 0) or 0)
    updated_value = max(0, current_value + delta)
    setattr(garment, field_name, updated_value)


def normalize_fit_source(value: Any) -> str:
    text = str(value or "").strip().lower()
    aliases = {
        "": "online",
        "online": "online",
        "web": "online",
        "app": "online",
        "offline": "offline",
        "mirror": "offline",
        "store": "offline",
        "hardware": "offline",
    }
    return aliases.get(text, text or "online")


def normalize_fit_status(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None

    aliases = {
        "good": "fit",
        "fit": "fit",
        "ok": "fit",
        "fine": "fit",
        "too_small": "too_small",
        "small": "too_small",
        "tight": "too_small",
        "too_large": "too_large",
        "large": "too_large",
        "loose": "too_large",
        "bad": "not_fit",
        "not_fit": "not_fit",
    }
    return aliases.get(text, text)


def _extract_fit_status(feedback: Feedback) -> Optional[str]:
    if feedback.fit_status:
        return normalize_fit_status(feedback.fit_status)

    meta = feedback.meta or {}
    if isinstance(meta, dict):
        for key in ("fit_status", "fit", "size_fit", "size_feedback"):
            value = meta.get(key)
            if value:
                return normalize_fit_status(value)
    return None


def _extract_body_snapshot(feedback: Feedback) -> Dict[str, Any]:
    snapshot = feedback.body_snapshot or {}
    if isinstance(snapshot, dict) and snapshot:
        return snapshot

    meta = feedback.meta or {}
    if isinstance(meta, dict):
        for key in ("body_snapshot", "body", "mirror_body", "body_metrics"):
            value = meta.get(key)
            if isinstance(value, dict) and value:
                return value
    return {}


def _extract_garment_size(feedback: Feedback) -> Optional[str]:
    if feedback.garment_size:
        text = str(feedback.garment_size).strip()
        if text:
            return text

    meta = feedback.meta or {}
    if isinstance(meta, dict):
        for key in ("garment_size", "size", "size_label"):
            value = meta.get(key)
            if value:
                text = str(value).strip()
                if text:
                    return text
    return None


def _extract_style_labels(garment: Garment) -> List[str]:
    labels: List[str] = []
    blacklist = {
        "success",
        "message",
        "error",
        "raw_tags",
        "tag_info",
        "unknown",
        "none",
        "null",
    }
    for value in (garment.category, garment.season, garment.color):
        if value:
            label = str(value).strip()
            if label and label.lower() not in blacklist:
                labels.append(label)

    tags = garment.tags or []
    if isinstance(tags, list):
        for tag in tags:
            label = str(tag).strip()
            if label and label.lower() not in blacklist:
                labels.append(label)

    deduped: List[str] = []
    seen = set()
    for label in labels:
        if label in seen:
            continue
        seen.add(label)
        deduped.append(label)
    return deduped


def build_analytics_overview(db: Session, limit: int = 10) -> Dict[str, Any]:
    users = db.query(User).all()
    garments = db.query(Garment).filter(Garment.is_deleted == False).all()  # noqa: E712
    tryon_records = db.query(TryonRecord).all()
    feedbacks = db.query(Feedback).all()
    user_by_id = {user.id: user for user in users}

    body_shape_counter = Counter()
    body_shape_fit_counter = Counter()
    body_scatter = []
    body_profile_trend = [
        {"week": f"W{index + 1}", "samples": 0, "valid": 0}
        for index in range(4)
    ]
    total_height = 0.0
    total_weight = 0.0
    height_count = 0
    weight_count = 0

    now = datetime.utcnow()

    def _week_start(value: datetime) -> datetime:
        current = value.date() - timedelta(days=value.weekday())
        return datetime.combine(current, datetime.min.time())

    current_week_start = _week_start(now)

    for user in users:
        if user.height_cm is not None and user.weight_kg is not None:
            body_scatter.append(
                {
                    "h": int(round(float(user.height_cm))),
                    "weight": round(float(user.weight_kg), 1),
                    "size": str(user.body_shape).strip() if user.body_shape else "未知",
                }
            )
        if user.body_shape:
            body_shape_counter[str(user.body_shape).strip()] += 1
        if user.height_cm is not None:
            total_height += float(user.height_cm)
            height_count += 1
        if user.weight_kg is not None:
            total_weight += float(user.weight_kg)
            weight_count += 1

        created_at = getattr(user, "created_at", None) or now
        created_week = _week_start(created_at)
        week_delta = int((current_week_start - created_week).days // 7)
        if 0 <= week_delta <= 3:
            bucket = body_profile_trend[3 - week_delta]
            bucket["samples"] += 1
            if user.height_cm is not None or user.weight_kg is not None or user.body_shape:
                bucket["valid"] += 1

    style_scores = defaultdict(lambda: {"score": 0.0, "tryon_count": 0, "favorite_count": 0})
    for garment in garments:
        weight = float(garment.tryon_count or 0) + float(garment.favorite_count or 0) * 2.0
        for label in _extract_style_labels(garment):
            style_scores[label]["score"] += weight
            style_scores[label]["tryon_count"] += int(garment.tryon_count or 0)
            style_scores[label]["favorite_count"] += int(garment.favorite_count or 0)

    top_garments = sorted(
        garments,
        key=lambda item: (int(item.tryon_count or 0), int(item.favorite_count or 0), int(item.id)),
        reverse=True,
    )[:limit]

    top_favorite_garments = sorted(
        garments,
        key=lambda item: (int(item.favorite_count or 0), int(item.tryon_count or 0), int(item.id)),
        reverse=True,
    )[:limit]

    fit_status_counter = Counter()
    fit_garment_counter = Counter()
    fit_source_counter = Counter()
    fit_status_by_source = defaultdict(Counter)
    garment_size_counter = Counter()
    garment_size_by_source = defaultdict(Counter)
    body_shape_by_source = defaultdict(Counter)
    garment_counter_by_source = defaultdict(Counter)

    for feedback in feedbacks:
        fit_source = normalize_fit_source(getattr(feedback, "fit_source", None))
        fit_status = _extract_fit_status(feedback)
        body_snapshot = _extract_body_snapshot(feedback)
        garment_size = _extract_garment_size(feedback)

        fit_source_counter[fit_source] += 1
        if fit_status:
            fit_status_counter[fit_status] += 1
            fit_status_by_source[fit_source][fit_status] += 1
            if feedback.garment_id:
                fit_garment_counter[int(feedback.garment_id)] += 1
                garment_counter_by_source[fit_source][int(feedback.garment_id)] += 1

        if garment_size:
            garment_size_counter[garment_size] += 1
            garment_size_by_source[fit_source][garment_size] += 1

        if body_snapshot:
            body_shape = body_snapshot.get("body_shape") or body_snapshot.get("shape") or body_snapshot.get("type")
            if body_shape:
                body_shape_by_source[fit_source][str(body_shape).strip()] += 1

        if fit_status:
            body_shape = None
            if body_snapshot:
                body_shape = body_snapshot.get("body_shape") or body_snapshot.get("shape") or body_snapshot.get("type")
            if not body_shape and feedback.owner_id in user_by_id:
                body_shape = user_by_id[feedback.owner_id].body_shape
            if body_shape:
                body_shape_fit_counter[str(body_shape).strip()] += 1

    def _counter_items(counter: Counter, key_name: str) -> List[Dict[str, Any]]:
        return [{key_name: key, "count": count} for key, count in counter.most_common()]

    def _top_garment_items(counter: Counter) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for garment_id, count in counter.most_common(limit):
            garment = next((item for item in garments if item.id == garment_id), None)
            if not garment:
                continue
            items.append(
                {
                    "garment_id": garment_id,
                    "name": garment.name,
                    "category": garment.category,
                    "fit_feedback_count": count,
                }
            )
        return items

    style_heat = [
        {
            "style": label,
            "score": round(values["score"], 2),
            "tryon_count": int(values["tryon_count"]),
            "favorite_count": int(values["favorite_count"]),
        }
        for label, values in sorted(style_scores.items(), key=lambda item: item[1]["score"], reverse=True)[:limit]
    ]

    fit_garments = []
    for garment_id, count in fit_garment_counter.most_common(limit):
        garment = next((item for item in garments if item.id == garment_id), None)
        if not garment:
            continue
        fit_garments.append(
            {
                "garment_id": garment_id,
                "name": garment.name,
                "category": garment.category,
                "fit_feedback_count": count,
            }
        )

    body_segment_stats = []
    for body_shape, count in body_shape_counter.most_common():
        fit_count = int(body_shape_fit_counter.get(body_shape, 0) or 0)
        body_segment_stats.append(
            {
                "segment": body_shape,
                "percent": round((count / len(users)) * 100, 1) if users else 0,
                "conversion": round((fit_count / count) * 100, 1) if count else 0,
            }
        )

    return {
        "user_metrics": {
            "total_users": len(users),
            "profiled_users": sum(1 for user in users if user.height_cm is not None or user.weight_kg is not None or user.body_shape),
            "average_height_cm": round(total_height / height_count, 2) if height_count else None,
            "average_weight_kg": round(total_weight / weight_count, 2) if weight_count else None,
            "body_scatter": body_scatter,
            "body_profile_trend": body_profile_trend,
            "body_segment_stats": body_segment_stats,
            "body_shape_distribution": [
                {"body_shape": body_shape, "count": count}
                for body_shape, count in body_shape_counter.most_common()
            ],
        },
        "garment_metrics": {
            "total_garments": len(garments),
            "total_tryon_records": len(tryon_records),
            "top_tryon_garments": [
                {
                    "garment_id": garment.id,
                    "name": garment.name,
                    "category": garment.category,
                    "tryon_count": int(garment.tryon_count or 0),
                    "favorite_count": int(garment.favorite_count or 0),
                }
                for garment in top_garments
            ],
            "top_favorite_garments": [
                {
                    "garment_id": garment.id,
                    "name": garment.name,
                    "category": garment.category,
                    "tryon_count": int(garment.tryon_count or 0),
                    "favorite_count": int(garment.favorite_count or 0),
                }
                for garment in top_favorite_garments
            ],
            "style_heat": style_heat,
        },
        "fit_feedback_metrics": {
            "total_feedback": len(feedbacks),
            "fit_feedback_count": sum(fit_status_counter.values()),
            "fit_source_distribution": _counter_items(fit_source_counter, "fit_source"),
            "fit_status_distribution": [
                {"fit_status": status_name, "count": count}
                for status_name, count in fit_status_counter.most_common()
            ],
            "online_fit_feedback_count": fit_source_counter.get("online", 0),
            "offline_fit_feedback_count": fit_source_counter.get("offline", 0),
            "online_fit_status_distribution": [
                {"fit_status": status_name, "count": count}
                for status_name, count in fit_status_by_source["online"].most_common()
            ],
            "offline_fit_status_distribution": [
                {"fit_status": status_name, "count": count}
                for status_name, count in fit_status_by_source["offline"].most_common()
            ],
            "garment_size_distribution": _counter_items(garment_size_counter, "garment_size"),
            "online_garment_size_distribution": _counter_items(garment_size_by_source["online"], "garment_size"),
            "offline_garment_size_distribution": _counter_items(garment_size_by_source["offline"], "garment_size"),
            "online_body_shape_distribution": _counter_items(body_shape_by_source["online"], "body_shape"),
            "offline_body_shape_distribution": _counter_items(body_shape_by_source["offline"], "body_shape"),
            "online_top_fit_garments": _top_garment_items(garment_counter_by_source["online"]),
            "offline_top_fit_garments": _top_garment_items(garment_counter_by_source["offline"]),
            "top_fit_garments": fit_garments,
            "offline_binding_count": sum(1 for feedback in feedbacks if normalize_fit_source(getattr(feedback, "fit_source", None)) == "offline" and (_extract_garment_size(feedback) or _extract_body_snapshot(feedback))),
        },
    }
