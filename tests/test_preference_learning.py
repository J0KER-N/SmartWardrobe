from backend.app.services.preference_learning import update_user_pref, get_user_preference_profile, score_outfit_preference


def test_update_user_pref_increases_positive_weights(tmp_path, monkeypatch):
    storage_path = tmp_path / "user_preferences.json"
    monkeypatch.setattr("backend.app.services.preference_learning._STORAGE_PATH", storage_path)

    feedback = {
        "action": "like",
        "style": "简约",
        "color": "浅色",
        "categories": ["上衣"],
        "tags": ["通勤", "休闲"],
    }

    profile = update_user_pref(1, feedback)

    assert profile["feedback_count"] == 1
    assert profile["style_weights"]["简约"] > 0
    assert profile["color_weights"]["浅色"] > 0
    assert profile["category_weights"]["上衣"] > 0
    assert profile["tag_weights"]["通勤"] > 0

    loaded = get_user_preference_profile(1)
    assert loaded["feedback_count"] == 1
    assert loaded["style_weights"]["简约"] > 0


def test_negative_feedback_reduces_weight(tmp_path, monkeypatch):
    storage_path = tmp_path / "user_preferences.json"
    monkeypatch.setattr("backend.app.services.preference_learning._STORAGE_PATH", storage_path)

    update_user_pref(2, {"action": "like", "style": "时尚"})
    profile = update_user_pref(2, {"action": "dislike", "style": "时尚"})

    assert profile["style_weights"]["时尚"] == 0


def test_score_outfit_preference_matches_profile():
    profile = {
        "style_weights": {"简约": 1.0},
        "color_weights": {"浅色": 0.5},
        "category_weights": {"上衣": 1.0},
        "tag_weights": {"通勤": 0.5},
    }

    garments = [
        {"category": "上衣", "color": "浅色", "tags": ["简约", "通勤"]},
        {"category": "裤子", "color": "深色", "tags": ["基础款"]},
    ]

    score = score_outfit_preference(garments, profile)

    assert 0.5 <= score <= 1.0
