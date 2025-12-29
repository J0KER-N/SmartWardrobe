import httpx
import uuid
from app.config import get_settings
from jose import jwt

settings = get_settings()
API = 'http://127.0.0.1:8001'
phone = '139' + str(uuid.uuid4().int)[:8]
print('phone', phone)
resp = httpx.post(f'{API}/auth/register', json={'phone': phone, 'password': 'Test1234', 'nickname': 'dbg'})
print('status', resp.status_code)
print(resp.text[:1000])
if resp.status_code in (200, 201):
    data = resp.json()
    token = data['access_token']
    print('token', token)
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=['HS256'])
        print('decoded', payload)
    except Exception as e:
        print('decode error', type(e), e)
else:
    print('register failed')
