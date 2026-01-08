# API Key 配置指南

## 必需配置的 API Key

本系统需要配置以下 API Key 才能使用完整功能：

### 1. Hugging Face API Key（必需 - 用于虚拟试穿功能）

**获取步骤：**
1. 访问 [Hugging Face 设置页面](https://huggingface.co/settings/tokens)
2. 点击 **"New token"** 按钮
3. 输入 Token 名称（如：smart-wardrobe）
4. 选择权限：
   - **"Read"** 权限（推荐）
   - 或细粒度权限中的 **"对无服务器推理 API 进行调用"**
5. 点击 **"Generate token"**
6. **复制生成的 Token**（只显示一次，请妥善保存）

**配置方法：**
在 `backend/.env` 文件中添加：
```env
HUGGINGFACE_API_KEY=your-copied-token-here
```

**验证：**
- 如果未配置，虚拟试穿功能会报错：`Hugging Face API Key未配置，请在环境变量中设置 HUGGINGFACE_API_KEY`
- 如果配置错误，API 调用会返回 401 或 403 错误

---

### 2. 百川大模型 API Key（必需 - 用于标签识别和推荐穿搭）

**获取步骤：**
1. 访问百川大模型官网
2. 注册并登录账号
3. 在控制台获取 API Key

**配置方法：**
在 `backend/.env` 文件中添加：
```env
BAICHUAN_API_KEY=your-baichuan-api-key-here
```

**验证：**
- 如果未配置，标签识别会返回默认标签，推荐穿搭会返回默认文案
- 如果配置错误，API 调用会失败

---

## 完整配置示例

在 `backend/.env` 文件中添加：

```env
# Hugging Face API（虚拟试穿）
HUGGINGFACE_API_KEY=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
HUGGINGFACE_LEFFA_MODEL=levihsu/OOTDiffusion

# 百川大模型（标签识别和推荐穿搭）
BAICHUAN_API_KEY=your-baichuan-api-key
BAICHUAN_ENDPOINT=https://api.baichuan-ai.com/v1/chat/completions
BAICHUAN_MODEL=Baichuan4-Air
```

## 检查配置

运行以下命令检查配置是否正确：
```bash
cd backend
python scripts/check_baichuan.py
```

## 注意事项

1. **安全性**：
   - 不要将 `.env` 文件提交到 Git
   - 生产环境使用环境变量而非文件配置
   - 定期轮换 API Key

2. **API 限制**：
   - Hugging Face 免费账户有调用频率限制
   - 百川大模型可能有使用量限制
   - 注意监控 API 使用情况

3. **错误处理**：
   - 如果 API Key 未配置，相关功能会报错或返回默认值
   - 查看日志文件了解详细错误信息




