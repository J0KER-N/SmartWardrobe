import os
from app.models import User
from app.security import get_password_hash


def test_admin_can_access_admin_ui(client, db_session):
    # 创建管理员用户（通过 DEV_ADMINS 环境变量授权）
    phone = "13900000001"
    admin = User(phone=phone, nickname="Admin User", hashed_password=get_password_hash("AdminPass123"))
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)

    # 设置 DEV_ADMINS 为该手机号
    os.environ["DEV_ADMINS"] = phone

    # 登录获取 token
    resp = client.post("/auth/login", data={"username": phone, "password": "AdminPass123"})
    assert resp.status_code == 200
    token = resp.json().get("access_token")
    assert token

    # 访问后台 UI
    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/admin/ui", headers=headers)
    assert r.status_code == 200
    assert "从镜子采集到版型决策" in r.text


def test_non_admin_forbidden(client, test_user):
    # 普通用户不能访问后台 UI
    resp = client.post("/auth/login", data={"username": test_user.phone, "password": "TestPassword123"})
    token = resp.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/admin/ui", headers=headers)
    assert r.status_code == 403
