import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import pymysql
from urllib.parse import urlparse, parse_qs

# PyMySQLをMySQLドライバとして使用
pymysql.install_as_MySQLdb()

# ログ設定
logger = logging.getLogger(__name__)

load_dotenv()

# 個別の環境変数から取得
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# DATABASE_URLを構築
if all([DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD]):
    DATABASE_URL = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        "?ssl_mode=REQUIRED"
    )
    logger.info("✅ DATABASE_URL constructed from individual environment variables")
else:
    # フォールバック: 元のDATABASE_URL環境変数を使用
    DATABASE_URL = os.getenv("DATABASE_URL")
    logger.info("⚠️ Using fallback DATABASE_URL environment variable")

SSL_CA_PATH = os.getenv("SSL_CA_PATH")

logger.info("🔧 Database configuration:")
logger.info(f"  DB_HOST: {DB_HOST if DB_HOST else 'Not set'}")
logger.info(f"  DB_PORT: {DB_PORT if DB_PORT else 'Not set'}")
logger.info(f"  DB_NAME: {DB_NAME if DB_NAME else 'Not set'}")
logger.info(f"  DB_USER: {DB_USER if DB_USER else 'Not set'}")
logger.info(f"  DB_PASSWORD: {'***' if DB_PASSWORD else 'Not set'}")
logger.info(f"  DATABASE_URL: {DATABASE_URL[:60] if DATABASE_URL else 'Not set'}...")
logger.info(f"  SSL_CA_PATH: {SSL_CA_PATH if SSL_CA_PATH else 'Not set'}")

# Azure App Service用の設定
engine = None

try:
    if not DATABASE_URL:
        logger.error(f"❌ DATABASE_URL: {DATABASE_URL.split('@')[0]}@[REDACTED]")
        raise ValueError("Database configuration is incomplete")
    
    logger.info("🔗 Creating database engine with ssl_mode=REQUIRED configuration")
    
    # DATABASE_URLからクエリパラメータを確認
    parsed_url = urlparse(DATABASE_URL)
    clean_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
    
    # クエリパラメータをチェック
    ssl_enabled = False
    ssl_mode = None
    if parsed_url.query:
        logger.info(f"🔍 URL query parameters: {parsed_url.query}")
        query_params = parse_qs(parsed_url.query)
        
        # ssl_mode パラメータをチェック
        if 'ssl_mode' in query_params:
            ssl_mode = query_params['ssl_mode'][0]
            logger.info(f"🔒 SSL mode from URL: {ssl_mode}")
            ssl_enabled = ssl_mode.upper() in ['REQUIRED', 'PREFERRED']
        elif 'ssl' in query_params:
            ssl_enabled = query_params.get('ssl', ['false'])[0].lower() == 'true'
            logger.info(f"🔒 SSL enabled from URL: {ssl_enabled}")
    
    logger.info(f"🔗 Clean DATABASE_URL: {clean_url[:60]}...")
    
    # ENGINE設定を構築
    engine_args = {
        "echo": False,
        "pool_pre_ping": True,
        "pool_recycle": 3600
    }
    
    # SSLが必要な場合の設定
    if ssl_enabled:
        logger.info(f"🔒 Configuring SSL connection (mode: {ssl_mode or 'enabled'})")
        # PyMySQLのSSL設定を適切に構成
        ssl_config = {
            "ssl_disabled": False,
            "ssl_verify_cert": False,
            "ssl_verify_identity": False
        }
        
        # ssl_mode=REQUIREDの場合の追加設定
        if ssl_mode and ssl_mode.upper() == 'REQUIRED':
            ssl_config["ssl_check_hostname"] = False
        
        # SSL証明書ファイルがある場合
        if SSL_CA_PATH and os.path.exists(SSL_CA_PATH):
            logger.info(f"🔒 Using SSL certificate file: {SSL_CA_PATH}")
            ssl_config["ssl_ca"] = SSL_CA_PATH
            ssl_config["ssl_verify_cert"] = True
        
        engine_args["connect_args"] = ssl_config
    else:
        logger.info("🔗 Using connection without explicit SSL configuration")
    
    # エンジンを作成（clean_urlまたは元のURLを使用）
    url_to_use = DATABASE_URL if not ssl_enabled else clean_url
    engine = create_engine(url_to_use, **engine_args)
    
    logger.info("✅ Database engine created successfully")
    
    # 接続テスト（オプション - 起動時のエラーを避けるため）
    try:
        logger.info("🧪 Testing database connection...")
        with engine.connect() as conn:
            result = conn.execute("SELECT 1 as test")
            logger.info("✅ Database connection test successful")
    except Exception as conn_error:
        logger.warning(f"⚠️ Database connection test failed: {conn_error}")
        logger.warning("⚠️ Will retry during first request")
    
except Exception as e:
    logger.error(f"❌ Failed to create database engine: {e}")
    logger.error(f"❌ DATABASE_URL: {DATABASE_URL}")
    logger.error(f"❌ Error type: {type(e)}")
    # エンジン作成に失敗してもアプリケーションは起動させる（デバッグのため）
    logger.error("❌ Creating dummy engine for debugging...")
    try:
        # SQLiteのダミーエンジンを作成（デバッグ用）
        engine = create_engine("sqlite:///:memory:", echo=False)
        logger.warning("⚠️ Using in-memory SQLite for debugging")
    except:
        logger.error("❌ Failed to create any database engine")
        engine = None

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    logger.debug("📡 Creating database session")
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"❌ Database session error: {e}")
        db.rollback()
        raise
    finally:
        logger.debug("📡 Closing database session")
        db.close()
