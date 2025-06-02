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
    if SSL_CA_PATH:
        logger.info("🔒 Using SSL connection with certificate")
        engine = create_engine(
            DATABASE_URL,
            connect_args={"ssl": {"ssl_ca": SSL_CA_PATH}},
            echo=False  # SQLクエリのログ出力（必要に応じてTrueに）
        )
    else:
        logger.info("🔗 Using standard connection (no SSL certificate)")
        engine = create_engine(
            DATABASE_URL,
            echo=False  # SQLクエリのログ出力（必要に応じてTrueに）
        )
    
    logger.info("✅ Database engine created successfully")
    
except Exception as e:
    logger.error(f"❌ Failed to create database engine: {e}")
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
