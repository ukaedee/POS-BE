import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import pymysql

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
try:
    # まずは最も単純な設定で試す
    logger.info("🔗 Creating database engine with basic configuration")
    
    # ENGINE設定を段階的に構築
    engine_args = {
        "echo": False,
        "pool_pre_ping": True,  # 接続の健全性をチェック
        "pool_recycle": 3600   # 1時間で接続をリサイクル
    }
    
    # SSL設定は一旦無効化して基本動作を確認
    # if SSL_CA_PATH and os.path.exists(SSL_CA_PATH):
    #     logger.info(f"🔒 Adding SSL configuration: {SSL_CA_PATH}")
    #     ssl_config = {
    #         "ssl_ca": SSL_CA_PATH,
    #         "ssl_verify_cert": True,
    #         "ssl_verify_identity": False
    #     }
    #     engine_args["connect_args"] = {"ssl": ssl_config}
    
    engine = create_engine(DATABASE_URL, **engine_args)
    
    logger.info("✅ Database engine created successfully")
    
    # 接続テスト
    logger.info("🧪 Testing database connection...")
    with engine.connect() as conn:
        result = conn.execute("SELECT 1 as test")
        logger.info("✅ Database connection test successful")
    
except Exception as e:
    logger.error(f"❌ Failed to create database engine: {e}")
    logger.error(f"❌ DATABASE_URL: {DATABASE_URL}")
    logger.error(f"❌ Error type: {type(e)}")
    raise

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
