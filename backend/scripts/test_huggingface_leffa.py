"""测试 Hugging Face Leffa 模型调用"""
import sys
import pathlib
import logging

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.services.ai_clients import generate_tryon, AIClientError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    settings = get_settings()
    
    print("="*60)
    print("测试 Hugging Face Leffa 模型")
    print("="*60)
    print(f"Hugging Face API Key: {'已配置' if settings.huggingface_api_key else '未配置'}")
    print(f"Leffa 模型: {settings.huggingface_leffa_model}")
    
    if not settings.huggingface_api_key:
        print("[ERROR] 请先配置 HUGGINGFACE_API_KEY 环境变量")
        return
    
    # 使用测试图片URL（需要替换为实际的图片URL）
    test_user_photo = "https://picsum.photos/seed/user/400/600"
    test_garment_image = "https://picsum.photos/seed/garment/400/600"
    
    print(f"\n测试参数:")
    print(f"用户照片: {test_user_photo}")
    print(f"衣物图片: {test_garment_image}")
    
    try:
        result = generate_tryon(test_user_photo, test_garment_image)
        print(f"\n[OK] 调用成功")
        print(f"返回结果类型: {type(result)}")
        if isinstance(result, dict) and "image_data" in result:
            print(f"图片数据大小: {len(result['image_data'])} 字节")
    except AIClientError as e:
        print(f"\n[ERROR] 调用失败: {str(e)}")
    except Exception as e:
        print(f"\n[ERROR] 异常: {str(e)}")
        logger.exception("详细错误信息")

if __name__ == '__main__':
    main()




