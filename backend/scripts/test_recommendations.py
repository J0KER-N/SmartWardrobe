"""测试脚本：使用本地用户调用 /recommendations/daily 并打印结果
"""
import sys
import pathlib
import logging

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import os
import httpx
from app.config import get_settings
from jose import jwt
from app.database import SessionLocal, init_db
from app.models import Garment
from io import BytesIO
from PIL import Image
import random, string

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
# Prefer explicit env var, fallback to backend default
API_BASE = os.getenv('API_BASE_URL', 'http://127.0.0.1:8000')

def login(phone: str, password: str):
    with httpx.Client(timeout=30) as client:
        r = client.post(f'{API_BASE}/auth/login', json={'phone': phone, 'password': password})
        print('LOGIN', r.status_code)
        try:
            print(r.json())
        except Exception:
            print(r.text)
        if r.status_code not in (200, 201):
            raise SystemExit('登录失败')
        return r.json()['access_token']

def call_recommendations(token: str, city: str = 'Beijing'):
    headers = {'Authorization': f'Bearer {token}'}
    payload = {'city': city}
    with httpx.Client(timeout=60) as client:
        r = client.post(f'{API_BASE}/recommendations/daily', json=payload, headers=headers)
        print('RECOMMENDATIONS', r.status_code)
        try:
            print(r.json())
        except Exception:
            print(r.text)
        return r


def make_test_image(color=(200, 100, 100)) -> bytes:
    img = Image.new('RGB', (320, 320), color=color)
    bio = BytesIO()
    img.save(bio, format='JPEG')
    bio.seek(0)
    return bio.read()


def create_garment_in_db(owner_id: int):
    # 直接在数据库中插入一条衣物记录，避免触发自动标签识别（外部依赖）
    init_db()
    db = SessionLocal()
    try:
        garment = Garment(
            owner_id=owner_id,
            name='Test Jacket',
            category='外套',
            color='蓝',
            season='秋',
            image_url='/uploads/garments/placeholder.jpg',
            tags=['测试','自动']
        )
        db.add(garment)
        db.commit()
        db.refresh(garment)
        print('Inserted garment in DB id=', garment.id)
        return garment
    finally:
        db.close()

def main():
    phone = '13800000000'
    password = 'Test1234'
    print('Using API_BASE =', API_BASE)
    token = login(phone, password)
    # 解析 token 获取用户 id，然后直接在数据库中插入衣物（避免触发外部标签识别）
    try:
        decoded = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"], options={"verify_exp": False})
        owner_id = int(decoded.get('sub'))
    except Exception:
        print('无法解析 token 获取用户 id')
        return

    create_garment_in_db(owner_id)
    call_recommendations(token, city='Beijing')

if __name__ == '__main__':
    main()
