import httpx, os, sys, time
from glob import glob
API='http://127.0.0.1:8001'
client=httpx.Client()
phone='19900000021'
password='Password123!'
print('registering...')
try:
    r=client.post(API+'/auth/register', json={'phone':phone,'password':password,'nickname':'tester'}, timeout=15)
    print('register', r.status_code, r.text[:500])
except Exception as e:
    print('register error', e)
    sys.exit(1)
if r.status_code!=201:
    r2=client.post(API+'/auth/login', json={'phone':phone,'password':password}, timeout=15)
    print('login', r2.status_code, r2.text[:500])
    if r2.status_code!=200:
        print('auth fail'); sys.exit(1)
    tokens=r2.json()
else:
    tokens=r.json()
access=tokens['access_token']
headers={'Authorization':f'Bearer {access}'}
# find sample files
garments=list(glob(os.path.join('uploads','garments','**','*.jpg'), recursive=True))+list(glob(os.path.join('uploads','garments','**','*.png'), recursive=True))
avatars=list(glob(os.path.join('uploads','avatars','**','*.jpg'), recursive=True))+list(glob(os.path.join('uploads','avatars','**','*.png'), recursive=True))
print('found', len(garments), 'garments,', len(avatars), 'avatars')
if not garments:
    print('no garment files found'); sys.exit(1)
if not avatars:
    print('no avatar files found'); sys.exit(1)
garment_image=garments[0]
avatar_image=avatars[0]
print('using files:', garment_image, avatar_image)
with open(garment_image,'rb') as gf:
    files={'file':('g.jpg', gf, 'image/jpeg')}
    data={'name':'t','category':'top','color':'red'}
    r=client.post(API+'/wardrobe/items', headers=headers, data=data, files=files, timeout=60)
    print('/wardrobe/items', r.status_code)
    print(r.text[:2000])
    if r.status_code!=201:
        sys.exit(1)
    gid=r.json()['id']
# call tryon
with open(avatar_image,'rb') as uf:
    files={'user_photo':('u.jpg', uf, 'image/jpeg')}
    data={'garment_id':str(gid)}
    print('calling tryon...')
    r=client.post(API+'/tryon/generate', headers=headers, data=data, files=files, timeout=120)
    print('/tryon/generate', r.status_code)
    print(r.text[:4000])
    if r.status_code==200:
        print('tryon response json keys:', list(r.json().keys()))
    print('done')
