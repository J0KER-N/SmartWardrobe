# 登录问题调试指南

## 🔍 调试步骤

### 1. 检查浏览器控制台
打开浏览器开发者工具（F12），查看：
- **Console 标签**：查看是否有错误信息
- **Network 标签**：查看登录请求是否发送，以及响应状态

### 2. 检查后端是否运行
```bash
# 检查后端是否在运行
curl http://127.0.0.1:8000/health
```

应该返回：
```json
{"status":"ok","environment":"development"}
```

### 3. 检查 CORS 配置
确保后端的 `.env` 文件中包含：
```env
FRONTEND_ORIGIN=http://localhost:8080,http://127.0.0.1:8080
```

### 4. 检查 API 地址
在浏览器控制台输入：
```javascript
console.log(window.API_BASE_URL);
console.log(window.api);
```

应该显示：
- `API_BASE_URL`: `http://127.0.0.1:8000`
- `api`: 一个对象（包含 authAPI, wardrobeAPI 等）

### 5. 手动测试登录 API
在浏览器控制台输入：
```javascript
fetch('http://127.0.0.1:8000/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    phone: '你的手机号',
    password: '你的密码'
  })
})
.then(r => r.json())
.then(console.log)
.catch(console.error);
```

## 🐛 常见问题

### 问题1: "API未加载，请刷新页面重试"
**原因**: `api.js` 文件未正确加载
**解决**: 
1. 检查 `index.html` 中是否包含 `<script src="api.js"></script>`
2. 检查浏览器 Network 标签，确认 `api.js` 文件已加载（状态码 200）
3. 检查 `api.js` 文件路径是否正确

### 问题2: CORS 错误
**错误信息**: `Access to fetch at '...' from origin '...' has been blocked by CORS policy`
**解决**:
1. 检查后端 `.env` 文件中的 `FRONTEND_ORIGIN`
2. 确保包含前端实际访问的地址
3. 重启后端服务

### 问题3: 网络错误
**错误信息**: `Failed to fetch` 或 `NetworkError`
**解决**:
1. 检查后端是否正在运行
2. 检查 `API_BASE_URL` 是否正确
3. 检查防火墙设置

### 问题4: 401 未授权
**错误信息**: `手机号或密码错误`
**解决**:
1. 确认手机号和密码正确
2. 检查数据库中用户是否存在
3. 检查密码是否正确加密

### 问题5: 请求无响应
**现象**: 点击登录后没有任何反应
**可能原因**:
1. JavaScript 错误导致代码中断
2. 网络请求被阻塞
3. 后端响应时间过长

**调试方法**:
1. 打开浏览器控制台，查看是否有红色错误
2. 查看 Network 标签，看请求是否发送
3. 检查请求状态（pending、failed、200等）

## 🔧 快速修复

### 如果完全无响应，尝试以下步骤：

1. **清除浏览器缓存**
   - 按 Ctrl+Shift+Delete
   - 清除缓存和 Cookie

2. **检查文件路径**
   - 确保 `api.js` 和 `index.html` 在同一目录
   - 确保使用 HTTP 服务器访问（不是直接打开文件）

3. **检查后端日志**
   ```bash
   # 查看后端日志
   tail -f backend/smartwardrobe.log
   ```

4. **测试后端 API 直接**
   ```bash
   curl -X POST http://127.0.0.1:8000/auth/login \
     -H "Content-Type: application/json" \
     -d '{"phone":"你的手机号","password":"你的密码"}'
   ```

## 📝 调试信息收集

如果问题仍然存在，请提供以下信息：

1. **浏览器控制台输出**（Console 标签的所有内容）
2. **网络请求详情**（Network 标签中登录请求的详情）
3. **后端日志**（如果有）
4. **测试用户信息**（手机号和密码，用于测试）

## 🚀 测试命令

### 测试后端健康检查
```bash
curl http://127.0.0.1:8000/health
```

### 测试登录 API
```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"phone":"13800138000","password":"Test1234"}'
```

### 测试 CORS
```bash
curl -X OPTIONS http://127.0.0.1:8000/auth/login \
  -H "Origin: http://localhost:8080" \
  -H "Access-Control-Request-Method: POST" \
  -v
```




