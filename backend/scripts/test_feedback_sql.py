import sys
import os

# 将 backend 根目录放入 sys.path 以便导入 app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import User, UserFeedback
from datetime import datetime

def test_insert_feedback():
    db = SessionLocal()
    try:
        # 创建或获取一个测试用户
        user = db.query(User).first()
        if not user:
            user = User(phone="13800000002", hashed_password="mock", nickname="测试反馈用户")
            db.add(user)
            db.commit()
            db.refresh(user)

        # 插入反馈记录
        fb = UserFeedback(
            user_id=user.id,
            item_id="item_1",
            event_type="like",
            context={"source": "recommendation_list"},
            timestamp=datetime.utcnow()
        )
        db.add(fb)
        db.commit()
        db.refresh(fb)
        
        print(f"成功插入反馈记录！ID={fb.id}, user_id={fb.user_id}, item_id={fb.item_id}, event_type={fb.event_type}")

        # 查询
        records = db.query(UserFeedback).filter(UserFeedback.user_id == user.id).all()
        print(f"当前用户共有 {len(records)} 条反馈记录：")
        for r in records:
            print(f"  - [{r.id}] {r.event_type} on {r.item_id} at {r.timestamp}")
            
    finally:
        db.close()

if __name__ == "__main__":
    test_insert_feedback()
