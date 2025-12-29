"""打印 openapi.json 中 PredictBody schema 的脚本

用法：
    python scripts/print_predict_schema.py --host http://127.0.0.1:7860
"""
import argparse
import httpx
import json

parser = argparse.ArgumentParser()
parser.add_argument('--host', default='http://127.0.0.1:7860')
args = parser.parse_args()

url = args.host.rstrip('/') + '/openapi.json'
print('Fetching', url)
try:
    r = httpx.get(url, timeout=10)
    r.raise_for_status()
    spec = r.json()
except Exception as e:
    print('Failed to fetch openapi.json:', e)
    raise SystemExit(1)

components = spec.get('components', {})
schemas = components.get('schemas', {})

for name in ['PredictBody','Body_predict_predict_post','Body_run_predict_post']:
    if name in schemas:
        print('\nSchema found:', name)
        print(json.dumps(schemas[name], indent=2, ensure_ascii=False)[:2000])
    else:
        print(f'\nSchema {name} not found')

# also dump any schema that references 'PredictBody'
refs = []
for k,v in schemas.items():
    s = json.dumps(v)
    if 'PredictBody' in s:
        refs.append(k)

if refs:
    print('\nSchemas referencing PredictBody:', refs)

print('\nDone')
