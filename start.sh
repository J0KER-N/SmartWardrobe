#!/bin/bash

echo "========================================"
echo "智能衣橱系统启动脚本"
echo "========================================"
echo ""

echo "[1/2] 启动后端服务..."
cd backend
uvicorn app.main:app --reload &
BACKEND_PID=$!
sleep 3

echo "[2/2] 启动前端服务..."
cd ../front
python3 -m http.server 8080 &
FRONTEND_PID=$!

echo ""
echo "========================================"
echo "启动完成！"
echo "========================================"
echo "后端服务: http://127.0.0.1:8000"
echo "前端服务: http://localhost:8080"
echo "API 文档: http://127.0.0.1:8000/docs"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

# 等待用户中断
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait

