from app.services.rules_engine import RulesEngine


def test_recommend_structure_and_reason():
    engine = RulesEngine(rules_path="./config/rules")
    garments = [
        {"id": 1, "color": "白", "tags": ["夏季", "休闲"]},
        {"id": 2, "color": "蓝", "tags": ["防水", "雨天"]},
    ]

    out = engine.recommend(garments, n=2)
    assert isinstance(out, list)
    assert len(out) <= 2
    for c in out:
        assert "candidate_id" in c
        assert "score" in c
        assert "reason" in c
