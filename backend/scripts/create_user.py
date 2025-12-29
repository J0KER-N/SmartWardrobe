"""在本地数据库中创建用户（不经验证码流程）

用法：
    python scripts/create_user.py --phone 13800000000 --password Test1234 --nickname myuser

如果未提供参数，脚本会提示输入。
"""
import sys
import pathlib
import argparse

# Ensure backend/ is on sys.path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.database import SessionLocal, init_db
from app.models import User
from app.security import get_password_hash


def create_user(phone: str, password: str, nickname: str = "user"):
    # Ensure tables exist
    init_db()

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.phone == phone).first()
        if existing:
            print(f"手机号 {phone} 已存在，用户 id={existing.id}")
            return

        hashed = get_password_hash(password)
        user = User(phone=phone, hashed_password=hashed, nickname=nickname)
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"已创建用户 id={user.id}, phone={user.phone}, nickname={user.nickname}")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Create a user directly in the local DB")
    parser.add_argument("--phone", help="手机号，例如 138xxxxxx", required=False)
    parser.add_argument("--password", help="密码", required=False)
    parser.add_argument("--nickname", help="昵称", default="user")
    args = parser.parse_args()

    phone = args.phone
    password = args.password
    nickname = args.nickname

    if not phone:
        phone = input("请输入手机号 (e.g. 138xxxxxxxx): ").strip()
    if not password:
        password = input("请输入密码: ").strip()

    if not phone or not password:
        print("手机号和密码为必填项")
        return

    create_user(phone, password, nickname)


if __name__ == "__main__":
    main()
