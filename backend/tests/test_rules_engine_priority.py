import tempfile
import yaml
from app.services.rules_engine import RulesEngine


def test_rule_weight_affects_ranking():
    # 准备临时规则目录和两个规则，分别对不同 garment 命中且权重不同
    with tempfile.TemporaryDirectory() as d:
        rules_path = d
        rule_file = f"{d}/w.yaml"
        rules = {
            "rules": [
                {"name": "low_weight", "tag": "low", "weight": 0.5, "description": "低权重规则"},
                {"name": "high_weight", "tag": "high", "weight": 2.0, "description": "高权重规则"},
            ]
        }
        with open(rule_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(rules, f, allow_unicode=True)

        garments = [
            {"id": 1, "tags": ["low"]},
            {"id": 2, "tags": ["high"]},
        ]

        engine = RulesEngine(rules_path=rules_path)
        out = engine.recommend(garments, n=2)

        # Expect garment with tag 'high' to appear before 'low' due to higher weight
        assert len(out) == 2
        assert out[0]["garment_id"] == 2
