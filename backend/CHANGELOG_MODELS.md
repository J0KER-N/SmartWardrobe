# 模型配置更新日志

## 2024-01-XX - 添加替代模型支持

### 更新内容

1. **默认模型更改为 `facebook/leffa`**
   - ✅ 支持 Hugging Face Inference API
   - ✅ 避免 404 错误
   - ✅ 稳定可靠

2. **添加魔搭模型支持**
   - ✅ 支持 `damo/cv_unet_virtual-try-on-idm-vton` 模型
   - ✅ 国内访问速度快
   - ✅ 适合国内用户

### 配置方式

#### 使用 Hugging Face（默认）
```env
HUGGINGFACE_API_KEY=your-huggingface-api-key-here
HUGGINGFACE_LEFFA_MODEL=facebook/leffa
```

#### 使用魔搭（国内推荐）
```env
MODELSCOPE_API_KEY=your-modelscope-api-key-here
MODELSCOPE_MODEL=damo/cv_unet_virtual-try-on-idm-vton
```

### 模型选择优先级

1. 如果配置了魔搭模型（`MODELSCOPE_API_KEY` 和 `MODELSCOPE_MODEL`），优先使用魔搭
2. 否则使用 Hugging Face 模型

### 修改的文件

- `backend/app/config.py` - 添加魔搭模型配置，默认模型改为 `facebook/leffa`
- `backend/app/services/ai_clients.py` - 添加魔搭模型支持函数 `_generate_tryon_modelscope`
- `backend/README.md` - 更新配置说明
- `backend/MODEL_CONFIGURATION.md` - 新增模型配置指南

### 使用建议

- **国内用户**：推荐使用魔搭模型，访问速度快
- **国际用户**：推荐使用 Hugging Face 的 `facebook/leffa` 模型
- **备用方案**：可以同时配置两个模型，系统会自动选择


