from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, CHAR, VARCHAR, TIMESTAMP, DECIMAL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Product(Base):
    __tablename__ = "product_master"

    PRD_ID = Column(Integer, primary_key=True, autoincrement=True)
    CODE = Column(CHAR(13), nullable=False)
    NAME = Column(VARCHAR(50), nullable=False)
    PRICE = Column(Integer, nullable=False)
    STOCK = Column(Integer, nullable=False)

class TaxMaster(Base):
    __tablename__ = "tax_master"

    TAX_CD = Column(CHAR(2), primary_key=True)
    TAX_RATE = Column(DECIMAL(5, 2), nullable=False)

class Transaction(Base):
    __tablename__ = "transactions"

    TRD_ID = Column(Integer, primary_key=True, autoincrement=True)
    DATETIME = Column(TIMESTAMP, default=datetime.now)
    EMP_CD = Column(CHAR(10), nullable=False)
    STORE_CD = Column(CHAR(5), nullable=False)
    POS_NO = Column(CHAR(3), nullable=False)
    TOTAL_AMT = Column(Integer, nullable=False)
    TTL_AMT_EX_TAX = Column(Integer, nullable=False)
    
    # リレーション
    details = relationship("TransactionDetail", back_populates="transaction")

class TransactionDetail(Base):
    __tablename__ = "transaction_details"

    TRD_ID = Column(Integer, ForeignKey("transactions.TRD_ID"), primary_key=True)
    DTL_ID = Column(Integer, primary_key=True, autoincrement=True)
    PRD_ID = Column(Integer, ForeignKey("product_master.PRD_ID"), nullable=False)
    PRD_CODE = Column(CHAR(13), nullable=False)
    PRD_NAME = Column(VARCHAR(50), nullable=False)
    PRD_PRICE = Column(Integer, nullable=False)
    QTY = Column(Integer, nullable=False)
    TAX_CD = Column(CHAR(2), ForeignKey("tax_master.TAX_CD"), nullable=False)
    
    # リレーション
    transaction = relationship("Transaction", back_populates="details")
    product = relationship("Product")
    tax_master = relationship("TaxMaster") 