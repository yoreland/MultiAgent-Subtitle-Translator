#!/bin/bash

echo "🚀 启动SRT翻译系统 - React版本"

# 检查Node.js
if ! command -v node &> /dev/null; then
    echo "❌ 请先安装Node.js"
    exit 1
fi

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 请先安装Python3"
    exit 1
fi

echo "📦 安装后端依赖..."
cd backend
pip install -r requirements.txt

echo "🔧 启动后端API服务器..."
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "📦 安装前端依赖..."
cd ../frontend
npm install

echo "🎨 启动前端开发服务器..."
PORT=3001 npm start &
FRONTEND_PID=$!

echo "✅ 系统启动完成!"
echo "📍 前端地址: http://localhost:3001"
echo "📍 后端API: http://localhost:8000"
echo ""
echo "按 Ctrl+C 停止服务"

# 等待用户中断
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
