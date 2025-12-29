import os
import requests
from io import BytesIO

ROOT = os.path.dirname(__file__)
LEFFA_ENDPOINT = os.environ.get('LEFFA_ENDPOINT', 'http://127.0.0.1:8000')
URL = LEFFA_ENDPOINT.rstrip('/') + '/predict/vt'

SRC = os.path.join(ROOT, '..', 'uploads', 'avatars', '202512', '11_39564e163eaa41369153d64eea8a5cd4.jpg')
REF = os.path.join(ROOT, '..', 'uploads', 'garments', '202512', '11_226f7b8995a04682ae2bb14b0499fd40.jpg')

out_default = os.path.join('C:\\Windows\\Temp', 'resp_default.png')
out_pre = os.path.join('C:\\Windows\\Temp', 'resp_preproc.png')
log_default = os.path.join(ROOT, '..', 'leffa_predict_last_response_curl_default.txt')
log_pre = os.path.join(ROOT, '..', 'leffa_predict_last_response_curl_pre.txt')

def make_png_bytes(path):
    try:
        from PIL import Image
        im = Image.open(path).convert('RGBA')
        buf = BytesIO(); im.save(buf, format='PNG'); return buf.getvalue()
    except Exception:
        with open(path, 'rb') as f:
            return f.read()

def do_post(preprocess, out_path, log_path):
    files = {}
    # src -> png
    src_bytes = make_png_bytes(SRC)
    files['src_image'] = ('src.png', src_bytes, 'image/png')

    # ref
    if preprocess:
        ref_bytes = make_png_bytes(REF)
        files['ref_image'] = ('ref.png', ref_bytes, 'image/png')
    else:
        with open(REF, 'rb') as f:
            ref_bytes = f.read()
        files['ref_image'] = (os.path.basename(REF), ref_bytes, 'application/octet-stream')

    data = {
        'preprocess_garment': 'true' if preprocess else 'false',
        'step': '30',
        'scale': '2.5',
        'seed': '42',
        'vt_model_type': 'viton_hd',
        'vt_garment_type': 'upper_body'
    }

    with open(log_path, 'wb') as lf:
        try:
            print('POST', URL, 'preprocess=', preprocess)
            resp = requests.post(URL, files=files, data=data, timeout=120)
            lf.write(f'HTTP {resp.status_code}\n'.encode('utf-8'))
            lf.write(f'Headers: {resp.headers}\n'.encode('utf-8'))
            if resp.status_code == 200 and 'image' in resp.headers.get('content-type',''):
                with open(out_path, 'wb') as f:
                    f.write(resp.content)
                lf.write(f'Saved image to {out_path} size={os.path.getsize(out_path)}\n'.encode('utf-8'))
            else:
                body = resp.text
                lf.write(b'BODY:\n')
                lf.write(body.encode('utf-8', errors='replace'))
        except Exception as e:
            msg = repr(e) + '\n'
            lf.write(msg.encode('utf-8'))

if __name__ == '__main__':
    do_post(False, out_default, log_default)
    do_post(True, out_pre, log_pre)
