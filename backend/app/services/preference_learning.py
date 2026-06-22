"""用户偏好学习——基于 SQLAlchemy 数据库存储，支持指数衰减和 sigmoid 归一化。

替换了旧版 JSON 文件存储，提供并发事务保护。
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence
from copy import deepcopy

from ..database import SessionLocal
from ..models import UserPreference

logger = logging.getLogger(__name__)

# ─── 常量 ──
_POSITIVE_ACTIONS = {"like", "collect", "purchase"}
_NEGATIVE_ACTIONS = {"dislike", "skip"}
_DECAY_RATE = 0.05  # 指数衰减率：每天衰减 5%
_SIGMOID_K = 0.5    # sigmoid 陡度参数
_STYLE_KEYWORDS = ["简约", "时尚", "休闲", "正式", "运动", "甜美", "复古", "通勤"]
_COLOR_KEYWORDS = ["深色", "浅色", "亮色", "暖色", "冷色", "黑", "白", "灰", "蓝", "红", "绿", "黄"]


# ─── 公共 API ──

def get_user_preference_profile(user_id: int) -> Dict[str, Any]:
    """获取用户偏好画像。"""
    db = SessionLocal()
    try:
        pref = db.query(UserPreference).filter(
            UserPreference.user_id == user_id
        ).first()
        if not pref:
            return _default_profile()
        return _profile_from_db(pref)
    finally:
        db.close()


def update_user_pref(user_id: int, feedback: Any) -> Dict[str, Any]:
    """基于反馈更新用户偏好（事务保护）。"""
    db = SessionLocal()
    try:
        # 使用行级锁避免并发竞争
        pref = db.query(UserPreference).filter(
            UserPreference.user_id == user_id
        ).with_for_update().first()

        if not pref:
            pref = UserPreference(user_id=user_id)
            db.add(pref)

        meta = _extract_feedback_meta(feedback)
        action = _normalize_action(meta.get("action"))
        delta = _action_delta(action)
        signals = _extract_signals(meta)

        # 先应用时间衰减
        _apply_decay(pref)

        # 更新权重
        weights_map = {
            "style_weights": signals.get("styles", []),
            "color_weights": signals.get("colors", []),
            "category_weights": signals.get("categories", []),
            "tag_weights": signals.get("tags", []),
        }

        for attr, values in weights_map.items():
            w = _get_json(pref, attr)
            for val in values:
                current = float(w.get(val, 0.0))
                w[val] = round(max(-5.0, min(5.0, current + delta)), 3)
            _set_json(pref, attr, w)

        pref.feedback_count = (pref.feedback_count or 0) + 1
        pref.updated_at = datetime.utcnow()
        db.commit()

        return _profile_from_db(pref)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def score_outfit_preference(
    garments: Sequence[Any],
    preference_profile: Optional[Dict[str, Any]],
) -> float:
    """根据用户偏好给一套搭配打分，返回 [0, 1] 使用 sigmoid 归一化。"""
    if not preference_profile:
        return 0.0

    weights = _get_field(preference_profile, "style_weights", {})
    color_w = _get_field(preference_profile, "color_weights", {})
    cat_w = _get_field(preference_profile, "category_weights", {})
    tag_w = _get_field(preference_profile, "tag_weights", {})

    score = 0.0
    touched = 0

    for g in garments:
        gd = g if isinstance(g, dict) else {}
        category = str(gd.get("category", "")).strip()
        color = str(gd.get("color", "")).strip()
        tags = gd.get("tags") or []
        if not isinstance(tags, (list, tuple, set)):
            tags = [tags]

        if category:
            score += float(cat_w.get(category, 0.0))
            touched += 1
        if color:
            score += float(color_w.get(color, 0.0))
            touched += 1
        for tag in tags:
            t = str(tag).strip()
            if t:
                score += float(tag_w.get(t, 0.0))
                for style, w in weights.items():
                    if style and style in t:
                        score += float(w)
                        touched += 1

    # sigmoid 归一化到 [0, 1]
    if touched == 0:
        return 0.0
    normalized = 1.0 / (1.0 + math.exp(-_SIGMOID_K * (score / max(touched, 1))))
    return round(normalized, 3)


# ─── 内部实现 ──

def _default_profile() -> Dict[str, Any]:
    return {
        "style_weights": {},
        "color_weights": {},
        "category_weights": {},
        "tag_weights": {},
        "feedback_count": 0,
        "updated_at": None,
    }


def _profile_from_db(pref: UserPreference) -> Dict[str, Any]:
    return {
        "style_weights": _get_json(pref, "style_weights"),
        "color_weights": _get_json(pref, "color_weights"),
        "category_weights": _get_json(pref, "category_weights"),
        "tag_weights": _get_json(pref, "tag_weights"),
        "feedback_count": pref.feedback_count or 0,
        "updated_at": pref.updated_at.isoformat() if pref.updated_at else None,
    }


def _get_json(pref: UserPreference, attr: str) -> Dict[str, float]:
    v = getattr(pref, attr, None)
    return v if isinstance(v, dict) else {}


def _set_json(pref: UserPreference, attr: str, value: Dict[str, float]) -> None:
    setattr(pref, attr, value)


def _get_field(profile: Dict, key: str, default: Any = None) -> Any:
    return profile.get(key, default) or {}


def _apply_decay(pref: UserPreference) -> None:
    """对旧权重应用指数时间衰减。"""
    updated = pref.updated_at
    if not updated:
        return
    now = datetime.utcnow()
    # 兼容带时区和不带时区的 datetime
    if updated.tzinfo is not None:
        now = now.replace(tzinfo=timezone.utc)
        updated = updated.replace(tzinfo=timezone.utc)

    days = (now - updated).total_seconds() / 86400.0
    if days <= 0:
        return

    decay_factor = math.exp(-_DECAY_RATE * days)

    for attr in ("style_weights", "color_weights", "category_weights", "tag_weights"):
        w = _get_json(pref, attr)
        for k in list(w.keys()):
            w[k] = round(float(w[k]) * decay_factor, 3)
            if abs(w[k]) < 0.001:  # 接近 0 的权重直接清理
                del w[k]
        _set_json(pref, attr, w)


def _extract_feedback_meta(feedback: Any) -> Dict[str, Any]:
    if isinstance(feedback, dict):
        return feedback
    if hasattr(feedback, "model_dump"):
        try:
            return feedback.model_dump(exclude_unset=True)
        except Exception:
            return {}
    if hasattr(feedback, "dict"):
        try:
            return feedback.dict(exclude_unset=True)
        except Exception:
            return {}
    return {}


def _normalize_action(action: Optional[str]) -> str:
    return (action or "like").strip().lower()


def _action_delta(action: str) -> float:
    if action in _POSITIVE_ACTIONS:
        return 1.0
    if action in _NEGATIVE_ACTIONS:
        return -1.0
    return 0.5


def _normalize_values(values: Any) -> List[str]:
    if not values:
        return []
    if isinstance(values, str):
        return [values]
    if isinstance(values, (list, tuple, set)):
        return [str(item) for item in values if item is not None]
    return [str(values)]


def _extract_signals(meta: Dict[str, Any]) -> Dict[str, List[str]]:
    signals = {"styles": [], "colors": [], "categories": [], "tags": []}

    for key in ("style", "styles"):
        signals["styles"].extend(_normalize_values(meta.get(key)))
    for key in ("color", "colors", "color_palette"):
        signals["colors"].extend(_normalize_values(meta.get(key)))
    for key in ("category", "categories", "garment_categories"):
        signals["categories"].extend(_normalize_values(meta.get(key)))
    for key in ("tag", "tags"):
        signals["tags"].extend(_normalize_values(meta.get(key)))

    reason_text = str(meta.get("reason", ""))
    if reason_text:
        for keyword in _STYLE_KEYWORDS:
            if keyword in reason_text:
                signals["styles"].append(keyword)
        for keyword in _COLOR_KEYWORDS:
            if keyword in reason_text:
                signals["colors"].append(keyword)

    # 从 garment 列表提取信号
    garment_list = meta.get("garments") or []
    for garment in garment_list:
        gm = garment if isinstance(garment, dict) else {}
        signals["categories"].extend(_normalize_values(gm.get("category")))
        signals["colors"].extend(_normalize_values(gm.get("color")))
        signals["tags"].extend(_normalize_values(gm.get("tags")))

    # 去重去空
    for k in signals:
        seen = set()
        deduped = []
        for item in signals[k]:
            v = str(item).strip()
            if v and v not in seen:
                seen.add(v)
                deduped.append(v)
        signals[k] = deduped

    return signals
