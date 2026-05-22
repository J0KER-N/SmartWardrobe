"""简单规则引擎：基于颜色 / 风格 / 场景的静态规则，返回 N 个候选及可解释原因。"""
from __future__ import annotations

from typing import List, Dict, Any, Optional
import yaml
import logging
import random
from pathlib import Path

logger = logging.getLogger(__name__)


class RulesEngine:
    def __init__(self, rules_path: Optional[str] = None):
        self.rules_path = rules_path or Path(__file__).resolve().parents[2] / "config" / "rules"
        self.rules = []
        self.load_rules()

    def load_rules(self):
        """从规则目录加载所有 YAML 规则文件（支持热加载调用）。"""
        rules_dir = Path(self.rules_path)
        if not rules_dir.exists():
            logger.warning("规则目录不存在: %s", rules_dir)
            self.rules = []
            return

        loaded = []
        for p in sorted(rules_dir.glob("*.yaml")):
            try:
                with p.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                    loaded.append({"file": str(p.name), "rules": data.get("rules", [])})
            except Exception as e:
                logger.exception("加载规则文件失败: %s, %s", p, e)

        self.rules = loaded

    def explain_match(self, rule: Dict[str, Any]) -> str:
        return rule.get("description") or rule.get("name") or "基于规则匹配"

    def score_candidate(self, garment: Dict[str, Any], rule: Dict[str, Any]) -> float:
        # 简单示例：根据命中权重返回得分
        return float(rule.get("weight", 1.0))

    def recommend(self, garments: List[Dict[str, Any]], *, n: int = 3, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """返回候选列表：每个候选包含 candidate_id, score, reason, garment_id。"""
        if context is None:
            context = {}

        # 重新加载规则，支持热加载
        self.load_rules()

        candidates: List[Dict[str, Any]] = []
        # 遍历每条规则，对所有衣物进行打分并产生候选
        for rule_file in self.rules:
            for rule in rule_file.get("rules", []):
                # 简单匹配逻辑：颜色/style/tag 匹配
                for g in garments:
                    score = 0.0
                    matched = False
                    # color
                    if rule.get("color") and g.get("color"):
                        if rule["color"] in str(g.get("color")):
                            matched = True
                            score += 1.0
                    # style
                    if rule.get("style") and g.get("style"):
                        if rule["style"] == g.get("style"):
                            matched = True
                            score += 1.0
                    # tag
                    if rule.get("tag") and g.get("tags"):
                        if rule["tag"] in g.get("tags", []):
                            matched = True
                            score += 0.8

                    if matched:
                        score += self.score_candidate(g, rule)
                        candidates.append({
                            "candidate_id": f"c_{g.get('id')}_{random.randint(1000,9999)}",
                            "garment_id": g.get("id"),
                            "score": round(score, 3),
                            "reason": self.explain_match(rule),
                        })

        # 如果没有任何规则命中，回退到按简单随机推荐
        if not candidates:
            sample = random.sample(garments, min(n, len(garments))) if garments else []
            for g in sample:
                candidates.append({
                    "candidate_id": f"c_{g.get('id')}_{random.randint(1000,9999)}",
                    "garment_id": g.get("id"),
                    "score": 0.1,
                    "reason": "基于衣橱的兜底推荐",
                })

        # 按 score 排序并去重 garment_id，保留最高
        candidates.sort(key=lambda x: x["score"], reverse=True)
        seen = set()
        out = []
        for c in candidates:
            if c["garment_id"] in seen:
                continue
            seen.add(c["garment_id"])
            out.append(c)
            if len(out) >= n:
                break

        return out


def get_default_engine() -> RulesEngine:
    return RulesEngine()


if __name__ == "__main__":
    # quick manual test
    engine = get_default_engine()
    garments = [
        {"id": 1, "color": "蓝", "style": "休闲", "tags": ["夏季"]},
        {"id": 2, "color": "白", "style": "正式", "tags": ["工作"]},
    ]
    print(engine.recommend(garments, n=3))
