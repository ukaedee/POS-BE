import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import pymysql

# PyMySQLをMySQLドライバとして使用
pymysql.install_as_MySQLdb()

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SSL_CA_PATH = os.getenv("SSL_CA_PATH")

# Azure App Service用の設定
if SSL_CA_PATH:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"ssl": {"ssl_ca": SSL_CA_PATH}}
    )
else:
    # SSL証明書パスが設定されていない場合（開発環境等）
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
