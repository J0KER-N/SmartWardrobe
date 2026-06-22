"""穿搭推荐逻辑。

配置驱动的标签体系 + 梯度温度区间 + 基础兼容性检查。
"""
from __future__ import annotations

import logging
import random
from typing import Any, Dict, List, Optional

from .preference_learning import score_outfit_preference
from .rules_engine import get_default_engine

logger = logging.getLogger(__name__)

# ─── 品类分组（用于兼容性检查） ──
_TOP_CATEGORIES = {"上装", "上衣", "T恤", "衬衫", "毛衣", "卫衣", "短袖", "长袖"}
_BOTTOM_CATEGORIES = {"下装", "裤子", "长裤", "短裤", "裙子", "半身裙"}
_OUTER_CATEGORIES = {"外套", "大衣", "夹克", "羽绒服", "风衣"}
_FULL_BODY_CATEGORIES = {"连衣裙", "连体裤"}


def generate_outfit_recommendations(
    garments: List,
    weather: Dict,
    preference_profile: Optional[Dict] = None,
) -> List[Dict]:
    """生成穿搭推荐组合。

    Args:
        garments: 用户衣橱中的衣物列表
        weather: 天气信息 {temp_c, condition, ...}
        preference_profile: 用户偏好画像（可选）

    Returns:
        推荐组合列表，每个包含 garment_ids, garments, reason
    """
    temp = weather.get("temp_c", 20)
    condition = weather.get("condition", "晴")
    engine = get_default_engine()

    # 对衣物做分类
    categorized = _categorize_garments(garments)

    recommendations = []

    # 1. 尝试按温度区间推荐
    zone_rec = _recommend_by_temperature(categorized, temp, condition, engine)
    if zone_rec:
        recommendations.append(zone_rec)

    # 2. 尝试按季节推荐
    season = engine._detect_season(temp)
    season_tags = engine._cache.season_tags.get(season, [])
    season_matched = [g for g in garments
                      if g.tags and any(t in (g.tags or []) for t in season_tags)]
    if season_matched and len(season_matched) >= 2:
        selected = _pick_compatible_set(season_matched, 2, engine)
        if selected:
            recommendations.append({
                "garment_ids": [g.id for g in selected],
                "garments": selected,
                "reason": f"适合{season}季节的搭配",
                "style": None,
                "color": None,
            })

    # 3. 基础搭配推荐（上+下）
    tops = categorized["tops"]
    bottoms = categorized["bottoms"]
    if tops and bottoms:
        top = _pick_best(tops, engine, temp)
        bottom = _pick_best(bottoms, engine, temp)
        # 检查颜色兼容
        if top.color and bottom.color:
            cs = engine.get_color_score(top.color, bottom.color)
            if cs > 0.3:  # 至少中性搭配
                recommendations.append({
                    "garment_ids": [top.id, bottom.id],
                    "garments": [top, bottom],
                    "reason": f"基础搭配（颜色兼容度 {cs:.1f}）",
                    "style": None,
                    "color": None,
                })

    # 4. 外搭推荐（如果有外套）
    if tops and bottoms and categorized["outers"]:
        outer = _pick_best(categorized["outers"], engine, temp)
        top = tops[0]
        bottom = bottoms[0]
        recommendations.append({
            "garment_ids": [top.id, bottom.id, outer.id],
            "garments": [top, bottom, outer],
            "reason": "三层穿搭：内搭 + 外套",
            "style": None,
            "color": None,
        })

    # 5. 连衣裙单独推荐
    for dress in categorized["dresses"]:
        recommendations.append({
            "garment_ids": [dress.id],
            "garments": [dress],
            "reason": "连衣裙单穿推荐",
            "style": None,
            "color": None,
        })

    # 6. 偏好排序
    if preference_profile and recommendations:
        recommendations.sort(
            key=lambda r: score_outfit_preference(
                r.get("garments", []), preference_profile
            ),
            reverse=True,
        )

    return recommendations


# ─── 内部函数 ──

def _categorize_garments(garments) -> Dict:
    """按品类分类衣物。"""
    result: Dict[str, List] = {
        "tops": [], "bottoms": [], "outers": [], "dresses": [],
        "shoes": [], "others": [],
    }
    for g in garments:
        cat = (g.category or "").strip()
        if cat in _TOP_CATEGORIES:
            result["tops"].append(g)
        elif cat in _BOTTOM_CATEGORIES:
            result["bottoms"].append(g)
        elif cat in _OUTER_CATEGORIES:
            result["outers"].append(g)
        elif cat in _FULL_BODY_CATEGORIES:
            result["dresses"].append(g)
        else:
            result["others"].append(g)
    return result


def _recommend_by_temperature(
    categorized: Dict,
    temp: float,
    condition: str,
    engine,
) -> Optional[Dict]:
    """按温度区间推荐，适配降雨/降雪天气。"""
    tops = categorized["tops"]
    bottoms = categorized["bottoms"]

    if not tops and not bottoms:
        return None

    if temp >= 25:
        # 炎热/温暖：短袖/短裤
        selected = _pick_compatible_set(
            tops[:3] + bottoms[:3],
            2,
            engine,
            prefer_tags=["短袖", "短裤", "裙子", "清凉"],
        )
    elif temp >= 15:
        # 舒适：常规搭配
        selected = _pick_compatible_set(
            tops + bottoms, 2, engine
        )
    elif temp >= 5:
        # 凉爽：长袖 + 外套
        selected = _pick_compatible_set(
            tops + categorized["outers"] + bottoms, 3, engine
        )
    else:
        # 寒冷：保暖
        selected = _pick_compatible_set(
            tops + categorized["outers"] + bottoms, 3, engine,
            prefer_tags=["保暖", "毛衣", "羽绒"],
        )

    if not selected:
        return None

    return {
        "garment_ids": [g.id for g in selected],
        "garments": selected,
        "reason": f"温度 {temp:.0f}°C 适配推荐",
        "style": None,
        "color": None,
    }


def _pick_compatible_set(
    candidates: List,
    count: int,
    engine,
    prefer_tags: Optional[List[str]] = None,
) -> List:
    """挑选兼容的衣物组合。"""
    # 优先按 prefer_tags 过滤
    if prefer_tags:
        tagged = [g for g in candidates
                  if g.tags and any(t in (g.tags or []) for t in prefer_tags)]
        if len(tagged) >= count:
            candidates = tagged

    # 打乱后取，检查品类冲突
    shuffled = list(candidates)
    random.shuffle(shuffled)
    selected = []
    selected_cats = set()

    for g in shuffled:
        cat = (g.category or "").strip()
        # 检查品类是否冲突
        if any(c in _TOP_CATEGORIES and cat in _TOP_CATEGORIES and c != cat
               for c in selected_cats):
            continue
        # 允许不同品类共存
        if cat in _BOTTOM_CATEGORIES and any(c in _BOTTOM_CATEGORIES for c in selected_cats):
            continue
        if cat in _OUTER_CATEGORIES and any(c in _OUTER_CATEGORIES for c in selected_cats):
            continue

        # 检查颜色兼容
        if selected and g.color:
            color_ok = all(
                engine.get_color_score(g.color, sg.color) > 0.3
                for sg in selected if sg.color
            )
            if not color_ok:
                continue

        selected.append(g)
        selected_cats.add(cat)
        if len(selected) >= count:
            break

    return selected


def _pick_best(
    garments: List,
    engine,
    temperature: float = 20,
) -> Any:
    """按得分选取最佳单品。"""
    if not garments:
        return None

    scored = []
    for g in garments:
        context = {"temperature": temperature}
        candidates = engine.recommend(
            [{"id": g.id, "color": g.color or "", "tags": g.tags or []}],
            n=1,
            context=context,
        )
        score = candidates[0]["score"] if candidates else 0.5
        scored.append((g, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[0][0]
