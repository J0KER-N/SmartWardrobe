from pathlib import Path

from app.models import Garment, User
from app.services import agent_orchestrator as orchestrator
from app.services import metrics


def _create_garment(db_session, owner_id: int, name: str, category: str, color: str, tags: list[str]):
    garment = Garment(
        owner_id=owner_id,
        name=name,
        category=category,
        color=color,
        image_url=f"/uploads/{name}.png",
        tags=tags,
        season="夏",
    )
    db_session.add(garment)
    db_session.flush()
    return garment


def test_run_recommendation_pipeline_logs_show_event(db_session, test_user, monkeypatch, tmp_path):
    metrics_path = tmp_path / "metrics.log"
    monkeypatch.setattr(metrics, "_METRICS_PATH", metrics_path)
    monkeypatch.setattr(orchestrator, "get_weather", lambda city: {"temp_c": 26, "condition": "晴", "city": city})
    monkeypatch.setattr(orchestrator, "summarize_outfit", lambda garments, weather: "测试穿搭描述")
    monkeypatch.setattr(orchestrator, "generate_recommendation_reason", lambda garments, weather, style=None, color=None: "测试推荐理由")
    monkeypatch.setattr(orchestrator, "save_recommendation_preview", lambda image_urls, user_id: f"/uploads/previews/{user_id}.png")
    monkeypatch.setattr(orchestrator, "get_user_preference_profile", lambda user_id: {"style_weights": {}, "color_weights": {}, "category_weights": {}, "tag_weights": {}})

    _create_garment(db_session, test_user.id, "上衣A", "上衣", "白", ["简约", "通勤", "清凉"])
    _create_garment(db_session, test_user.id, "裤子B", "裤子", "黑", ["基础款", "清凉"])

    result = orchestrator.run_recommendation_pipeline(
        db=db_session,
        current_user=test_user,
        city="北京",
        allow_weather_fallback=False,
        allow_random_fallback=False,
    )

    assert result.weather["city"] == "北京"
    assert len(result.recommendations) >= 1
    assert result.recommendations[0].reason == "测试推荐理由"
    assert result.recommendations[0].confidence >= 0.45

    events = metrics.read_metrics()
    assert events
    assert events[-1]["event"] == "recommendation_show"
    assert events[-1]["user_id"] == test_user.id
    assert events[-1]["payload"]["city"] == "北京"


def test_metrics_helpers_write_events(tmp_path, monkeypatch):
    metrics_path = tmp_path / "metrics.log"
    monkeypatch.setattr(metrics, "_METRICS_PATH", metrics_path)

    metrics.log_recommendation_accept(1, {"outfit_id": 10})
    metrics.log_tryon_request(2, {"garment_id": 20})

    events = metrics.read_metrics()
    assert [event["event"] for event in events] == ["recommendation_accept", "tryon_request"]