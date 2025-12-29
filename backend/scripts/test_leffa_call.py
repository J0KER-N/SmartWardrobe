"""调用 LEFFA_ENDPOINT 进行快速连通性和响应格式检查"""
import sys
import pathlib
import logging

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.services.ai_clients import generate_tryon, AIClientError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

print('Using LEFFA_ENDPOINT =', settings.leffa_endpoint)

# 示例图片（公开可访问的小图）
USER_PHOTO = 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/89/Portrait_Placeholder.png/320px-Portrait_Placeholder.png'
GARMENT_IMAGE = 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/ac/No_image_available.svg/320px-No_image_available.svg'

try:
    result = generate_tryon(USER_PHOTO, GARMENT_IMAGE)
    print('Result type:', type(result))
    try:
        import json
        print('Result JSON snippet:', json.dumps(result)[:1000])
    except Exception:
        print('Result repr:', repr(result)[:1000])
except AIClientError as e:
    print('AIClientError:', str(e))
except Exception as e:
    print('Exception:', type(e), str(e))
