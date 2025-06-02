import os
import sys
import logging
import uvicorn

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.StreamHandler(sys.stderr)
    ]
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("🚀 Starting POS API application...")
    
    # 環境情報のログ出力
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"PORT: {os.environ.get('PORT', '8000')}")
    
    # モジュールのインポートテスト
    try:
        logger.info("🧪 Testing module imports...")
        import app.main
        logger.info("✅ app.main imported successfully")
        
        # Azure App Serviceでは環境変数PORTが設定される
        port = int(os.environ.get("PORT", 8000))
        logger.info(f"🌐 Starting server on port {port}")
        
        uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        sys.exit(1) 