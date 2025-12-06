from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, User
from app.security import get_password_hash
from app.config import get_settings

# 初始化数据库连接
settings = get_settings()
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_test_user():
    db = SessionLocal()
    try:
        # 检查用户是否已存在
        existing_user = db.query(User).filter(User.phone == "13800138000").first()
        if existing_user:
            print("测试用户已存在")
            return

        # 创建新用户
        test_user = User(
            phone="13800138000",  # 测试手机号
            nickname="测试用户",   # 昵称
            hashed_password=get_password_hash("Test123456"),  # 密码哈希处理
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        print(f"测试用户创建成功，ID: {test_user.id}")
    finally:
        db.close()

if __name__ == "__main__":
    create_test_user()