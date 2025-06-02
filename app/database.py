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

# 環境変数の取得
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
SSL_CA_PATH = os.getenv("SSL_CA_PATH")

# DATABASE_URLを構築
if all([DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD]):
    DATABASE_URL = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    logger.info("✅ DATABASE_URL constructed from individual environment variables")
else:
    DATABASE_URL = os.getenv("DATABASE_URL")
    logger.info("⚠️ Using fallback DATABASE_URL environment variable")

# ログ出力
logger.info("🔧 Database configuration:")
logger.info(f"  DB_HOST: {DB_HOST if DB_HOST else 'Not set'}")
logger.info(f"  DB_PORT: {DB_PORT if DB_PORT else 'Not set'}")
logger.info(f"  DB_NAME: {DB_NAME if DB_NAME else 'Not set'}")
logger.info(f"  DB_USER: {DB_USER if DB_USER else 'Not set'}")
logger.info(f"  DB_PASSWORD: {'***' if DB_PASSWORD else 'Not set'}")
logger.info(f"  DATABASE_URL: {DATABASE_URL[:60] if DATABASE_URL else 'Not set'}...")
logger.info(f"  SSL_CA_PATH: {SSL_CA_PATH if SSL_CA_PATH else 'Not set'}")

# SQLAlchemyエンジン作成
engine = None

try:
    if not DATABASE_URL:
        raise ValueError("Database configuration is incomplete")
    
    logger.info("🔗 Creating database engine with Azure MySQL SSL support")

    # SQLAlchemy接続引数
    engine_args = {
        "echo": False,
        "pool_pre_ping": True,
        "pool_recycle": 3600
    }

    # Azure MySQL用SSL設定
    ssl_config = {
        "ssl_disabled": False,
        "ssl_verify_cert": False,  # 証明書検証を無効化
        "ssl_verify_identity": False,  # ID検証を無効化
    }

    # SSL証明書ファイルが存在する場合は使用
    if SSL_CA_PATH and os.path.exists(SSL_CA_PATH):
        logger.info(f"🔒 Using SSL certificate file: {SSL_CA_PATH}")
        ssl_config["ssl_ca"] = SSL_CA_PATH
        # ファイルがある場合でも検証は無効のまま（Azure MySQL用）
    else:
        logger.info("🔒 Using SSL without certificate file verification")

    engine_args["connect_args"] = ssl_config

    # エンジン作成
    engine = create_engine(DATABASE_URL, **engine_args)
    logger.info("✅ Database engine created successfully")

    # テスト接続
    try:
        logger.info("🧪 Testing database connection...")
        with engine.connect() as conn:
            result = conn.execute("SELECT 1 AS test")
            logger.info("✅ Database connection test successful")
    except Exception as conn_error:
        logger.warning(f"⚠️ Database connection test failed: {conn_error}")
        logger.warning("⚠️ Will retry during first request")

except Exception as e:
    logger.error(f"❌ Failed to create database engine: {e}")
    logger.error(f"❌ DATABASE_URL: {DATABASE_URL}")
    logger.error(f"❌ Error type: {type(e)}")
    logger.error("❌ Creating dummy engine for debugging...")
    try:
        engine = create_engine("sqlite:///:memory:", echo=False)
        logger.warning("⚠️ Using in-memory SQLite for debugging")
    except:
        logger.error("❌ Failed to create any database engine")
        engine = None

# セッション設定
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# DBセッション生成関数
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