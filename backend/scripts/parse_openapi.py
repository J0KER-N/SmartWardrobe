"""解析 Leffa 的 openapi.json，列出可能的生成接口候选。"""
import sys
import pathlib
import httpx
import json

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--host', default='http://127.0.0.1:7860')
args = parser.parse_args()

host = args.host.rstrip('/')
url = host + '/openapi.json'
print('Fetching', url)
try:
    r = httpx.get(url, timeout=10)
    r.raise_for_status()
    spec = r.json()
except Exception as e:
    print('Failed to fetch openapi.json:', e)
    sys.exit(1)

paths = spec.get('paths', {})
keywords = ['generate','predict','tryon','run','inference','model']

candidates = []
for path, methods in paths.items():
    for method, op in methods.items():
        lower = path.lower()
        summary = (op.get('summary') or '').lower()
        desc = (op.get('description') or '').lower()
        score = 0
        for k in keywords:
            if k in lower: score += 3
            if k in summary: score += 2
            if k in desc: score += 1
        # check requestBody content
        req = op.get('requestBody', {})
        content = req.get('content', {})
        content_types = list(content.keys())
        schema = None
        # attempt to extract schema properties
        try:
            media = next(iter(content.values()))
            schema = media.get('schema')
        except Exception:
            schema = None
        candidates.append({
            'path': path,
            'method': method.upper(),
            'summary': op.get('summary'),
            'description': op.get('description'),
            'content_types': content_types,
            'schema': schema,
            'score': score
        })

# sort by score desc
candidates = sorted(candidates, key=lambda x: x['score'], reverse=True)

print('\nTop candidate endpoints:')
for c in candidates[:20]:
    print('\n- PATH:', c['path'])
    print('  METHOD:', c['method'])
    print('  SCORE:', c['score'])
    print('  CONTENT-TYPES:', c['content_types'])
    if c['summary']:
        print('  SUMMARY:', c['summary'])
    if c['description']:
        print('  DESCRIPTION:', c['description'][:200])
    if c['schema']:
        print('  SCHEMA (snippet):', json.dumps(c['schema'])[:400])

print('\nAll paths scanned:', len(paths))
