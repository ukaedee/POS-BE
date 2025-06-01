from pydantic import BaseModel
from typing import List
from datetime import datetime

# Product関連
class ProductBase(BaseModel):
    CODE: str
    NAME: str
    PRICE: int
    STOCK: int

class Product(ProductBase):
    PRD_ID: int

    class Config:
        from_attributes = True

# Purchase関連
class PurchaseItem(BaseModel):
    prd_code: str
    qty: int

class PurchaseRequest(BaseModel):
    emp_cd: str
    items: List[PurchaseItem]

class TransactionDetailResponse(BaseModel):
    DTL_ID: int
    PRD_ID: int
    PRD_CODE: str
    PRD_NAME: str
    PRD_PRICE: int
    QTY: int
    TAX_CD: str

    class Config:
        from_attributes = True

class TransactionResponse(BaseModel):
    TRD_ID: int
    DATETIME: datetime
    EMP_CD: str
    STORE_CD: str
    POS_NO: str
    TOTAL_AMT: int
    TTL_AMT_EX_TAX: int
    details: List[TransactionDetailResponse]

    class Config:
        from_attributes = True 