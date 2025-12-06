# 前端说明

## 启动方式

由于使用了 ES6 模块，需要通过 HTTP 服务器访问，不能直接打开 HTML 文件。

### 方法一：Python 简单服务器（推荐）

```bash
# Python 3
python -m http.server 8080

# Python 2
python -m SimpleHTTPServer 8080
```

然后访问：http://localhost:8080

### 方法二：Node.js http-server

```bash
# 安装
npm install -g http-server

# 启动
http-server -p 8080
```

### 方法三：VS Code Live Server

安装 VS Code 的 "Live Server" 插件，右键 `index.html` 选择 "Open with Live Server"

## API 配置

API 基础地址在 `api.js` 中配置：

```javascript
const API_BASE_URL = 'http://127.0.0.1:8000';
```

如果后端运行在其他地址或端口，请修改此配置。

## 功能说明

- 所有 API 调用统一在 `api.js` 中管理
- Token 自动存储在 localStorage
- 支持 Token 自动刷新
- 错误统一处理

## 开发建议

1. 使用浏览器开发者工具查看网络请求
2. 检查控制台错误信息
3. 确保后端服务已启动
4. 检查 CORS 配置

