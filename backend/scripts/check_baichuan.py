"""检查百川大模型调用是否正常
检查推荐穿搭和衣物标签识别功能
"""
import sys
import pathlib
import logging
import os

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.services.ai_clients import summarize_outfit, extract_garment_tags, AIClientError
import httpx

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_config():
    """检查配置"""
    settings = get_settings()
    print("\n" + "="*60)
    print("配置检查")
    print("="*60)
    print(f"百川API密钥: {'已配置' if settings.baichuan_api_key else '未配置'}")
    print(f"百川API端点: {settings.baichuan_endpoint}")
    print(f"百川模型: {settings.baichuan_model}")
    print(f"FashionCLIP端点: {'已配置' if settings.fashionclip_endpoint else '未配置'}")
    print(f"Leffa端点: {'已配置' if settings.leffa_endpoint else '未配置'}")
    return settings

def test_baichuan_api(settings):
    """测试百川API连接"""
    print("\n" + "="*60)
    print("测试百川API连接")
    print("="*60)
    
    if not settings.baichuan_api_key:
        print("[WARN] 百川API密钥未配置，无法测试")
        return False
    
    try:
        # 测试简单的API调用
        payload = {
            "model": settings.baichuan_model,
            "messages": [
                {"role": "user", "content": "你好，请回复'测试成功'"}
            ],
            "temperature": 0.7,
            "max_tokens": 50
        }
        
        headers = {
            "Authorization": f"Bearer {settings.baichuan_api_key}",
            "Content-Type": "application/json"
        }
        
        print(f"正在调用: {settings.baichuan_endpoint}")
        print(f"使用模型: {settings.baichuan_model}")
        print(f"API密钥: {'已配置' if settings.baichuan_api_key else '未配置'}")
        
        # 尝试使用代理（百川API可能需要代理）
        print("尝试连接（使用系统代理）...")
        try:
            with httpx.Client(timeout=30, trust_env=True) as client:
                response = client.post(
                    settings.baichuan_endpoint,
                    json=payload,
                    headers=headers
                )
        except Exception as proxy_error:
            print(f"使用代理连接失败: {str(proxy_error)}")
            print("尝试直接连接（不使用代理）...")
            with httpx.Client(timeout=30, trust_env=False) as client:
                response = client.post(
                    settings.baichuan_endpoint,
                    json=payload,
                    headers=headers
                )
            
            print(f"响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                    result = response.json()
                    print("[OK] API调用成功")
                    print(f"响应结构: {list(result.keys())}")
                    
                    # 检查不同的响应格式
                    if "choices" in result:
                        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                        print(f"响应内容: {content}")
                    elif "output" in result:
                        content = result.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", "")
                        print(f"响应内容: {content}")
                    elif "data" in result:
                        print(f"响应数据: {result.get('data')}")
                    else:
                        print(f"完整响应: {result}")
                    
                    return True
            else:
                print(f"[ERROR] API调用失败: {response.status_code}")
                print(f"错误信息: {response.text}")
                return False
                
    except httpx.TimeoutException:
        print("[ERROR] 请求超时")
        return False
    except httpx.HTTPStatusError as e:
        print(f"[ERROR] HTTP错误: {e.response.status_code}")
        print(f"错误信息: {e.response.text}")
        return False
    except Exception as e:
        print(f"[ERROR] 连接失败: {str(e)}")
        return False

def test_summarize_outfit(settings):
    """测试穿搭描述生成"""
    print("\n" + "="*60)
    print("测试穿搭描述生成（推荐穿搭功能）")
    print("="*60)
    
    garments = [
        {"id": 1, "name": "牛仔外套", "category": "外套", "tags": ["休闲", "牛仔", "秋季"]},
        {"id": 2, "name": "白色衬衫", "category": "上衣", "tags": ["正式", "白色"]},
        {"id": 3, "name": "深色牛仔裤", "category": "裤装", "tags": ["休闲", "深色"]}
    ]
    weather = {"condition": "多云", "temp_c": 18}
    
    try:
        result = summarize_outfit(garments, weather)
        print(f"[OK] 生成成功")
        print(f"描述内容: {result}")
        return True
    except Exception as e:
        print(f"[ERROR] 生成失败: {str(e)}")
        logger.exception("详细错误信息")
        return False

def test_tag_extraction():
    """测试标签识别（FashionCLIP）"""
    print("\n" + "="*60)
    print("测试衣物标签识别（FashionCLIP）")
    print("="*60)
    
    settings = get_settings()
    if not settings.fashionclip_endpoint:
        print("[WARN] FashionCLIP端点未配置，跳过测试")
        print("注意：衣物标签识别使用的是FashionCLIP，不是百川大模型")
        return None
    
    # 创建一个简单的测试图片（1x1像素的PNG）
    test_image = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
    
    try:
        tags = extract_garment_tags(test_image)
        print(f"[OK] 标签识别成功")
        print(f"识别标签: {tags}")
        return True
    except Exception as e:
        print(f"[ERROR] 标签识别失败: {str(e)}")
        logger.exception("详细错误信息")
        return False

def main():
    print("\n" + "="*60)
    print("百川大模型调用检查")
    print("="*60)
    
    settings = check_config()
    
    # 测试百川API连接
    api_ok = test_baichuan_api(settings)
    
    # 测试穿搭描述生成
    outfit_ok = test_summarize_outfit(settings)
    
    # 测试标签识别（注意：这个不是百川，是FashionCLIP）
    tag_ok = test_tag_extraction()
    
    # 总结
    print("\n" + "="*60)
    print("检查总结")
    print("="*60)
    print(f"百川API连接: {'[OK] 正常' if api_ok else '[ERROR] 异常'}")
    print(f"推荐穿搭功能: {'[OK] 正常' if outfit_ok else '[ERROR] 异常'}")
    if tag_ok is not None:
        print(f"标签识别功能: {'[OK] 正常' if tag_ok else '[ERROR] 异常'}")
    else:
        print(f"标签识别功能: [WARN] 未配置（使用FashionCLIP，不是百川）")
    
    print("\n注意：")
    print("1. 推荐穿搭功能使用百川大模型生成描述文案")
    print("2. 衣物标签识别使用FashionCLIP，不是百川大模型")
    print("3. 如果百川API未配置，推荐穿搭会返回默认文案")

if __name__ == '__main__':
    main()

