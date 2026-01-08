#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""诊断 Hugging Face API 连接问题"""
import sys
import pathlib
import logging
import httpx
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.config import get_settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_api_connection():
    """测试 Hugging Face API 连接"""
    settings = get_settings()
    
    print("="*60)
    print("Hugging Face API 诊断")
    print("="*60)
    
    # 检查配置
    print(f"\n1. 配置检查:")
    print(f"   API Key: {'已配置' if settings.huggingface_api_key else '❌ 未配置'}")
    if settings.huggingface_api_key:
        print(f"   API Key 前缀: {settings.huggingface_api_key[:10]}...")
    print(f"   模型: {settings.huggingface_leffa_model}")
    
    if not settings.huggingface_api_key:
        print("\n❌ 错误: 未配置 HUGGINGFACE_API_KEY")
        return
    
    # 测试API连接（使用新的 router 端点）
    api_url = f"https://router.huggingface.co/models/{settings.huggingface_leffa_model}"
    headers = {
        "Authorization": f"Bearer {settings.huggingface_api_key}",
        "Content-Type": "application/json"
    }
    
    print(f"\n2. API端点:")
    print(f"   URL: {api_url}")
    
    # 测试简单的请求
    print(f"\n3. 测试API连接:")
    try:
        # 先发送一个简单的测试请求（不包含图片）
        test_payload = {
            "inputs": "test"
        }
        
        print(f"   发送测试请求...")
        start_time = time.time()
        
        with httpx.Client(timeout=10.0) as client:
            response = client.post(api_url, json=test_payload, headers=headers)
            elapsed = time.time() - start_time
            
            print(f"   响应时间: {elapsed:.2f}秒")
            print(f"   状态码: {response.status_code}")
            print(f"   Content-Type: {response.headers.get('content-type', 'unknown')}")
            
            if response.status_code == 503:
                try:
                    error_info = response.json()
                    print(f"   ❌ 模型正在加载")
                    print(f"   错误信息: {error_info}")
                    if "estimated_time" in error_info:
                        print(f"   预计等待时间: {error_info['estimated_time']}秒")
                except:
                    print(f"   响应内容: {response.text[:200]}")
            elif response.status_code == 401:
                print(f"   ❌ 认证失败 - API Key 可能无效")
                print(f"   响应: {response.text[:200]}")
            elif response.status_code == 404:
                print(f"   ❌ 模型不存在: {settings.huggingface_leffa_model}")
            elif response.status_code == 200:
                print(f"   ✓ API连接正常")
            else:
                print(f"   响应: {response.text[:200]}")
                
    except httpx.TimeoutException:
        print(f"   ❌ 请求超时（10秒）")
        print(f"   可能原因: 网络问题或模型加载时间过长")
    except httpx.RequestError as e:
        print(f"   ❌ 连接失败: {str(e)}")
    except Exception as e:
        print(f"   ❌ 错误: {str(e)}")
    
    print(f"\n4. 建议:")
    if settings.huggingface_api_key:
        print(f"   - 检查 API Key 是否正确（访问 https://huggingface.co/settings/tokens）")
        print(f"   - 确认模型名称是否正确: {settings.huggingface_leffa_model}")
        print(f"   - 检查网络连接是否正常")
        print(f"   - 如果是首次调用，模型可能需要加载，请耐心等待")
        print(f"   - 查看后端日志获取更详细的错误信息")

if __name__ == '__main__':
    test_api_connection()

