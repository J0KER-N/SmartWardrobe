# Hugging Face API 网络问题排查指南

## 问题：连接超时 (ConnectTimeout)

如果遇到 `httpx.ConnectTimeout` 或 `请求超时` 错误，可能是网络连接问题。

## 解决方案

### 1. 检查网络连接

```bash
# 测试是否能访问 Hugging Face
ping router.huggingface.co

# 或使用 curl 测试
curl -I https://router.huggingface.co
```

### 2. 配置代理（如果需要）

如果您的网络环境需要代理才能访问外网，请在 `.env` 文件中添加：

```env
# HTTP 代理（如果需要）
HTTP_PROXY=http://proxy.example.com:8080
HTTPS_PROXY=http://proxy.example.com:8080

# 或者
http_proxy=http://proxy.example.com:8080
https_proxy=http://proxy.example.com:8080
```

### 3. 检查防火墙设置

确保防火墙允许访问：
- `router.huggingface.co`
- 端口 443 (HTTPS)

### 4. 使用诊断脚本

运行诊断脚本检查连接：

```bash
cd backend
python scripts/diagnose_huggingface.py
```

### 5. 增加超时时间

如果网络较慢，可以在代码中增加超时时间（已在代码中设置为 300 秒）。

### 6. 检查 DNS 解析

如果 DNS 解析有问题，可以尝试：
- 更换 DNS 服务器（如 8.8.8.8）
- 使用 VPN
- 检查 hosts 文件

## 常见错误

1. **ConnectTimeout**: 无法连接到服务器
   - 检查网络连接
   - 检查代理设置
   - 检查防火墙

2. **ReadTimeout**: 连接成功但响应超时
   - 增加超时时间
   - 检查网络速度

3. **503 错误**: 模型正在加载
   - 这是正常的，等待模型加载完成即可
   - 代码已自动处理重试

## 联系支持

如果以上方法都无法解决问题，请：
1. 查看完整的错误日志
2. 运行诊断脚本并保存输出
3. 联系 Hugging Face 支持团队

