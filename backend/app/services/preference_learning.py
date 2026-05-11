from __future__ import annotations

import json
import logging
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

logger = logging.getLogger(__name__)

_STORAGE_PATH = Path(__file__).resolve().parents[2] / "data" / "user_preferences.json"

_DEFAULT_PROFILE: Dict[str, Any] = {
    "style_weights": {},
    "color_weights": {},
    "category_weights": {},
    "tag_weights": {},
    "feedback_count": 0,
    "updated_at": None,
}

_POSITIVE_ACTIONS = {"like", "collect", "purchase"}
_NEGATIVE_ACTIONS = {"dislike", "skip"}

_STYLE_KEYWORDS = ["简约", "时尚", "休闲", "正式", "运动", "甜美", "复古", "通勤"]
_COLOR_KEYWORDS = ["深色", "浅色", "亮色", "暖色", "冷色", "黑", "白", "灰", "蓝", "红", "绿", "黄"]


def _ensure_storage_parent() -> None:
    _STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)


def _load_store() -> Dict[str, Dict[str, Any]]:
    if not _STORAGE_PATH.exists():
        return {}
    try:
        with _STORAGE_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, dict) else {}
    except Exception as exc:
        logger.warning("读取偏好存储失败: %s", exc)
        return {}


def _save_store(store: Dict[str, Dict[str, Any]]) -> None:
    _ensure_storage_parent()
    with _STORAGE_PATH.open("w", encoding="utf-8") as file:
        json.dump(store, file, ensure_ascii=False, indent=2)


def _make_profile() -> Dict[str, Any]:
    return deepcopy(_DEFAULT_PROFILE)


def get_user_preference_profile(user_id: int) -> Dict[str, Any]:
    store = _load_store()
    return deepcopy(store.get(str(user_id), _make_profile()))


def _normalize_action(action: Optional[str]) -> str:
    if not action:
        return "like"
    return action.strip().lower()


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


def _normalize_values(values: Any) -> List[str]:
    if values is None:
        return []
    if isinstance(values, str):
        return [values]
    if isinstance(values, (list, tuple, set)):
        return [str(item) for item in values if item is not None]
    return [str(values)]


def _extract_signals(meta: Dict[str, Any]) -> Dict[str, List[str]]:
    signals = {
        "styles": [],
        "colors": [],
        "categories": [],
        "tags": [],
    }

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

    garment_list = meta.get("garments") or []
    for garment in garment_list:
        garment_meta = garment if isinstance(garment, dict) else {}
        signals["categories"].extend(_normalize_values(garment_meta.get("category")))
        signals["colors"].extend(_normalize_values(garment_meta.get("color")))
        signals["tags"].extend(_normalize_values(garment_meta.get("tags")))

    for signal_key in signals:
        # 去重并去空
        deduped = []
        seen = set()
        for item in signals[signal_key]:
            value = str(item).strip()
            if not value or value in seen:
                continue
            seen.add(value)
            deduped.append(value)
        signals[signal_key] = deduped

    return signals


def _action_delta(action: str) -> float:
    if action in _POSITIVE_ACTIONS:
        return 1.0
    if action in _NEGATIVE_ACTIONS:
        return -1.0
    return 0.5


def _bump_weight(weights: Dict[str, float], key: str, delta: float) -> None:
    current = float(weights.get(key, 0.0))
    updated = max(-5.0, min(5.0, current + delta))
    weights[key] = round(updated, 3)


def update_user_pref(user_id: int, feedback: Any) -> Dict[str, Any]:
    """基于反馈更新用户偏好画像。

    参数支持 dict / Pydantic model / 简单对象，方便后续接入 feedback 接口。
    """
    meta = _extract_feedback_meta(feedback)
    action = _normalize_action(meta.get("action"))
    delta = _action_delta(action)
    signals = _extract_signals(meta)

    store = _load_store()
    profile = deepcopy(store.get(str(user_id), _make_profile()))

    if signals["styles"]:
        for style in signals["styles"]:
            _bump_weight(profile["style_weights"], style, delta)
    if signals["colors"]:
        for color in signals["colors"]:
            _bump_weight(profile["color_weights"], color, delta)
    if signals["categories"]:
        for category in signals["categories"]:
            _bump_weight(profile["category_weights"], category, delta)
    if signals["tags"]:
        for tag in signals["tags"]:
            _bump_weight(profile["tag_weights"], tag, delta)

    profile["feedback_count"] = int(profile.get("feedback_count", 0)) + 1
    profile["updated_at"] = datetime.utcnow().isoformat() + "Z"

    store[str(user_id)] = profile
    _save_store(store)
    return deepcopy(profile)


def score_outfit_preference(garments: Sequence[Any], preference_profile: Optional[Dict[str, Any]]) -> float:
    """根据用户偏好给一套搭配打分，分值范围约为 0.0 - 1.0。"""
    if not preference_profile:
        return 0.0

    style_weights = preference_profile.get("style_weights", {}) or {}
    color_weights = preference_profile.get("color_weights", {}) or {}
    category_weights = preference_profile.get("category_weights", {}) or {}
    tag_weights = preference_profile.get("tag_weights", {}) or {}

    score = 0.0
    touched = 0

    for garment in garments:
        garment_data = garment if isinstance(garment, dict) else {}
        category = str(garment_data.get("category", "")).strip()
        color = str(garment_data.get("color", "")).strip()
        tags = garment_data.get("tags") or []
        if not isinstance(tags, (list, tuple, set)):
            tags = [tags]

        if category:
            score += float(category_weights.get(category, 0.0))
            touched += 1
        if color:
            score += float(color_weights.get(color, 0.0))
            touched += 1
        for tag in tags:
            tag_text = str(tag).strip()
            if not tag_text:
                continue
            score += float(tag_weights.get(tag_text, 0.0))
            for style, weight in style_weights.items():
                if style and style in tag_text:
                    score += float(weight)
                    touched += 1

    if touched == 0:
        return 0.0

    # 归一化到 0-1 区间，便于和其它启发式分数合并
    normalized = 0.5 + score / max(8.0, float(touched) * 4.0)
    return round(max(0.0, min(1.0, normalized)), 3)
