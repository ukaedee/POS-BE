#!/bin/bash

# Azure App Service startup script for POS API

echo "🚀 Starting POS API application..."

# 環境変数の確認
echo "📋 Environment check:"
echo "  PORT: ${PORT:-8000}"
echo "  DATABASE_URL: ${DATABASE_URL:0:20}..."

# 依存関係がインストールされているか確認
if ! python -c "import uvicorn" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

# Azure App Serviceのポート設定
PORT=${PORT:-8000}

# アプリケーションを起動
echo "🌐 Starting FastAPI server on port $PORT..."
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT 