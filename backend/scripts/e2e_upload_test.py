"""端到端上传测试脚本

前提：后端服务正在运行（默认 http://127.0.0.1:8000）
依赖：在 backend 虚拟环境中安装 `httpx` 与 `Pillow`（项目 requirements 已包含）

用法：
    python scripts/e2e_upload_test.py

此脚本会：
- 注册一个临时测试用户并获取 access token
- 使用 access token 上传一张模拟生成的图片作为衣物
- 上传头像
- 尝试调用 /tryon/generate（以 multipart 上传 user_photo）

注意：脚本用于本地 smoke 测试，非完整集成测试。
"""
import os
import random
import string
import json
import sys
import pathlib

# Ensure project root (backend/) is on sys.path so `from app import ...` works
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from io import BytesIO
from PIL import Image
import httpx
from jose import jwt
from jose.exceptions import ExpiredSignatureError
from app.config import get_settings


API_BASE = os.getenv('API_BASE_URL', 'http://127.0.0.1:8000')
# 如果默认端口需要改为 8001，可在此处硬编码覆盖（用于调试）



def random_phone():
    # 生成符合 ^1[3-9]\d{9}$ 的手机号（中国手机号样式）
    return '138' + ''.join(random.choice(string.digits) for _ in range(8))


def make_test_image(color=(200, 100, 100)) -> bytes:
    img = Image.new('RGB', (320, 320), color=color)
    bio = BytesIO()
    img.save(bio, format='JPEG')
    bio.seek(0)
    return bio.read()


def register_and_get_token(client: httpx.Client):
    phone = random_phone()
    password = 'Test1234'
    payload = {
        'phone': phone,
        'password': password,
        'nickname': 'e2e_test'
    }
    r = client.post(f'{API_BASE}/auth/register', json=payload)
    print('REGISTER', r.status_code, r.text)
    if r.status_code not in (200, 201):
        raise SystemExit('注册失败，先确认后端 /auth/register 可用')
    data = r.json()
    # 本地尝试解码返回的 token 以验证签名/exp 格式
    settings = get_settings()
    try:
        # 先尝试严格解码（包括 exp 校验）以便捕捉格式问题
        decoded = jwt.decode(data['access_token'], settings.jwt_secret_key, algorithms=['HS256'])
        print('LOCAL DECODE OK ->', decoded)
    except ExpiredSignatureError as e:
        # token 可能已过期（或系统时钟不同步），尝试允许过期以获取 payload 用于调试
        print('LOCAL DECODE EXPIRED ->', e)
        try:
            decoded = jwt.decode(data['access_token'], settings.jwt_secret_key, algorithms=['HS256'], options={"verify_exp": False})
            print('LOCAL DECODE (unverified exp) ->', decoded)
        except Exception as e2:
            print('LOCAL DECODE FAILED ->', type(e2), e2)
    except Exception as e:
        print('LOCAL DECODE FAILED ->', type(e), e)

    return data['access_token'], data['refresh_token'], phone, password


def create_garment(client: httpx.Client, token: str):
    headers = {'Authorization': f'Bearer {token}'}
    print('>> create_garment headers:', headers)
    img_bytes = make_test_image()
    files = {
        'file': ('garment.jpg', img_bytes, 'image/jpeg')
    }
    data = {
        'name': 'E2E Test Shirt',
        'category': '上衣',
        'color': '红',
        'season': '夏',
        'manual_tags': '测试,自动'
    }
    r = client.post(f'{API_BASE}/wardrobe/items', data=data, files=files, headers=headers)
    print('CREATE GARMENT', r.status_code)
    try:
        print(r.json())
    except Exception:
        print(r.text)
    return r


def upload_avatar(client: httpx.Client, token: str):
    headers = {'Authorization': f'Bearer {token}'}
    print('>> upload_avatar headers:', headers)
    img_bytes = make_test_image(color=(50, 150, 200))
    files = {'file': ('avatar.jpg', img_bytes, 'image/jpeg')}
    r = client.post(f'{API_BASE}/profile/avatar', files=files, headers=headers)
    print('UPLOAD AVATAR', r.status_code)
    try:
        print(r.json())
    except Exception:
        print(r.text)
    return r


def generate_tryon(client: httpx.Client, token: str, garment_id: int):
    headers = {'Authorization': f'Bearer {token}'}
    print('>> generate_tryon headers:', headers)
    # 尝试以 multipart 方式上传 user_photo
    img_bytes = make_test_image(color=(20, 180, 90))
    files = {'user_photo': ('user.jpg', img_bytes, 'image/jpeg')}
    data = {'garment_id': str(garment_id)}
    r = client.post(f'{API_BASE}/tryon/generate', data=data, files=files, headers=headers)
    print('TRYON GENERATE', r.status_code)
    try:
        print(r.json())
    except Exception:
        print(r.text)
    return r


def main():
    print('API_BASE =', API_BASE)
    with httpx.Client(timeout=30) as client:
        try:
            access, refresh, phone, pwd = register_and_get_token(client)
        except SystemExit as e:
            print(e)
            return

        # 上传衣物
        r = create_garment(client, access)
        garment_id = None
        try:
            if r.status_code in (200, 201):
                body = r.json()
                # 若返回的是模型实例（dict），尝试读取 id
                garment_id = body.get('id') or (body[0].get('id') if isinstance(body, list) and body else None)
        except Exception:
            pass

        # 上传头像
        upload_avatar(client, access)

        # 生成试穿（如果有 garment_id）
        if garment_id:
            generate_tryon(client, access, garment_id)
        else:
            print('未能获取 garment_id，跳过 tryon 生成')


if __name__ == '__main__':
    main()
