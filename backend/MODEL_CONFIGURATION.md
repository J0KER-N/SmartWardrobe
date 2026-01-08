# 虚拟试衣模型配置指南

## 支持的模型

系统支持两种虚拟试衣模型服务：

### 1. Hugging Face Inference API（默认）

**推荐模型：`facebook/leffa`**
- ✅ 支持 Inference API
- ✅ 稳定可靠
- ✅ 全球可用

**配置方式：**
```env
HUGGINGFACE_API_KEY=your-huggingface-api-key-here
HUGGINGFACE_LEFFA_MODEL=facebook/leffa
```

**其他可用模型：**
- `levihsu/OOTDiffusion` - 可能不支持 Inference API，需要自定义端点

### 2. 魔搭 ModelScope API（国内推荐）

**推荐模型：`damo/cv_unet_virtual-try-on-idm-vton`**
- ✅ 国内访问速度快
- ✅ 支持 Inference API
- ✅ 适合国内用户

**配置方式：**
```env
MODELSCOPE_API_KEY=your-modelscope-api-key-here
MODELSCOPE_MODEL=damo/cv_unet_virtual-try-on-idm-vton
```

**注意：** 如果同时配置了魔搭和 Hugging Face，系统会优先使用魔搭模型。

## 模型选择优先级

1. **魔搭模型**（如果配置了 `MODELSCOPE_API_KEY` 和 `MODELSCOPE_MODEL`）
2. **Hugging Face 模型**（如果配置了 `HUGGINGFACE_API_KEY`）

## 获取 API Key

### Hugging Face API Key
1. 访问 https://huggingface.co/settings/tokens
2. 点击 "New token" 创建新的 Access Token
3. 选择 "Read" 权限（或细粒度权限中的 "对无服务器推理 API 进行调用"）
4. 复制 Token 并粘贴到 `.env` 文件

### 魔搭 API Key
1. 访问 https://modelscope.cn
2. 注册并登录账户
3. 在个人设置中创建 API Key
4. 复制 API Key 并粘贴到 `.env` 文件

## 故障排除

### 问题：模型返回 404 错误

**原因：**
- 模型不支持 Inference API
- 模型名称错误
- API Key 无效

**解决方案：**
1. 确认模型名称正确（例如：`facebook/leffa`）
2. 访问模型页面确认模型存在
3. 检查 API Key 是否正确配置
4. 尝试使用其他模型（如魔搭模型）

### 问题：请求超时

**原因：**
- 模型加载需要时间
- 网络连接问题

**解决方案：**
1. 等待模型首次加载完成（可能需要几分钟）
2. 检查网络连接
3. 如果使用代理，确认代理配置正确

## 推荐配置

### 国内用户（推荐）
```env
# 使用魔搭模型
MODELSCOPE_API_KEY=your-modelscope-api-key-here
MODELSCOPE_MODEL=damo/cv_unet_virtual-try-on-idm-vton
```

### 国际用户（推荐）
```env
# 使用 Hugging Face 模型
HUGGINGFACE_API_KEY=your-huggingface-api-key-here
HUGGINGFACE_LEFFA_MODEL=facebook/leffa
```

### 备用配置
```env
# 同时配置两个模型，系统会优先使用魔搭
MODELSCOPE_API_KEY=your-modelscope-api-key-here
MODELSCOPE_MODEL=damo/cv_unet_virtual-try-on-idm-vton

HUGGINGFACE_API_KEY=your-huggingface-api-key-here
HUGGINGFACE_LEFFA_MODEL=facebook/leffa
```


