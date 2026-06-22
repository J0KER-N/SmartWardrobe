from app.database import engine, SessionLocal, Base
from app.models import User
from app.security import get_password_hash


def ensure_dev_admin(phone: str = "13900000001", password: str = "AdminPass123"):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.phone == phone).first()
        if existing:
            print("Dev admin already exists:", phone)
            return
        user = User(phone=phone, nickname="DevAdmin", hashed_password=get_password_hash(password))
        db.add(user)
        db.commit()
        print("Created dev admin:", phone)
    finally:
        db.close()


if __name__ == "__main__":
    ensure_dev_admin()
