import httpx
import logging
import os
import time
from typing import Dict, List, Optional
from pydantic import BaseModel
import base64

from ..config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# 自定义异常
class AIClientError(Exception):
    """AI服务基础异常"""
    pass

class AIClientTimeoutError(AIClientError):
    """超时异常"""
    pass

class AIClientRateLimitError(AIClientError):
    """限流异常"""
    pass

class AIClientInvalidRequestError(AIClientError):
    """请求参数错误"""
    pass

# 通用请求工具
async def _async_post_json(
    url: str,
    payload: dict,
    headers: Optional[dict] = None,
    timeout: int = 60
) -> Dict:
    """异步POST请求（用于高并发场景）"""
    if not url:
        raise AIClientError("AI服务地址未配置")
    
    headers = headers or {}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        raise AIClientTimeoutError(f"请求超时（{timeout}秒）")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            raise AIClientRateLimitError("请求频率超限")
        elif e.response.status_code == 400:
            raise AIClientInvalidRequestError(f"请求参数错误: {e.response.text}")
        else:
            raise AIClientError(f"服务错误: {e.response.status_code} - {e.response.text}")
    except httpx.RequestError as e:
        raise AIClientError(f"连接失败: {str(e)}")

def _sync_post_json(
    url: str,
    payload: dict,
    headers: Optional[dict] = None,
    timeout: int = 60,
    max_retries: int = 3,
    use_proxy: bool = False,
) -> Dict:
    """同步 POST 请求，带简单重试和错误处理。
    
    Args:
        url: 请求URL
        payload: 请求体
        headers: 请求头
        timeout: 超时时间（秒）
        max_retries: 最大重试次数
        use_proxy: 是否使用系统代理（默认False，直接连接）
    """
    if not url:
        raise AIClientError("AI服务地址未配置")

    headers = headers or {}
    last_error: Optional[Exception] = None

    for attempt in range(max_retries):
        try:
            # 每次重试适当增加超时时间
            retry_timeout = timeout * (attempt + 1) if attempt > 0 else timeout

            # 根据 use_proxy 参数决定是否使用代理
            # 对于外部API（如百川），可能需要代理；对于本地服务，不使用代理
            client_kwargs = {
                "timeout": retry_timeout,
                "follow_redirects": True,
                "trust_env": use_proxy  # 如果 use_proxy=True，则信任环境变量中的代理设置
            }
            
            with httpx.Client(**client_kwargs) as client:
                logger.debug(f"发送请求到 {url} (尝试 {attempt + 1}/{max_retries}, 超时: {retry_timeout}秒, 代理: {use_proxy})")
                response = client.post(url, json=payload, headers=headers)

            logger.debug(
                f"收到响应: 状态码={response.status_code}, "
                f"Content-Type={response.headers.get('content-type', 'unknown')}"
            )

            # 处理 503（例如模型正在加载）
            if response.status_code == 503:
                try:
                    if response.headers.get("content-type", "").startswith("application/json"):
                        error_info = response.json()
                    else:
                        error_info = {}
                except Exception:
                    error_info = {}

                estimated_time = error_info.get("estimated_time", 30)
                error_msg = error_info.get("error", "模型正在加载")
                logger.warning(f"API 返回 503: {error_msg}, 预计等待时间: {estimated_time} 秒")

                if attempt < max_retries - 1:
                    wait_time = min(estimated_time, 60)
                    logger.info(f"等待 {wait_time} 秒后重试（尝试 {attempt + 1}/{max_retries}）")
                    time.sleep(wait_time)
                    continue
                else:
                    raise AIClientError(
                        f"模型加载超时，请稍后重试。错误信息: {error_info.get('error', '未知错误')}"
                    )

            # 非 200 状态码，记录错误内容
            if response.status_code != 200:
                error_text = response.text[:500]
                logger.error(f"API 返回错误状态码 {response.status_code}: {error_text}")

            # 如果状态码是错误，将抛出 HTTPStatusError
            response.raise_for_status()

            # 根据 Content-Type 解析响应
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                result = response.json()
                logger.debug(f"收到 JSON 响应，大小: {len(str(result))} 字符")
                return result
            elif "image" in content_type:
                logger.info("收到图片响应")
                return {"image_data": response.content}
            else:
                # 尝试解析 JSON，失败则返回原始文本
                try:
                    return response.json()
                except Exception:
                    logger.warning(f"无法解析响应为 JSON，Content-Type: {content_type}")
                    return {"raw": response.text[:1000]}

        except httpx.TimeoutException:
            last_error = AIClientTimeoutError(f"请求超时（{retry_timeout}秒）")
            if attempt < max_retries - 1:
                logger.warning(f"请求超时，重试中（尝试 {attempt + 1}/{max_retries}）")
                continue
            else:
                raise last_error
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            if status_code == 429:
                raise AIClientRateLimitError("请求频率超限")
            elif status_code == 400:
                raise AIClientInvalidRequestError(f"请求参数错误: {e.response.text}")
            elif status_code == 404:
                error_text = e.response.text[:500] if e.response.text else "Not Found"
                logger.error(f"模型或端点不存在 (404): {error_text}")
                raise AIClientError(
                    f"模型或端点不存在 (404)。请检查模型名称是否正确，"
                    f"或该模型是否支持 Inference API。模型: {getattr(settings, 'huggingface_leffa_model', 'unknown')}, "
                    f"错误: {error_text}"
                )
            else:
                raise AIClientError(f"服务错误: {status_code} - {e.response.text}")
        except httpx.RequestError as e:
            # 连接错误
            error_str = str(e)
            if attempt < max_retries - 1:
                logger.warning(f"连接失败，重试中（尝试 {attempt + 1}/{max_retries}）")
                time.sleep(2)
                last_error = AIClientError(f"连接失败: {error_str}")
                continue
            else:
                raise AIClientError(f"连接失败: {error_str}")

    # 如果所有重试都失败
    if last_error:
        raise last_error
    raise AIClientError("请求失败，未知错误")

# ------------------------------ 虚拟试穿（仅使用自建云端 Leffa 服务） ------------------------------
def generate_tryon(user_photo_url: str, garment_image_url: str) -> Dict:
    """生成虚拟试穿图片（只调用自建云端 Leffa /virtual_tryon 接口）"""
    # 必须配置自建 Leffa 虚拟试穿服务 URL
    # 在 .env 中设置：LEFFA_VIRTUAL_TRYON_URL=http://your-server:8000/virtual_tryon
    return _generate_tryon_custom_leffa(user_photo_url, garment_image_url)


def _generate_tryon_huggingface(user_photo_url: str, garment_image_url: str) -> Dict:
    """使用 Hugging Face Inference API 生成虚拟试穿图片"""
    if not settings.huggingface_api_key:
        raise AIClientError("Hugging Face API Key未配置，请在环境变量中设置 HUGGINGFACE_API_KEY")
    
    # Hugging Face Inference API 端点
    # 优先使用自定义端点 URL（如果配置了）
    endpoint_url = os.getenv("HUGGINGFACE_ENDPOINT_URL")
    if endpoint_url:
        api_url = endpoint_url
        logger.info(f"使用自定义 Inference Endpoint: {api_url}")
    else:
        # 使用标准的 Inference API 端点
        # 注意：Hugging Face 已弃用 api-inference.huggingface.co，必须使用 router.huggingface.co
        # 尝试两种可能的端点格式
        api_url = f"https://router.huggingface.co/hf-inference/models/{settings.huggingface_leffa_model}"
    
    # 如果模型不存在，尝试使用 Inference API 的备用端点
    # 注意：某些模型可能需要使用 Inference Endpoints 而不是 Inference API
    
    headers = {
        "Authorization": f"Bearer {settings.huggingface_api_key}",
        "Content-Type": "application/json"
    }
    
    # 构建完整的图片URL（如果是相对路径，需要转换为完整URL）
    # 注意：当前后端运行在 8001 端口，这里默认也指向 8001；
    # 如果以后端口有变，可以在 .env 中显式配置 API_BASE_URL 覆盖。
    api_base_url = os.getenv("API_BASE_URL", "http://127.0.0.1:8001")
    
    def _get_full_url(url: str) -> str:
        """将相对路径转换为完整URL"""
        if url.startswith("http"):
            return url
        # 如果是相对路径，拼接基础URL
        if url.startswith("/"):
            return f"{api_base_url}{url}"
        return f"{api_base_url}/{url}"
    
    full_user_photo_url = _get_full_url(user_photo_url)
    full_garment_image_url = _get_full_url(garment_image_url)
    
    # Hugging Face API 的 payload 格式
    # 对于图片输入，Hugging Face API 通常支持：
    # 1. 直接发送图片 URL
    # 2. 发送 base64 编码的图片
    # 3. 使用 multipart/form-data（需要特殊处理）
    
    # 下载图片并转换为 base64（Hugging Face API 需要 base64 编码的图片）
    try:
        # 不使用代理，直接连接下载图片
        with httpx.Client(timeout=30.0) as client:
            # 下载用户照片
            logger.info(f"下载用户照片: {full_user_photo_url}")
            user_response = client.get(full_user_photo_url, timeout=30.0)
            user_response.raise_for_status()
            user_image_data = user_response.content
            
            # 下载衣物图片
            logger.info(f"下载衣物图片: {full_garment_image_url}")
            garment_response = client.get(full_garment_image_url, timeout=30.0)
            garment_response.raise_for_status()
            garment_image_data = garment_response.content
        
        # 转换为 base64
        user_image_base64 = base64.b64encode(user_image_data).decode('utf-8')
        garment_image_base64 = base64.b64encode(garment_image_data).decode('utf-8')
        
        # Hugging Face Inference API 的正确格式
        # 对于多图片输入，需要根据模型的具体要求来构造
        # OOTDiffusion 模型通常需要两个图片输入：人物图片和衣物图片
        # 尝试多种格式以确保兼容性
        
        # 格式1：直接使用 base64 字符串（某些模型支持）
        # 格式2：使用字典格式（某些模型需要）
        # 格式3：使用数组格式（某些模型需要）
        
        # Hugging Face Inference API 的正确格式
        # 根据 Hugging Face 文档，对于图片输入，应该直接使用 base64 字符串
        # 但对于多图片输入，可能需要使用不同的格式
        # 尝试使用标准的 inputs 格式
        
        # 根据模型类型调整 payload 格式
        # facebook/leffa 模型可能需要不同的参数格式
        if "facebook/leffa" in settings.huggingface_leffa_model.lower():
            # facebook/leffa 模型可能需要特定的参数格式
            # 尝试使用数组格式或字典格式
            payload = {
                "inputs": {
                    "person_image": user_image_base64,  # 不带 data URI 前缀
                    "garment_image": garment_image_base64  # 不带 data URI 前缀
                }
            }
        else:
            # 其他模型使用标准格式
            payload = {
                "inputs": {
                    "person_image": user_image_base64,  # 不带 data URI 前缀
                    "garment_image": garment_image_base64  # 不带 data URI 前缀
                }
            }
        
        logger.info("已下载图片并转换为base64格式")
        logger.info(f"用户图片大小: {len(user_image_data)} 字节, 衣物图片大小: {len(garment_image_data)} 字节")
        logger.info(f"Base64编码后大小: 用户={len(user_image_base64)} 字符, 衣物={len(garment_image_base64)} 字符")
        
    except Exception as e:
        logger.error(f"下载图片失败: {str(e)}")
        raise AIClientError(f"无法下载图片: {str(e)}")
    
    logger.info(f"调用Hugging Face Leffa模型 | 用户图片: {full_user_photo_url} | 衣物图片: {full_garment_image_url}")
    logger.info(f"使用模型: {settings.huggingface_leffa_model}")
    logger.info(f"API URL: {api_url}")
    
    # 如果使用默认端点，尝试多个可能的端点格式
    endpoint_urls_to_try = []
    if not endpoint_url:
        # 尝试多种端点格式（注意：api-inference.huggingface.co 已被弃用，不再使用）
        endpoint_urls_to_try = [
            f"https://router.huggingface.co/hf-inference/models/{settings.huggingface_leffa_model}",
            f"https://router.huggingface.co/models/{settings.huggingface_leffa_model}"
        ]
    else:
        endpoint_urls_to_try = [api_url]
    
    last_error = None
    result = None
    
    for try_url in endpoint_urls_to_try:
        try:
            logger.info(f"尝试端点: {try_url}")
            # 使用更长的超时时间和重试机制
            # Hugging Face 模型可能需要加载，第一次请求可能需要更长时间
            result = _sync_post_json(
                url=try_url,
                payload=payload,
                headers=headers,
                timeout=300,  # 5分钟超时（模型加载和生成可能需要较长时间）
                max_retries=3  # 最多重试3次
            )
            # 如果成功，跳出循环
            logger.info(f"成功使用端点: {try_url}")
            break
        except AIClientError as e:
            # 如果是 404 错误且还有其他端点可尝试，继续尝试下一个
            if "404" in str(e) and try_url != endpoint_urls_to_try[-1]:
                logger.warning(f"端点 {try_url} 返回 404，尝试下一个端点...")
                last_error = e
                continue
            else:
                # 其他错误或已经是最后一个端点，直接抛出
                raise
        except Exception as e:
            # 捕获其他异常，记录并继续尝试下一个端点（如果是 404）
            if "404" in str(e) and try_url != endpoint_urls_to_try[-1]:
                logger.warning(f"端点 {try_url} 返回 404，尝试下一个端点...")
                last_error = AIClientError(f"端点错误: {str(e)}")
                continue
            else:
                raise AIClientError(f"请求失败: {str(e)}")
    
    if result is None:
        if last_error:
            # 提供更详细的错误信息和建议
            error_msg = str(last_error)
            if "404" in error_msg:
                raise AIClientError(
                    f"模型 {settings.huggingface_leffa_model} 不支持 Inference API 或不存在。\n"
                    f"请尝试以下解决方案：\n"
                    f"1. 检查模型名称是否正确：{settings.huggingface_leffa_model}\n"
                    f"2. 访问 https://huggingface.co/{settings.huggingface_leffa_model} 确认模型存在\n"
                    f"3. 如果模型存在但不支持 Inference API，请使用自定义端点 URL：\n"
                    f"   在 .env 文件中设置 HUGGINGFACE_ENDPOINT_URL=您的端点URL\n"
                    f"4. 或者使用 Hugging Face Spaces API（如果模型部署在 Space 上）"
                )
            raise last_error
        raise AIClientError("所有端点都失败，无法生成试穿图片")
    
    try:
        
        # Hugging Face API 返回的格式可能是：
        # 1. 直接返回图片的 base64 编码（字符串）
        # 2. 返回包含图片数据的字典
        # 3. 返回字节数据（需要特殊处理）
        # 4. 返回任务ID（如果是异步任务，需要轮询）
        
        # 处理不同的响应格式
        if isinstance(result, dict):
            # 检查是否有错误信息
            if "error" in result:
                error_msg = result.get("error", "未知错误")
                raise AIClientError(f"Hugging Face API错误: {error_msg}")
            
            # 如果返回的是字典，尝试提取图片数据
            if "image" in result:
                # 如果包含 base64 编码的图片
                image_data = result["image"]
                if isinstance(image_data, str):
                    # base64 字符串，需要解码
                    # 可能包含 data:image/...;base64, 前缀
                    if "base64," in image_data:
                        image_data = image_data.split("base64,")[1]
                    image_bytes = base64.b64decode(image_data)
                    return {"image_data": image_bytes}
            elif "output" in result:
                # 如果包含 output 字段
                output = result["output"]
                if isinstance(output, str):
                    if "base64," in output:
                        output = output.split("base64,")[1]
                    image_bytes = base64.b64decode(output)
                    return {"image_data": image_bytes}
                elif isinstance(output, dict) and "image" in output:
                    image_data = output["image"]
                    if isinstance(image_data, str):
                        if "base64," in image_data:
                            image_data = image_data.split("base64,")[1]
                        image_bytes = base64.b64decode(image_data)
                        return {"image_data": image_bytes}
            elif "image_data" in result:
                # 如果直接包含 image_data（可能是字节）
                image_data = result["image_data"]
                if isinstance(image_data, bytes):
                    return {"image_data": image_data}
                elif isinstance(image_data, str):
                    if "base64," in image_data:
                        image_data = image_data.split("base64,")[1]
                    image_bytes = base64.b64decode(image_data)
                    return {"image_data": image_bytes}
            elif "generated_image" in result:
                # 某些模型可能返回 generated_image
                image_data = result["generated_image"]
                if isinstance(image_data, str):
                    if "base64," in image_data:
                        image_data = image_data.split("base64,")[1]
                    image_bytes = base64.b64decode(image_data)
                    return {"image_data": image_bytes}
        
        # 如果返回的是字符串（base64编码的图片）
        if isinstance(result, str):
            try:
                if "base64," in result:
                    result = result.split("base64,")[1]
                image_bytes = base64.b64decode(result)
                return {"image_data": image_bytes}
            except Exception as e:
                logger.error(f"无法解码base64图片: {str(e)}")
        
        # 如果无法解析，记录详细信息并抛出错误
        logger.error(f"Hugging Face API返回格式无法解析: {type(result)}, 内容: {str(result)[:200]}")
        raise AIClientError(f"Hugging Face API返回格式无法解析: {type(result)}，请检查模型API文档")
        
    except AIClientError as e:
        logger.error(f"Hugging Face Leffa模型调用失败: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Hugging Face Leffa模型调用异常: {str(e)}")
        raise AIClientError(f"调用失败: {str(e)}")


def _generate_tryon_custom_leffa(user_photo_url: str, garment_image_url: str) -> Dict:
    """使用自建云端 Leffa /virtual_tryon 接口生成虚拟试穿图片
    
    接口规范（由用户提供）：
      - 方法：POST
      - 路径：http://<服务器>:8000/virtual_tryon
      - 表单（multipart/form-data）字段：
        - person_image: 人像图片文件（必填）
        - garment_image: 衣服图片文件（必填，PNG 效果最好）
        - vt_model_type: "viton_hd"（默认）或 "dress_code"
        - vt_garment_type: "upper_body" / "lower_body" / "dresses"（默认 "upper_body"）
        - ref_acceleration: true/false（默认 false）
        - step: 推理步数（默认 30）
        - scale: guidance scale（默认 2.5）
        - seed: 随机种子（默认 42）
        - vt_repaint: true/false（默认 false）
        - preprocess_garment: true/false（默认 false）
        - return_image_file: true/false（默认 true，直接返回 PNG 文件）
      - 返回：
        - 默认直接返回合成图像 image/png（二进制）
    """
    if not settings.leffa_virtual_tryon_url:
        raise AIClientError("未配置自建 Leffa 虚拟试穿服务，请在 .env 中设置 LEFFA_VIRTUAL_TRYON_URL")

    api_url = settings.leffa_virtual_tryon_url
    logger.info(f"使用自建 Leffa 虚拟试穿服务: {api_url}")

    # 构建完整的图片URL（如果是相对路径，需要转换为完整URL）
    api_base_url = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

    def _get_full_url(url: str) -> str:
        """将相对路径转换为完整URL"""
        if url.startswith("http"):
            return url
        if url.startswith("/"):
            return f"{api_base_url}{url}"
        return f"{api_base_url}/{url}"

    full_user_photo_url = _get_full_url(user_photo_url)
    full_garment_image_url = _get_full_url(garment_image_url)

    try:
        # 注意：本地图片访问不需要走外部代理，否则可能导致 127.0.0.1:8001 连接被代理拦截（WinError 10061）
        # 因此这里显式禁用代理，直接访问本机服务。

        # 先从本系统下载两张图片，再作为文件上传到云端 Leffa
        # trust_env=False 用来忽略系统环境中的 HTTP(S)_PROXY，避免本地 127.0.0.1:8001 被代理拦截
        with httpx.Client(timeout=30.0, trust_env=False) as client:
            logger.info(f"[Custom Leffa] 下载用户照片: {full_user_photo_url}")
            user_resp = client.get(full_user_photo_url, timeout=30.0)
            user_resp.raise_for_status()
            user_image_data = user_resp.content

            logger.info(f"[Custom Leffa] 下载衣物图片: {full_garment_image_url}")
            garment_resp = client.get(full_garment_image_url, timeout=30.0)
            garment_resp.raise_for_status()
            garment_image_data = garment_resp.content

        logger.info(
            f"[Custom Leffa] 已下载图片，用户={len(user_image_data)}字节, 衣物={len(garment_image_data)}字节"
        )
    except Exception as e:
        logger.error(f"[Custom Leffa] 下载图片失败: {str(e)}")
        raise AIClientError(f"无法下载图片: {str(e)}")

    # 组装 multipart/form-data 请求
    # 这里使用默认参数，你如果有特殊需求，可以后续加 .env 配置来覆盖
    data = {
        "vt_model_type": "viton_hd",
        "vt_garment_type": "upper_body",
        "ref_acceleration": "false",
        "step": "30",
        "scale": "2.5",
        "seed": "42",
        "vt_repaint": "false",
        "preprocess_garment": "false",
        "return_image_file": "true",
    }

    # Content-Type 由 httpx 根据 files 自动设置，这里不用手动指定
    files = {
        "person_image": ("person.png", user_image_data, "image/png"),
        "garment_image": ("garment.png", garment_image_data, "image/png"),
    }

    try:
        logger.info(f"[Custom Leffa] 调用云端 /virtual_tryon，URL: {api_url}")

        # 调用云端虚拟试穿接口，预期直接返回 PNG
        # trust_env=False：忽略系统中的 HTTP(S)_PROXY，避免被本机代理端口拒绝连接（WinError 10061）
        with httpx.Client(timeout=300.0, trust_env=False) as client:
            resp = client.post(api_url, data=data, files=files)

        logger.info(f"[Custom Leffa] 响应状态码: {resp.status_code}")

        # 如果服务按约定返回 image/png，直接取二进制
        content_type = resp.headers.get("content-type", "")
        if resp.status_code == 200 and content_type.startswith("image/"):
            image_bytes = resp.content
            logger.info(
                f"[Custom Leffa] 收到试穿图片，大小={len(image_bytes)}字节, Content-Type={content_type}"
            )
            return {"image_data": image_bytes}

        # 非 200 或非图片，尝试解析错误信息
        try:
            err_json = resp.json()
            logger.error(f"[Custom Leffa] 接口返回错误: {err_json}")
            raise AIClientError(f"自建 Leffa 接口错误: {err_json}")
        except Exception:
            # 不是 JSON，就当作纯文本错误
            logger.error(f"[Custom Leffa] 接口返回非图片且无法解析 JSON，文本: {resp.text[:200]}")
            raise AIClientError(
                f"自建 Leffa 接口返回非图片响应，状态码={resp.status_code}，内容={resp.text[:200]}"
            )

    except AIClientError:
        # 已经记录过详细日志，直接抛出
        raise
    except Exception as e:
        logger.error(f"[Custom Leffa] 调用云端虚拟试穿接口异常: {str(e)}")
        raise AIClientError(f"调用云端虚拟试穿接口失败: {str(e)}")


def _generate_tryon_modelscope(user_photo_url: str, garment_image_url: str) -> Dict:
    """使用魔搭 API 生成虚拟试穿图片"""
    if not settings.modelscope_api_key:
        raise AIClientError("魔搭 API Key未配置，请在环境变量中设置 MODELSCOPE_API_KEY")
    
    # 魔搭 API 端点
    # 魔搭的 API 格式通常是：https://api.modelscope.cn/api/v1/models/{model}/inference
    api_url = f"https://api.modelscope.cn/api/v1/models/{settings.modelscope_model}/inference"
    
    headers = {
        "Authorization": f"Bearer {settings.modelscope_api_key}",
        "Content-Type": "application/json"
    }
    
    # 构建完整的图片URL
    api_base_url = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    
    def _get_full_url(url: str) -> str:
        """将相对路径转换为完整URL"""
        if url.startswith("http"):
            return url
        if url.startswith("/"):
            return f"{api_base_url}{url}"
        return f"{api_base_url}/{url}"
    
    full_user_photo_url = _get_full_url(user_photo_url)
    full_garment_image_url = _get_full_url(garment_image_url)
    
    # 下载图片并转换为 base64
    try:
        # 不使用代理，直接连接下载图片
        with httpx.Client(timeout=30.0) as client:
            logger.info(f"下载用户照片: {full_user_photo_url}")
            user_response = client.get(full_user_photo_url, timeout=30.0)
            user_response.raise_for_status()
            user_image_data = user_response.content
            
            logger.info(f"下载衣物图片: {full_garment_image_url}")
            garment_response = client.get(full_garment_image_url, timeout=30.0)
            garment_response.raise_for_status()
            garment_image_data = garment_response.content
        
        # 转换为 base64
        user_image_base64 = base64.b64encode(user_image_data).decode('utf-8')
        garment_image_base64 = base64.b64encode(garment_image_data).decode('utf-8')
        
        logger.info("已下载图片并转换为base64格式")
        logger.info(f"用户图片大小: {len(user_image_data)} 字节, 衣物图片大小: {len(garment_image_data)} 字节")
        
    except Exception as e:
        logger.error(f"下载图片失败: {str(e)}")
        raise AIClientError(f"无法下载图片: {str(e)}")
    
    logger.info(f"调用魔搭模型 | 用户图片: {full_user_photo_url} | 衣物图片: {full_garment_image_url}")
    logger.info(f"使用模型: {settings.modelscope_model}")
    logger.info(f"API URL: {api_url}")
    
    # 魔搭 API 的 payload 格式
    # 根据魔搭文档，通常使用 inputs 字段
    payload = {
        "inputs": {
            "person_image": user_image_base64,
            "garment_image": garment_image_base64
        }
    }
    
    try:
        result = _sync_post_json(
            url=api_url,
            payload=payload,
            headers=headers,
            timeout=300,  # 5分钟超时
            max_retries=3
        )
        
        # 处理魔搭 API 返回的格式
        if isinstance(result, dict):
            if "error" in result:
                error_msg = result.get("error", "未知错误")
                raise AIClientError(f"魔搭 API错误: {error_msg}")
            
            # 尝试提取图片数据
            if "output" in result:
                output = result["output"]
                if isinstance(output, str):
                    if "base64," in output:
                        output = output.split("base64,")[1]
                    image_bytes = base64.b64decode(output)
                    return {"image_data": image_bytes}
                elif isinstance(output, dict) and "image" in output:
                    image_data = output["image"]
                    if isinstance(image_data, str):
                        if "base64," in image_data:
                            image_data = image_data.split("base64,")[1]
                        image_bytes = base64.b64decode(image_data)
                        return {"image_data": image_bytes}
            
            if "image" in result:
                image_data = result["image"]
                if isinstance(image_data, str):
                    if "base64," in image_data:
                        image_data = image_data.split("base64,")[1]
                    image_bytes = base64.b64decode(image_data)
                    return {"image_data": image_bytes}
        
        # 如果返回的是字符串（base64编码的图片）
        if isinstance(result, str):
            try:
                if "base64," in result:
                    result = result.split("base64,")[1]
                image_bytes = base64.b64decode(result)
                return {"image_data": image_bytes}
            except Exception as e:
                logger.error(f"无法解码base64图片: {str(e)}")
        
        logger.error(f"魔搭 API返回格式无法解析: {type(result)}, 内容: {str(result)[:200]}")
        raise AIClientError(f"魔搭 API返回格式无法解析: {type(result)}，请检查模型API文档")
        
    except AIClientError as e:
        logger.error(f"魔搭模型调用失败: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"魔搭模型调用异常: {str(e)}")
        raise AIClientError(f"调用失败: {str(e)}")

# ------------------------------ 衣物标签识别（百川大模型） ------------------------------
def extract_garment_tags(image_data: bytes) -> List[str]:
    """提取衣物标签（使用百川大模型）"""
    if not settings.baichuan_api_key:
        logger.warning("百川API未配置，返回默认标签")
        return ["未识别标签"]
    
    # 将图片转换为base64编码
    image_base64 = base64.b64encode(image_data).decode()
    
    # 构建提示词，让百川大模型分析图片并返回标签
    prompt = """请分析这张衣物图片，识别并返回衣物的标签。
要求：
1. 返回5-8个最相关的标签
2. 标签应该包括：类别（如上衣、裤子、外套等）、风格（如休闲、正式、运动等）、颜色、季节、材质等
3. 标签之间用中文逗号分隔
4. 只返回标签，不要其他说明文字
5. 如果无法识别，返回"未识别标签"

示例格式：休闲,短袖,白色,夏季,棉质,简约,日常

请直接返回标签："""
    
    # 由于百川大模型可能不支持直接图片输入，我们使用文字描述的方式
    # 通过提示词让模型根据图片特征生成标签
    # 注意：这里我们无法直接发送图片，所以使用通用的提示词
    # 如果需要真正的图片识别，需要百川支持vision模型或使用其他服务
    
    # 尝试使用支持图片的 API 格式（如果百川支持），否则回退到文字描述方式
    try:
        # 先尝试使用图片输入的格式
        payload = {
            "model": settings.baichuan_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            },
                        },
                    ],
                }
            ],
            "temperature": 0.3,
            "max_tokens": 200,
        }

        headers = {
            "Authorization": f"Bearer {settings.baichuan_api_key}",
            "Content-Type": "application/json",
        }

        logger.info("调用百川大模型进行标签识别（尝试图片输入）")
        logger.debug(f"百川API端点: {settings.baichuan_endpoint}, 模型: {settings.baichuan_model}")
        result = _sync_post_json(
            url=settings.baichuan_endpoint,
            payload=payload,
            headers=headers,
            timeout=60,
            use_proxy=True,  # 百川API可能需要代理
        )

        # 解析响应
        content = ""
        if "choices" in result:
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        elif "output" in result:
            content = (
                result.get("output", {})
                .get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )

        if content and "未识别" not in content:
            tags = _parse_tags_from_response(content)
            if tags:
                logger.info(f"识别到标签: {tags}")
                return tags

        # 如果图片输入失败，使用备用方案
        logger.info("图片输入方式失败，使用文字描述方式")
        return _extract_tags_fallback(image_data)

    except (AIClientError, KeyError, TypeError) as e:
        # API 不支持图片输入格式，使用备用方案
        logger.info(f"图片输入格式不支持，使用文字描述方式: {str(e)}")
        return _extract_tags_fallback(image_data)
    except Exception as e:
        logger.error(f"标签识别异常: {str(e)}")
        return _extract_tags_fallback(image_data)

def _parse_tags_from_response(content: str) -> List[str]:
    """从响应文本中解析标签"""
    if not content:
        return []
    
    # 需要过滤掉的无效词汇
    invalid_words = [
        "标签", "识别", "分析", "根据", "图片", "特征", "示例", "可以", "无法", 
        "直接", "查看", "提供", "准确", "由于", "我", "您", "为", "的", "是",
        "包括", "应该", "如", "等", "请", "返回", "不要", "说明", "文字",
        "类别", "风格", "颜色", "季节", "材质", "生成", "相关", "衣物"
    ]
    
    tags = []
    # 尝试从响应中提取标签
    lines = content.strip().split('\n')
    for line in lines:
        line = line.strip()
        # 跳过空行和说明性文字
        if not line or len(line) > 100:
            continue
        
        # 如果包含逗号，按逗号分割
        if '，' in line or ',' in line:
            parts = line.replace('，', ',').split(',')
            for part in parts:
                part = part.strip()
                # 过滤无效标签
                if (part and 
                    len(part) > 0 and 
                    len(part) < 20 and 
                    part not in invalid_words and
                    not any(word in part for word in invalid_words) and
                    not part.startswith(('可以', '无法', '由于', '我', '您'))):
                    tags.append(part)
        else:
            # 单个标签
            if (len(line) < 20 and 
                line not in invalid_words and
                not any(word in line for word in invalid_words) and
                not line.startswith(('可以', '无法', '由于', '我', '您'))):
                tags.append(line)
    
    # 去重并过滤
    tags = list(set([t for t in tags if t and len(t) > 0 and len(t) < 20]))
    
    # 进一步过滤：只保留看起来像标签的词（通常是2-4个汉字）
    valid_tags = []
    for tag in tags:
        # 检查是否是有效的标签格式（2-6个字符，主要是中文）
        if (2 <= len(tag) <= 6 and 
            all('\u4e00' <= char <= '\u9fff' or char.isalnum() for char in tag) and
            tag not in invalid_words):
            valid_tags.append(tag)
    
    # 限制标签数量（最多8个）
    return valid_tags[:8] if valid_tags else []

def _extract_tags_fallback(image_data: bytes) -> List[str]:
    """备用标签识别方案（使用文字描述，基于图片特征）"""
    if not settings.baichuan_api_key:
        return ["未识别标签"]
    
    # 备用方案：由于无法直接输入图片，我们使用通用的提示词
    # 让模型生成一些常见的衣物标签组合
    # 注意：这种方式无法真正识别图片内容，只能生成通用标签
    prompt = """请为一件衣物生成5-8个相关标签。
标签应该包括：
1. 类别：上衣、裤子、外套、短袖、长袖、裙子、鞋子等
2. 风格：休闲、正式、运动、简约、时尚等
3. 颜色：白色、黑色、深色、浅色、亮色等
4. 季节：春季、夏季、秋季、冬季
5. 材质：棉质、牛仔、针织等

请直接返回标签，用中文逗号分隔，不要其他说明文字。
示例：休闲,短袖,白色,夏季,棉质,简约

请返回标签："""
    
    payload = {
        "model": settings.baichuan_model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5,  # 稍微提高温度以获得更多样化的标签
        "max_tokens": 200
    }
    
    headers = {
        "Authorization": f"Bearer {settings.baichuan_api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        logger.info("使用备用方案生成标签（文字描述）")
        logger.debug(f"百川API端点: {settings.baichuan_endpoint}, 模型: {settings.baichuan_model}")
        result = _sync_post_json(
            url=settings.baichuan_endpoint,
            payload=payload,
            headers=headers,
            timeout=30,
            use_proxy=True,  # 百川API可能需要代理
        )
        
        content = ""
        if "choices" in result:
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        elif "output" in result:
            content = result.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", "")
        
        if content:
            # 解析标签
            tags = _parse_tags_from_response(content)
            if tags:
                logger.info(f"备用方案生成标签: {tags}")
                return tags
    except Exception as e:
        logger.error(f"备用标签识别失败: {str(e)}")
    
    # 如果都失败了，返回默认标签
    logger.warning("所有标签识别方案都失败，返回默认标签")
    return ["未识别标签"]

# ------------------------------ 穿搭文案生成（百川） ------------------------------
def summarize_outfit(garments: List[Dict], weather: Dict) -> str:
    """生成穿搭描述文案"""
    if not settings.baichuan_api_key:
        logger.warning("百川API未配置，返回默认文案")
        return "今日穿搭推荐：适合当前天气的舒适搭配"
    
    # 构建提示词
    def _get_field(item, field, default=None):
        # 支持 dict-like、对象属性（SQLAlchemy 或 Pydantic 模型）
        try:
            # 属性访问优先（适用于 Pydantic / ORM 实例）
            if hasattr(item, field):
                return getattr(item, field)
        except Exception:
            pass
        try:
            # 字典访问回退
            return item.get(field, default) if isinstance(item, dict) else default
        except Exception:
            return default

    garment_desc = "\n".join([
        f"- {_get_field(g, 'category', '')}: {_get_field(g, 'name', '')}（{','.join(_get_field(g, 'tags', []) or [])}）"
        for g in garments
    ])
    prompt = f"""
    基于以下信息生成简洁优美的穿搭描述（50字以内）：
    天气：{weather['condition']}，温度{weather['temp_c']}℃
    衣物：{garment_desc}
    要求：口语化、友好，突出搭配亮点和适配天气的原因
    """
    
    payload = {
        "model": settings.baichuan_model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 100
    }
    
    headers = {
        "Authorization": f"Bearer {settings.baichuan_api_key}",
        "Content-Type": "application/json"
    }
    
    logger.info("调用百川大模型生成穿搭文案")
    logger.debug(f"API端点: {settings.baichuan_endpoint}, 模型: {settings.baichuan_model}")
    if not settings.baichuan_api_key:
        logger.warning("百川API密钥未配置，无法调用API")
    try:
        result = _sync_post_json(
            url=settings.baichuan_endpoint,
            payload=payload,
            headers=headers,
            timeout=30,
            use_proxy=True,  # 百川API可能需要代理
        )
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "今日穿搭推荐")
        if content and content.strip():
            return content.strip()
        return "今日穿搭推荐：适合当前天气的舒适搭配"
    except AIClientError as e:
        error_str = str(e)
        # 检查是否是连接错误
        if "10061" in error_str or "Connection refused" in error_str or "actively refused" in error_str:
            logger.warning(
                f"百川模型API连接失败，可能是端点地址不正确或服务不可用: {settings.baichuan_endpoint}\n"
                f"请检查：\n"
                f"1. API端点地址是否正确（当前: {settings.baichuan_endpoint}）\n"
                f"2. 是否需要配置代理（当前已启用代理支持）\n"
                f"3. 网络连接是否正常\n"
                f"4. API密钥是否正确配置"
            )
        else:
            logger.error(f"百川模型调用失败: {error_str}")
        # 生成基于衣物的简单描述作为降级方案
        garment_names = [g.get('name', '') or getattr(g, 'name', '') for g in garments if g]
        if garment_names:
            return f"今日穿搭推荐：{', '.join(garment_names[:3])}的舒适搭配，适合当前天气"
        return "今日穿搭推荐：适合当前天气的舒适搭配"


def generate_recommendation_reason(garments: List[Dict], weather: Dict, style: Optional[str] = None, color: Optional[str] = None) -> str:
    """生成推荐理由（包含天气信息）"""
    if not settings.baichuan_api_key:
        logger.warning("百川API未配置，返回默认推荐理由")
        # 降级方案：基于天气和风格生成理由
        weather_info = f"{weather.get('condition', '晴')}，{weather.get('temp_c', 20)}℃"
        if style and color:
            return f"{style}风格，{color}系搭配，适合{weather_info}的天气"
        return f"适合{weather_info}的天气，推荐舒适搭配"
    
    # 构建提示词
    def _get_field(item, field, default=None):
        try:
            if hasattr(item, field):
                return getattr(item, field)
        except Exception:
            pass
        try:
            return item.get(field, default) if isinstance(item, dict) else default
        except Exception:
            return default

    garment_desc = "\n".join([
        f"- {_get_field(g, 'name', '')}（{_get_field(g, 'category', '')}，{','.join(_get_field(g, 'tags', []) or [])}）"
        for g in garments
    ])
    
    weather_info = f"{weather.get('condition', '晴')}，温度{weather.get('temp_c', 20)}℃"
    style_text = f"{style}风格" if style else "未指定"
    color_text = f"{color}系" if color else "未指定"
    
    prompt = f"""
    基于以下信息生成简洁的推荐理由（30字以内，包含天气信息）：
    天气：{weather_info}
    衣物：{garment_desc}
    风格：{style_text}，{color_text}
    要求：说明为什么这套搭配适合当前天气，格式如"XX风格，XX系搭配，适合XX天气（XX℃）"
    示例："休闲风格，冷色系搭配，适合晴天25℃的天气"
    """
    
    payload = {
        "model": settings.baichuan_model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 80
    }
    
    headers = {
        "Authorization": f"Bearer {settings.baichuan_api_key}",
        "Content-Type": "application/json"
    }
    
    logger.info("调用百川大模型生成推荐理由")
    logger.debug(f"API端点: {settings.baichuan_endpoint}, 模型: {settings.baichuan_model}")
    if not settings.baichuan_api_key:
        logger.warning("百川API密钥未配置，无法调用API")
    try:
        result = _sync_post_json(
            url=settings.baichuan_endpoint,
            payload=payload,
            headers=headers,
            timeout=30,
            use_proxy=True,  # 百川API可能需要代理
        )
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        if content and content.strip():
            reason = content.strip()
            # 确保包含天气信息
            if weather_info not in reason and str(weather.get('temp_c', '')) not in reason:
                reason = f"{reason}，适合{weather_info}的天气"
            return reason
        # 如果返回为空，使用降级方案
        raise AIClientError("百川模型返回空内容")
    except AIClientError as e:
        error_str = str(e)
        # 检查是否是连接错误
        if "10061" in error_str or "Connection refused" in error_str or "actively refused" in error_str:
            logger.warning(
                f"百川模型API连接失败，使用降级方案生成推荐理由: {settings.baichuan_endpoint}\n"
                f"请检查：\n"
                f"1. API端点地址是否正确（当前: {settings.baichuan_endpoint}）\n"
                f"2. 是否需要配置代理（当前已启用代理支持）\n"
                f"3. 网络连接是否正常\n"
                f"4. API密钥是否正确配置"
            )
        else:
            logger.error(f"百川模型调用失败: {error_str}")
        
        # 降级方案：基于天气、风格和颜色生成理由
        weather_info = f"{weather.get('condition', '晴')}，{weather.get('temp_c', 20)}℃"
        if style and color:
            return f"{style}风格，{color}系搭配，适合{weather_info}的天气"
        elif style:
            return f"{style}风格，适合{weather_info}的天气"
        elif color:
            return f"{color}系搭配，适合{weather_info}的天气"
        else:
            return f"适合{weather_info}的天气，推荐舒适搭配"