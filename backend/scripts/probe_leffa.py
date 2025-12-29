"""探测 Leffa 部署常见 API 路径的脚本

用法：
    python scripts/probe_leffa.py --host http://127.0.0.1:7860

会尝试 GET /openapi.json /docs /api/docs 等，以及对若干常见 POST 路径发送示例 JSON，打印状态码与部分响应。
"""
import argparse
import httpx
import json

COMMON_GET_PATHS = [
    "/", "/docs", "/openapi.json", "/api/docs", "/swagger.json", "/swagger-ui.html"
]

COMMON_POST_PATHS = [
    "/generate", "/api/generate", "/api/predict", "/predict", "/run/predict", "/api/v1/generate", "/model/predict"
]

SAMPLE_JSON = {
    "user_photo": "https://example.com/user.jpg",
    "garment_image": "https://example.com/garment.jpg"
}

TIMEOUT = 10


def probe(host: str):
    client = httpx.Client(timeout=TIMEOUT)
    print(f"Probing host: {host}")

    # GET paths
    for p in COMMON_GET_PATHS:
        url = host.rstrip('/') + p
        try:
            r = client.get(url)
            print(f"GET {p} -> {r.status_code}")
            if r.headers.get('content-type','').startswith('application/json'):
                try:
                    data = r.json()
                    print('  JSON keys:', list(data.keys())[:10])
                except Exception:
                    print('  <json parse failed>')
            else:
                text = r.text[:300].replace('\n',' ')
                print('  text:', text)
        except Exception as e:
            print(f"GET {p} -> ERROR: {e}")

    # POST paths (JSON)
    for p in COMMON_POST_PATHS:
        url = host.rstrip('/') + p
        try:
            r = client.post(url, json=SAMPLE_JSON)
            print(f"POST {p} -> {r.status_code}")
            ct = r.headers.get('content-type','')
            if 'json' in ct:
                try:
                    data = r.json()
                    keys = list(data.keys()) if isinstance(data, dict) else None
                    print('  JSON keys sample:', keys)
                    # print small snippet
                    print('  JSON snippet:', json.dumps(data)[:500])
                except Exception:
                    print('  <json parse failed>')
            else:
                print('  text snippet:', r.text[:500].replace('\n',' '))
        except Exception as e:
            print(f"POST {p} -> ERROR: {e}")

    client.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='http://127.0.0.1:7860')
    args = parser.parse_args()
    probe(args.host)
