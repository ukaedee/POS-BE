#!/bin/bash

# Azure App Service startup script for POS API

echo "🚀 Starting POS API application..."
echo "⏰ Current time: $(date)"

# 環境変数の確認
echo "📋 Environment check:"
echo "  PORT: ${PORT:-8000}"
echo "  DATABASE_URL: ${DATABASE_URL:0:50}..."
echo "  SSL_CA_PATH: ${SSL_CA_PATH:-'Not set'}"
echo "  PYTHONPATH: ${PYTHONPATH:-'Not set'}"
echo "  WEBSITE_HOSTNAME: ${WEBSITE_HOSTNAME:-'Not set'}"

# Python環境の確認
echo "🐍 Python environment:"
python --version
pip --version
echo "  Current working directory: $(pwd)"

# ファイル構造の確認
echo "📁 File structure:"
ls -la
echo "📁 App directory:"
ls -la app/

# 依存関係がインストールされているか確認
echo "📦 Checking dependencies..."
if ! python -c "import uvicorn, fastapi, sqlalchemy, pymysql" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
    echo "📦 Installation completed"
else
    echo "✅ Dependencies already installed"
fi

# インストールされたパッケージの確認
echo "📦 Installed packages:"
pip list | grep -E "(fastapi|uvicorn|sqlalchemy|pymysql|pydantic)"

# Pythonモジュールのテスト
echo "🧪 Testing Python imports..."
python -c "
try:
    import app.main
    print('✅ app.main imported successfully')
    import app.models
    print('✅ app.models imported successfully')
    import app.schemas
    print('✅ app.schemas imported successfully')
    import app.database
    print('✅ app.database imported successfully')
except Exception as e:
    print(f'❌ Import failed: {e}')
"

# Azure App Serviceのポート設定
PORT=${PORT:-8000}

# Python ログレベルを設定
export PYTHONUNBUFFERED=1
export PYTHON_LOG_LEVEL=INFO

# アプリケーションを起動
echo "🌐 Starting FastAPI server on port $PORT..."
echo "📋 Log level: INFO"
echo "⏰ Startup time: $(date)"

# uvicornの起動確認
echo "🔧 Testing uvicorn command..."
uvicorn --version

exec uvicorn app.main:app --host 0.0.0.0 --port $PORT --log-level info 