import os
import requests

ROOT = os.path.dirname(__file__)
LEFFA_ENDPOINT = os.environ.get('LEFFA_ENDPOINT', 'http://127.0.0.1:8000')
URL = LEFFA_ENDPOINT.rstrip('/') + '/predict/vt'

SRC = os.path.join(ROOT, '..', 'uploads', 'avatars', '202512', '11_39564e163eaa41369153d64eea8a5cd4.jpg')
REF = os.path.join(ROOT, '..', 'uploads', 'garments', '202512', '11_226f7b8995a04682ae2bb14b0499fd40.jpg')

log_req = os.path.join(ROOT, '..', 'leffa_last_request.log')
log_resp = os.path.join(ROOT, '..', 'leffa_predict_last_response_500.txt')

data = {
    'preprocess_garment': 'false',
    'step': '30',
    'scale': '2.5',
    'seed': '42',
    'vt_model_type': 'viton_hd',
    'vt_garment_type': 'upper_body'
}

def write_request_log(req_info):
    with open(log_req, 'w', encoding='utf-8') as f:
        f.write(req_info)

def main():
    # prepare files as raw bytes (JPEG) to reproduce previous failure
    with open(SRC, 'rb') as f:
        src_bytes = f.read()
    with open(REF, 'rb') as f:
        ref_bytes = f.read()

    files = {
        'src_image': (os.path.basename(SRC), src_bytes, 'image/jpeg'),
        'ref_image': (os.path.basename(REF), ref_bytes, 'image/jpeg'),
    }

    req_info = []
    req_info.append('POST ' + URL) 
    req_info.append('Form data: ' + str(data))
    req_info.append('Files:')
    req_info.append(f"  src: {SRC} size={len(src_bytes)} bytes")
    req_info.append(f"  ref: {REF} size={len(ref_bytes)} bytes (sent as JPEG)")
    write_request_log('\n'.join(req_info))

    try:
        resp = requests.post(URL, files=files, data=data, timeout=120)
        with open(log_resp, 'w', encoding='utf-8') as f:
            f.write(f'HTTP {resp.status_code}\n')
            f.write('Headers: ' + str(dict(resp.headers)) + '\n')
            # if response is text, write first 2000 chars
            ctype = resp.headers.get('content-type','')
            if 'image' in ctype:
                outp = os.path.join(ROOT, '..', 'uploads', 'tryon', 'replay_500_output.png')
                with open(outp, 'wb') as of:
                    of.write(resp.content)
                f.write(f'Saved image to {outp} size={os.path.getsize(outp)}\n')
            else:
                body = resp.text
                f.write('Body:\n')
                f.write(body[:20000])
    except Exception as e:
        with open(log_resp, 'w', encoding='utf-8') as f:
            f.write('Exception: ' + repr(e) + '\n')

if __name__ == '__main__':
    main()
