import os
import sys
import requests

LEFFA_ENDPOINT = os.environ.get('LEFFA_ENDPOINT', 'http://127.0.0.1:8000')
URL = LEFFA_ENDPOINT.rstrip('/') + '/predict/vt'
# Prefer local sample images if available to avoid external network issues
local_src = os.path.join(os.path.dirname(__file__), '..', 'uploads', 'avatars', '202512')
local_ref = os.path.join(os.path.dirname(__file__), '..', 'uploads', 'garments', '202512')

def first_file_in(dirpath):
    try:
        files = [f for f in os.listdir(dirpath) if os.path.isfile(os.path.join(dirpath, f))]
        files.sort()
        return os.path.join(dirpath, files[0]) if files else None
    except Exception:
        return None

SRC_IMG_LOCAL = first_file_in(local_src)
REF_IMG_LOCAL = first_file_in(local_ref)

SRC_IMG_URL = 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/89/Portrait_Placeholder.png/320px-Portrait_Placeholder.png'
REF_IMG_URL = 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/ac/No_image_available.svg/320px-No_image_available.svg'

out_dir = os.path.join(os.path.dirname(__file__), '..', 'uploads', 'tryon')
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, 'leffa_test_output.png')

print('POST', URL)
try:
    s = requests.Session()
    if SRC_IMG_LOCAL and REF_IMG_LOCAL:
        print('Using local images:', SRC_IMG_LOCAL, SRC_IMG_LOCAL)
        try:
            from PIL import Image
            from io import BytesIO
            # convert both images to PNG in-memory (some endpoints require PNG)
            im_a = Image.open(SRC_IMG_LOCAL).convert('RGBA')
            im_b = Image.open(REF_IMG_LOCAL).convert('RGBA')
            buf_a = BytesIO(); im_a.save(buf_a, format='PNG'); a_content = buf_a.getvalue()
            buf_b = BytesIO(); im_b.save(buf_b, format='PNG'); b_content = buf_b.getvalue()
            content_type = 'image/png'
        except Exception:
            # fallback: send raw bytes as jpeg
            with open(SRC_IMG_LOCAL, 'rb') as f:
                a_content = f.read()
            with open(REF_IMG_LOCAL, 'rb') as f:
                b_content = f.read()
            content_type = 'image/jpeg'
    else:
        print('Downloading remote images...')
        a = s.get(SRC_IMG_URL, timeout=15)
        a.raise_for_status()
        b = s.get(REF_IMG_URL, timeout=15)
        b.raise_for_status()
        a_content = a.content
        b_content = b.content

    files = {
        'src_image': ('src.png' if content_type=='image/png' else 'src.jpg', a_content, content_type),
        'ref_image': ('ref.png' if content_type=='image/png' else 'ref.jpg', b_content, content_type),
    }
    data = {
        'preprocess_garment': 'false',
        'step': '30',
        'scale': '2.5',
        'seed': '42',
        'vt_model_type': 'viton_hd',
        'vt_garment_type': 'upper_body'
    }
    print('Uploading images...')
    def do_post(data_override=None, attempt=1):
        d = dict(data)
        if data_override:
            d.update(data_override)
        print('\nAttempt', attempt, 'with data=', d)
        resp = s.post(URL, files=files, data=d, timeout=120)
        print('HTTP', resp.status_code)
        if resp.status_code == 200:
            ct = resp.headers.get('content-type', '')
            print('Content-Type:', ct)
            if 'image' in ct:
                path = out_path if attempt == 1 else out_path.replace('.png', f'_attempt{attempt}.png')
                with open(path, 'wb') as f:
                    f.write(resp.content)
                print('Saved image to', path, 'size=', os.path.getsize(path))
                return 0
            else:
                print('Response body (truncated):', resp.text[:1000])
                return 2
        else:
            print('Error body:', resp.text[:2000])
            return 3

    code = do_post(None, attempt=1)
    if code != 0:
        # try with preprocess enabled
        code = do_post({'preprocess_garment': 'true'}, attempt=2)
    sys.exit(code)
except Exception as e:
    print('Exception:', repr(e))
    sys.exit(4)
