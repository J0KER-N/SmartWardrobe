"""测试使用百川大模型进行标签识别"""
import sys
import pathlib
import logging

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.services.ai_clients import extract_garment_tags

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    # 创建一个简单的测试图片（1x1像素的PNG）
    test_image = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
    
    print("="*60)
    print("测试百川大模型标签识别")
    print("="*60)
    
    try:
        tags = extract_garment_tags(test_image)
        print(f"[OK] 标签识别完成")
        print(f"识别到的标签: {tags}")
    except Exception as e:
        print(f"[ERROR] 标签识别失败: {str(e)}")
        logger.exception("详细错误信息")

if __name__ == '__main__':
    main()




