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

DATABASE_URL = os.getenv("DATABASE_URL")
SSL_CA_PATH = os.getenv("SSL_CA_PATH")

logger.info("🔧 Database configuration:")
logger.info(f"  DATABASE_URL: {DATABASE_URL[:50] if DATABASE_URL else 'Not set'}...")
logger.info(f"  SSL_CA_PATH: {SSL_CA_PATH if SSL_CA_PATH else 'Not set'}")

# Azure App Service用の設定
engine = None

try:
    if not DATABASE_URL:
        logger.error("❌ DATABASE_URL is not set")
        raise ValueError("DATABASE_URL environment variable is required")
    
    logger.info("🔗 Creating database engine with fixed SSL configuration")
    
    # DATABASE_URLからSSLクエリパラメータを削除
    parsed_url = urlparse(DATABASE_URL)
    clean_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
    
    # クエリパラメータをチェック
    if parsed_url.query:
        logger.info(f"🔍 Original URL query parameters: {parsed_url.query}")
        query_params = parse_qs(parsed_url.query)
        ssl_enabled = query_params.get('ssl', ['false'])[0].lower() == 'true'
        logger.info(f"🔒 SSL enabled from URL: {ssl_enabled}")
    else:
        ssl_enabled = False
    
    logger.info(f"🔗 Clean DATABASE_URL: {clean_url[:50]}...")
    
    # ENGINE設定を構築
    engine_args = {
        "echo": False,
        "pool_pre_ping": True,
        "pool_recycle": 3600
    }
    
    # SSLが必要な場合の設定
    if ssl_enabled:
        logger.info("🔒 Configuring SSL connection")
        # PyMySQLのSSL設定を適切に構成
        ssl_config = {
            "ssl_disabled": False,
            "ssl_verify_cert": False,
            "ssl_verify_identity": False
        }
        
        # SSL証明書ファイルがある場合
        if SSL_CA_PATH and os.path.exists(SSL_CA_PATH):
            logger.info(f"🔒 Using SSL certificate file: {SSL_CA_PATH}")
            ssl_config["ssl_ca"] = SSL_CA_PATH
            ssl_config["ssl_verify_cert"] = True
        
        engine_args["connect_args"] = ssl_config
    else:
        logger.info("🔗 Using connection without explicit SSL configuration")
    
    # エンジンを作成（clean_urlを使用）
    engine = create_engine(clean_url, **engine_args)
    
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
