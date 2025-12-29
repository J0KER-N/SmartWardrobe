"""测试脚本：直接调用 summarize_outfit 来验证百川大模型调用是否工作
"""
import sys
import pathlib
import logging

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.services.ai_clients import summarize_outfit, AIClientError
from app.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

def main():
    garments = [
        {"id": 1, "owner_id": 1, "name": "牛仔外套", "category": "外套", "tags": ["休闲", "牛仔"]},
        {"id": 2, "owner_id": 1, "name": "白色衬衫", "category": "上衣", "tags": ["正式", "白色"]}
    ]
    weather = {"condition": "多云", "temp_c": 18}

    print("Using BAICHUAN_ENDPOINT:", settings.baichuan_endpoint)
    print("Using BAICHUAN_API_KEY present:", bool(settings.baichuan_api_key))

    try:
        text = summarize_outfit(garments, weather)
        print("Baichuan response:\n", text)
    except Exception as e:
        logger.exception("百川调用失败")

if __name__ == '__main__':
    main()
