from pydantic import BaseModel, Field
from typing import List, Optional
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
    qty: int = Field(ge=1, description="数量は1以上である必要があります")

class PurchaseRequest(BaseModel):
    emp_cd: Optional[str] = None
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

# トランザクション詳細取得用スキーマ
class TransactionItemDetail(BaseModel):
    name: str
    unit_price: int
    quantity: int
    tax_rate: float
    tax_amount: int
    price_incl_tax: int

class TransactionDetailWithTotals(BaseModel):
    transaction_id: int
    items: List[TransactionItemDetail]
    total_excl_tax: int
    total_tax: int
    total_incl_tax: int 