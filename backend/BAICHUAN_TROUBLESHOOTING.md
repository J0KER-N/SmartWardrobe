# 百川大模型连接问题排查指南

## 问题现象

连接百川大模型时出现以下错误：
- `[WinError 10061] 由于目标计算机积极拒绝，无法连接`
- `百川模型API连接失败，可能是端点地址不正确或服务不可用`

## 可能的原因

### 1. API密钥未配置

**检查方法：**
```bash
cd backend
python scripts/check_baichuan.py
```

如果显示"百川API密钥: 未配置"，需要在 `.env` 文件中配置。

**解决方法：**
1. 访问百川大模型官网（https://www.baichuan-ai.com/）注册并获取 API Key
2. 在 `backend/.env` 文件中添加：
```env
BAICHUAN_API_KEY=your-api-key-here
BAICHUAN_ENDPOINT=https://api.baichuan-ai.com/v1/chat/completions
BAICHUAN_MODEL=Baichuan4-Air
```

### 2. API端点地址不正确

百川大模型的API端点可能因地区或服务版本而异。请检查：

**可能的端点地址：**
- `https://api.baichuan-ai.com/v1/chat/completions`（默认）
- `https://open.baichuan-ai.com/v1/chat/completions`
- 其他官方提供的端点地址

**解决方法：**
1. 查看百川大模型官方文档确认正确的端点地址
2. 在 `.env` 文件中更新 `BAICHUAN_ENDPOINT`

### 3. 网络连接问题

**检查方法：**
```bash
# 测试网络连接
curl -v https://api.baichuan-ai.com/v1/chat/completions
```

**解决方法：**
1. 检查网络连接是否正常
2. 如果在中国大陆，可能需要配置代理
3. 检查防火墙设置

### 4. 需要代理访问

如果百川API服务器在海外，可能需要通过代理访问。

**解决方法：**
1. 配置系统代理环境变量：
```bash
# Windows PowerShell
$env:HTTP_PROXY="http://127.0.0.1:7890"
$env:HTTPS_PROXY="http://127.0.0.1:7890"

# Linux/Mac
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890
```

2. 代码已支持自动使用系统代理（`trust_env=True`）

### 5. 模型名称不正确

**检查方法：**
查看 `.env` 文件中的 `BAICHUAN_MODEL` 配置。

**常见的模型名称：**
- `Baichuan4-Air`
- `baichuan2-7b-chat`
- `Baichuan2-13B-Chat`
- 其他官方支持的模型

**解决方法：**
在 `.env` 文件中设置正确的模型名称：
```env
BAICHUAN_MODEL=Baichuan4-Air
```

## 诊断步骤

### 步骤1：检查配置

运行诊断脚本：
```bash
cd backend
python scripts/check_baichuan.py
```

查看输出中的：
- 百川API密钥是否已配置
- API端点地址
- 模型名称

### 步骤2：测试网络连接

```bash
# 测试端点是否可达
ping api.baichuan-ai.com

# 或使用 curl 测试
curl -I https://api.baichuan-ai.com
```

### 步骤3：测试API调用

使用测试脚本进行详细测试：
```bash
cd backend
python scripts/test_baichuan.py
```

### 步骤4：查看日志

查看后端日志文件 `backend/smartwardrobe.log`，查找详细的错误信息。

## 常见错误及解决方案

### 错误1：`[WinError 10061] 由于目标计算机积极拒绝，无法连接`

**原因：**
- 端点地址不正确
- 服务不可用
- 需要代理但未配置

**解决：**
1. 确认端点地址正确
2. 配置代理（如需要）
3. 检查服务状态

### 错误2：`401 Unauthorized`

**原因：**
- API密钥错误或过期

**解决：**
1. 检查 `.env` 文件中的 `BAICHUAN_API_KEY` 是否正确
2. 重新生成 API Key

### 错误3：`404 Not Found`

**原因：**
- 端点地址不正确
- 模型名称不存在

**解决：**
1. 检查端点地址
2. 检查模型名称是否正确

## 临时解决方案

如果百川API暂时无法使用，系统会自动使用降级方案：
- **标签识别**：返回默认标签 `["未识别标签"]`
- **推荐理由**：返回基于天气和风格的简单理由
- **穿搭描述**：返回默认描述文案

这些降级方案不会影响系统的基本功能，但AI功能会受限。

## 联系支持

如果以上方法都无法解决问题，建议：
1. 查看百川大模型官方文档：https://docs.baichuan-ai.com
2. 联系百川技术支持
3. 检查百川服务状态公告


