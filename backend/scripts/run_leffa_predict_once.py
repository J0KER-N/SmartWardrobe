import os
import sys
import argparse
import requests
from io import BytesIO

parser = argparse.ArgumentParser()
parser.add_argument('--preprocess', action='store_true')
args = parser.parse_args()

ROOT = os.path.dirname(__file__)
LEFFA_ENDPOINT = os.environ.get('LEFFA_ENDPOINT', 'http://127.0.0.1:8000')
URL = LEFFA_ENDPOINT.rstrip('/') + '/predict/vt'

local_src = os.path.join(ROOT, '..', 'uploads', 'avatars', '202512')
local_ref = os.path.join(ROOT, '..', 'uploads', 'garments', '202512')

def first_file_in(dirpath):
    try:
        files = [f for f in os.listdir(dirpath) if os.path.isfile(os.path.join(dirpath, f))]
        files.sort()
        return os.path.join(dirpath, files[0]) if files else None
    except Exception:
        return None

SRC_IMG_LOCAL = first_file_in(local_src)
REF_IMG_LOCAL = first_file_in(local_ref)

out_dir = os.path.join(ROOT, '..', 'uploads', 'tryon')
os.makedirs(out_dir, exist_ok=True)

def make_files(preprocess):
    # load content
    if not SRC_IMG_LOCAL or not REF_IMG_LOCAL:
        raise SystemExit('Local images not found')
    # ensure ref is PNG if preprocess
    if preprocess:
        try:
            from PIL import Image
            im = Image.open(REF_IMG_LOCAL).convert('RGBA')
            buf = BytesIO(); im.save(buf, format='PNG'); ref_bytes = buf.getvalue()
            ref_name = 'ref.png'
            ref_ct = 'image/png'
        except Exception:
            with open(REF_IMG_LOCAL, 'rb') as f:
                ref_bytes = f.read()
            ref_name = os.path.basename(REF_IMG_LOCAL)
            ref_ct = 'application/octet-stream'
    else:
        with open(REF_IMG_LOCAL, 'rb') as f:
            ref_bytes = f.read()
        ref_name = os.path.basename(REF_IMG_LOCAL)
        ref_ct = 'application/octet-stream'

    # source image convert to PNG if possible
    try:
        from PIL import Image
        im = Image.open(SRC_IMG_LOCAL).convert('RGBA')
        buf = BytesIO(); im.save(buf, format='PNG'); src_bytes = buf.getvalue()
        src_name = 'src.png'
        src_ct = 'image/png'
    except Exception:
        with open(SRC_IMG_LOCAL, 'rb') as f:
            src_bytes = f.read()
        src_name = os.path.basename(SRC_IMG_LOCAL)
        src_ct = 'application/octet-stream'

    files = {
        'src_image': (src_name, src_bytes, src_ct),
        'ref_image': (ref_name, ref_bytes, ref_ct),
    }
    return files

data = {
    'preprocess_garment': 'true' if args.preprocess else 'false',
    'step': '30',
    'scale': '2.5',
    'seed': '42',
    'vt_model_type': 'viton_hd',
    'vt_garment_type': 'upper_body'
}

print('POST', URL, 'preprocess=', args.preprocess)
files = make_files(args.preprocess)
try:
    resp = requests.post(URL, files=files, data=data, timeout=120)
    print('HTTP', resp.status_code)
    if resp.status_code == 200:
        ct = resp.headers.get('content-type','')
        print('Content-Type:', ct)
        if 'image' in ct:
            suffix = 'pre' if args.preprocess else 'def'
            out_path = os.path.join(out_dir, f'leffa_output_{suffix}.png')
            with open(out_path, 'wb') as f:
                f.write(resp.content)
            print('Saved', out_path, os.path.getsize(out_path))
            sys.exit(0)
        else:
            print('Body:', resp.text[:2000])
            sys.exit(2)
    else:
        print('Error body:', resp.text[:2000])
        sys.exit(3)
except Exception as e:
    print('Exception:', repr(e))
    sys.exit(4)
