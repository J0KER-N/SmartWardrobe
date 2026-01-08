# 虚拟试衣功能故障排除指南

## 问题：模型返回 404 错误

如果遇到 `模型或端点不存在 (404)` 错误，可能的原因和解决方案如下：

### 原因分析

1. **模型不支持 Inference API**
   - 并非所有 Hugging Face 模型都支持 Inference API
   - 某些模型可能需要通过 Spaces API 或其他方式访问

2. **模型名称错误**
   - 确认模型名称拼写正确
   - 检查模型是否存在于 Hugging Face

3. **API 端点格式变更**
   - Hugging Face 可能更新了 API 端点格式
   - 某些模型可能需要使用不同的端点

### 解决方案

#### 方案 1：使用自定义端点 URL

如果模型部署在 Hugging Face Spaces 或其他服务上，可以使用自定义端点：

1. 在 `backend/.env` 文件中添加：
```env
HUGGINGFACE_ENDPOINT_URL=https://your-custom-endpoint-url.com/api
```

2. 重启后端服务

#### 方案 2：使用 Hugging Face Spaces API

如果模型部署在 Hugging Face Space 上：

1. 找到 Space 的 API 端点（通常在 Space 页面的 "API" 标签中）
2. 在 `backend/.env` 文件中设置：
```env
HUGGINGFACE_ENDPOINT_URL=https://your-space-name.hf.space/api
```

#### 方案 3：更换模型

如果当前模型不支持，可以尝试其他虚拟试衣模型：

1. 访问 https://huggingface.co/models 搜索 "virtual try-on" 或 "OOTDiffusion"
2. 找到支持 Inference API 的模型
3. 在 `backend/.env` 文件中更新：
```env
HUGGINGFACE_LEFFA_MODEL=新的模型名称
```

#### 方案 4：使用本地部署的模型

如果模型支持本地部署：

1. 在本地部署模型服务
2. 在 `backend/.env` 文件中设置：
```env
HUGGINGFACE_ENDPOINT_URL=http://localhost:7860/api
```

### 检查模型状态

1. 访问模型页面：https://huggingface.co/levihsu/OOTDiffusion
2. 查看模型是否支持 Inference API
3. 检查模型的 "Deploy" 标签，查看可用的部署选项

### 常见模型推荐

以下是一些可能支持虚拟试衣的模型（需要验证）：

- `levihsu/OOTDiffusion` - OOTDiffusion 模型（当前使用）
- 其他 OOTDiffusion 变体
- 其他虚拟试衣模型

### 获取帮助

如果以上方案都无法解决问题：

1. 查看后端日志：`backend/smartwardrobe.log`
2. 检查 Hugging Face API Key 是否正确配置
3. 确认网络连接正常（如果使用代理，检查代理配置）
4. 联系 Hugging Face 支持团队



