from fastapi import FastAPI, Request
import base64
from pathlib import Path

app = FastAPI()

@app.post('/generate')
async def generate(request: Request):
    # 返回一个固定的示例试穿图片（base64）
    img_path = Path(__file__).parent / 'uploads' / 'tryon' / 'leffa_test_output.png'
    if not img_path.exists():
        return {"error": "no sample image"}
    data = img_path.read_bytes()
    return {"image_data": base64.b64encode(data).decode()}
