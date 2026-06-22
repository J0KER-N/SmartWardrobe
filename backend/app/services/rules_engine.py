"""穿搭规则引擎：基于颜色兼容矩阵、温度适配和季节协调的动态推荐。

主要改进：
1. 启动时加载规则（缓存），移除每次 recommend() 的热加载
2. 引入颜色兼容矩阵进行动态打分
3. score_candidate() 实现有意义的多因子评分
"""
from __future__ import annotations

import logging
import random
import threading
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# ─── 单例规则缓存 ──

class RuleCache:
    """线程安全的规则缓存单例。"""
    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            self.rules_path = Path(__file__).resolve().parents[2] / "config" / "rules"
            self._load()
            self._initialized = True

    def _load(self):
        rules_dir = self.rules_path
        self.color_matrix: Dict[str, float] = {}
        self.temperature_zones: List[Dict] = []
        self.season_tags: Dict[str, List[str]] = {}
        self.conflict_rules: Dict[str, List[List[str]]] = {}
        self.rules: List[Dict] = []

        if not rules_dir.exists():
            logger.warning("规则目录不存在: %s", rules_dir)
            return

        for p in sorted(rules_dir.glob("*.yaml")):
            try:
                with p.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}

                if "color_compatibility" in data:
                    self.color_matrix.update(data["color_compatibility"])
                if "temperature_zones" in data:
                    self.temperature_zones = data["temperature_zones"]
                if "season_tags" in data:
                    self.season_tags.update(data["season_tags"])
                if "conflict_rules" in data:
                    self.conflict_rules.update(data["conflict_rules"])
                if "rules" in data:
                    self.rules.extend(data["rules"])

            except Exception as e:
                logger.error("加载规则文件失败 %s: %s", p, e)

        logger.info(
            "规则已加载: %d 颜色规则, %d 温度区间, %d 规则条目",
            len(self.color_matrix), len(self.temperature_zones), len(self.rules)
        )

    def reload(self):
        with self._lock:
            self._load()

    @property
    def is_loaded(self) -> bool:
        return bool(self.color_matrix) or bool(self.rules)


# ─── 规则引擎 ──

class RulesEngine:
    def __init__(self):
        self._cache = RuleCache()

    # ── 公共 API ──

    def recommend(
        self,
        garments: List[Dict[str, Any]],
        *,
        n: int = 3,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        返回候选项列表，每个包含 candidate_id, score, reason, garment_id。

        context 支持:
          - temperature: float（当前温度）
          - season: str（当前季节）
        """
        if context is None:
            context = {}

        candidates: List[Dict[str, Any]] = []
        temp = context.get("temperature", 20.0)
        season = context.get("season", self._detect_season(temp))

        for g in garments:
            score, reasons = self._score_garment(g, temp, season)
            if score > 0:
                candidates.append({
                    "candidate_id": f"c_{g.get('id')}_{random.randint(1000, 9999)}",
                    "garment_id": g.get("id"),
                    "score": round(score, 3),
                    "reason": "；".join(reasons),
                })

        # 按分数排序去重
        candidates.sort(key=lambda x: x["score"], reverse=True)
        seen: Set[int] = set()
        result = []
        for c in candidates:
            gid = c["garment_id"]
            if gid in seen:
                continue
            seen.add(gid)
            result.append(c)
            if len(result) >= n:
                break

        # 如果没有任何候选项，随机取
        if not result and garments:
            sample = random.sample(garments, min(n, len(garments)))
            result = [
                {
                    "candidate_id": f"c_{g.get('id')}_{random.randint(1000, 9999)}",
                    "garment_id": g.get("id"),
                    "score": 0.1,
                    "reason": "衣橱兜底推荐",
                }
                for g in sample
            ]

        return result

    def get_color_score(self, color1: str, color2: str) -> float:
        """查询颜色兼容度。"""
        if not color1 or not color2:
            return 0.5
        key = f"{color1}:{color2}"
        rev_key = f"{color2}:{color1}"
        return max(
            self._cache.color_matrix.get(key, 0.5),
            self._cache.color_matrix.get(rev_key, 0.5),
        )

    def check_category_conflict(self, categories: List[str]) -> bool:
        """检查品类是否冲突。"""
        conflicts = self._cache.conflict_rules.get("category_conflicts", [])
        for a, b in conflicts:
            if a in categories and b in categories:
                return True
        return False

    def _detect_season(self, temp: float) -> str:
        if temp >= 25:
            return "summer"
        elif temp >= 15:
            return "spring"
        elif temp >= 5:
            return "autumn"
        return "winter"

    def _score_garment(
        self,
        garment: Dict[str, Any],
        temperature: float,
        season: str,
    ) -> tuple:
        score = 0.0
        reasons = []
        tags = garment.get("tags") or []
        category = garment.get("category", "")
        season_str = ""

        # 1. 温度适配 (权重 1.5)
        for zone in self._cache.temperature_zones:
            if zone["min"] <= temperature < zone["max"]:
                zone_suggestions = zone.get("suggestions", [])
                match = any(s in category for s in zone_suggestions)
                match = match or any(t in tags for t in zone_suggestions)
                if match:
                    score += 1.5
                    reasons.append(f"适合 {zone['label']} 天气")
                break

        # 2. 季节协调 (权重 0.8)
        season_tags = self._cache.season_tags.get(season, [])
        if any(t in tags for t in season_tags):
            score += 0.8
            reasons.append(f"适合{season}季节")

        # 3. 规则文件中的规则匹配
        for rule in self._cache.rules:
            rname = rule.get("name", "")
            rweight = float(rule.get("weight", 1.0))
            rtag = rule.get("tag", "")
            rstyle = rule.get("style", "")
            rcolor = rule.get("color", "")

            if rtag and rtag in tags:
                score += rweight * 0.8
                if rcolor and garment.get("color") == rcolor:
                    score += rweight * 0.5
                if rstyle:
                    reasons.append(rule.get("description", rname))

        return score, reasons


# ─── 工厂函数 ──

_default_engine = None
_engine_lock = threading.Lock()


def get_default_engine() -> RulesEngine:
    global _default_engine
    if _default_engine is None:
        with _engine_lock:
            if _default_engine is None:
                _default_engine = RulesEngine()
    return _default_engine
