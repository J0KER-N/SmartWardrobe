@echo off
echo ========================================
echo 智能衣橱系统启动脚本
echo ========================================
echo.

echo [1/2] 启动后端服务...
cd backend
start "后端服务" cmd /k "uvicorn app.main:app --reload"
timeout /t 3 /nobreak >nul

echo [2/2] 启动前端服务...
cd ..\front
start "前端服务" cmd /k "python -m http.server 8080"
timeout /t 2 /nobreak >nul

echo.
echo ========================================
echo 启动完成！
echo ========================================
echo 后端服务: http://127.0.0.1:8000
echo 前端服务: http://localhost:8080
echo API 文档: http://127.0.0.1:8000/docs
echo.
echo 按任意键退出...
pause >nul

