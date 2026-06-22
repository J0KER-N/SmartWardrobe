from app.models import Feedback, Garment, TryonRecord, User
from app.security import create_access_token, get_password_hash
from app.services.engagement_metrics import increment_garment_counter


def _create_garment(db_session, owner_id, name="测试上衣"):
    garment = Garment(
        owner_id=owner_id,
        name=name,
        category="上衣",
        color="白",
        image_url="http://example.com/garment.jpg",
        tags=["休闲", "夏季"],
        season="夏",
    )
    db_session.add(garment)
    db_session.commit()
    db_session.refresh(garment)
    return garment


def _create_tryon_record(db_session, owner_id, garment_id):
    record = TryonRecord(
        owner_id=owner_id,
        garment_id=garment_id,
        user_photo_url="http://example.com/user.jpg",
        tryon_image_url="http://example.com/tryon.jpg",
        tryon_status="success",
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    return record


def _auth_headers(user):
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


def test_profile_updates_body_metrics(client, test_user):
    response = client.put(
        "/profile/me",
        json={
            "nickname": "Body Tester",
            "height_cm": 178,
            "weight_kg": 68.5,
            "body_shape": "rectangle",
        },
        headers=_auth_headers(test_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["nickname"] == "Body Tester"
    assert data["height_cm"] == 178
    assert data["weight_kg"] == 68.5
    assert data["body_shape"] == "rectangle"


def test_tryon_counter_helper_updates_value(db_session, test_user):
    garment = _create_garment(db_session, test_user.id)

    increment_garment_counter(db_session, garment.id, "tryon_count", 1)
    db_session.commit()
    db_session.refresh(garment)

    assert garment.tryon_count == 1


def test_favorite_counter_syncs_with_favorites(client, db_session, test_user):
    garment = _create_garment(db_session, test_user.id)
    tryon_record = _create_tryon_record(db_session, test_user.id, garment.id)

    create_response = client.post(
        "/records/favorites",
        json={"tryon_record_id": tryon_record.id},
        headers=_auth_headers(test_user),
    )
    assert create_response.status_code == 201
    favorite_id = create_response.json()["id"]

    db_session.refresh(garment)
    assert garment.favorite_count == 1

    delete_response = client.delete(f"/records/favorites/{favorite_id}", headers=_auth_headers(test_user))
    assert delete_response.status_code == 200

    db_session.refresh(garment)
    assert garment.favorite_count == 0


def test_feedback_links_tryon_and_garment(client, db_session, test_user):
    garment = _create_garment(db_session, test_user.id)
    tryon_record = _create_tryon_record(db_session, test_user.id, garment.id)

    response = client.post(
        "/feedback/",
        json={
            "action": "fit",
            "tryon_record_id": tryon_record.id,
            "fit_status": "too_small",
            "meta": {"note": "shoulder tight"},
        },
        headers=_auth_headers(test_user),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["tryon_record_id"] == tryon_record.id
    assert data["garment_id"] == garment.id
    assert data["fit_status"] == "too_small"

    feedback = db_session.query(Feedback).filter(Feedback.id == data["id"]).first()
    assert feedback is not None
    assert feedback.garment_id == garment.id
    assert feedback.tryon_record_id == tryon_record.id


def test_analytics_overview_returns_metrics(client, db_session, test_user):
    garment = _create_garment(db_session, test_user.id)
    garment.tryon_count = 4
    garment.favorite_count = 2
    db_session.commit()
    db_session.refresh(garment)

    second_user = User(
        phone="13900139001",
        nickname="Second User",
        hashed_password=get_password_hash("TestPassword123"),
        height_cm=165,
        weight_kg=54.2,
        body_shape="pear",
    )
    db_session.add(second_user)
    db_session.commit()

    feedback = Feedback(
        owner_id=test_user.id,
        garment_id=garment.id,
        action="fit",
        fit_status="fit",
        fit_source="online",
        meta={"fit_status": "fit"},
    )
    db_session.add(feedback)
    db_session.commit()

    offline_feedback = Feedback(
        owner_id=test_user.id,
        garment_id=garment.id,
        action="fit",
        fit_status="too_small",
        fit_source="offline",
        garment_size="M",
        body_snapshot={"height_cm": 176, "weight_kg": 67, "body_shape": "rectangle"},
        meta={"fit_status": "too_small", "garment_size": "M"},
    )
    db_session.add(offline_feedback)
    db_session.commit()

    response = client.get("/analytics/overview", headers=_auth_headers(test_user))
    assert response.status_code == 200
    data = response.json()

    assert data["user_metrics"]["total_users"] >= 2
    assert any(item["body_shape"] == "pear" for item in data["user_metrics"]["body_shape_distribution"])
    assert data["garment_metrics"]["top_tryon_garments"][0]["tryon_count"] == 4
    assert data["fit_feedback_metrics"]["fit_feedback_count"] >= 1
    assert data["fit_feedback_metrics"]["online_fit_feedback_count"] >= 1
    assert data["fit_feedback_metrics"]["offline_fit_feedback_count"] >= 1
    assert any(item["garment_size"] == "M" for item in data["fit_feedback_metrics"]["garment_size_distribution"])
    assert any(item["fit_status"] == "too_small" for item in data["fit_feedback_metrics"]["offline_fit_status_distribution"])
