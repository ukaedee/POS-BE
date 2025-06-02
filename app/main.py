from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from . import models, schemas
from .database import get_db

app = FastAPI(title="POS API", description="POS Application Backend API")

# 設定値
TAX_RATE = 0.10  # 10%
DEFAULT_STORE_CD = "00001"  # デフォルト店舗コード
DEFAULT_POS_NO = "001"      # デフォルトPOS番号
DEFAULT_TAX_CD = "10"       # デフォルト税区分（10%）
DEFAULT_EMP_CD = "9999999999"  # デフォルト従業員コード

@app.get("/products", response_model=List[schemas.Product])
def get_all_products(db: Session = Depends(get_db)):
    products = db.query(models.Product).all()
    return products

@app.get("/products/{code}", response_model=schemas.Product)
def get_product(code: str, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.CODE == code).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.get("/transactions/{transaction_id}", response_model=schemas.TransactionDetailWithTotals)
def get_transaction_details(transaction_id: int, db: Session = Depends(get_db)):
    # トランザクション存在チェック
    transaction = db.query(models.Transaction).filter(models.Transaction.TRD_ID == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # 明細データを税率マスタと結合して取得
    details_with_tax = db.query(
        models.TransactionDetail,
        models.TaxMaster.TAX_RATE
    ).join(
        models.TaxMaster, 
        models.TransactionDetail.TAX_CD == models.TaxMaster.TAX_CD
    ).filter(
        models.TransactionDetail.TRD_ID == transaction_id
    ).all()
    
    items = []
    total_excl_tax = 0
    total_tax = 0
    
    for detail, tax_rate in details_with_tax:
        # 各商品の計算
        unit_price = detail.PRD_PRICE
        quantity = detail.QTY
        subtotal_excl_tax = unit_price * quantity
        
        # 税額計算（小数点以下切り捨て）
        tax_amount = int(subtotal_excl_tax * (float(tax_rate) / 100))
        price_incl_tax = subtotal_excl_tax + tax_amount
        
        items.append(schemas.TransactionItemDetail(
            name=detail.PRD_NAME,
            unit_price=unit_price,
            quantity=quantity,
            tax_rate=float(tax_rate),
            tax_amount=tax_amount,
            price_incl_tax=price_incl_tax
        ))
        
        total_excl_tax += subtotal_excl_tax
        total_tax += tax_amount
    
    total_incl_tax = total_excl_tax + total_tax
    
    return schemas.TransactionDetailWithTotals(
        transaction_id=transaction_id,
        items=items,
        total_excl_tax=total_excl_tax,
        total_tax=total_tax,
        total_incl_tax=total_incl_tax
    )

@app.post("/purchase", response_model=schemas.TransactionResponse)
def create_purchase(purchase_data: schemas.PurchaseRequest, db: Session = Depends(get_db)):
    try:
        # emp_cdのデフォルト値設定
        emp_cd = purchase_data.emp_cd if purchase_data.emp_cd else DEFAULT_EMP_CD
        
        # 商品情報取得と在庫チェック
        purchase_items = []
        total_amount_ex_tax = 0
        
        for item in purchase_data.items:
            # 数量バリデーション（Pydanticで1以上はチェック済み）
            
            # 商品コードで商品を検索
            product = db.query(models.Product).filter(models.Product.CODE == item.prd_code).first()
            if not product:
                raise HTTPException(status_code=404, detail=f"Product not found: {item.prd_code}")
            
            # 在庫チェック
            if product.STOCK < item.qty:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Insufficient stock for {product.NAME}. Available: {product.STOCK}, Requested: {item.qty}"
                )
            
            # 購入アイテム情報を保存
            purchase_items.append({
                "product": product,
                "qty": item.qty,
                "subtotal": product.PRICE * item.qty
            })
            
            total_amount_ex_tax += product.PRICE * item.qty

        # 税込金額計算
        tax_amount = int(total_amount_ex_tax * TAX_RATE)
        total_amount = total_amount_ex_tax + tax_amount

        # 1. transactionヘッダを作成
        db_transaction = models.Transaction(
            EMP_CD=emp_cd,
            STORE_CD=DEFAULT_STORE_CD,
            POS_NO=DEFAULT_POS_NO,
            TOTAL_AMT=total_amount,
            TTL_AMT_EX_TAX=total_amount_ex_tax
        )
        db.add(db_transaction)
        db.flush()  # TRD_IDを取得

        # 2. transaction_details明細を作成
        transaction_details = []
        for idx, item_data in enumerate(purchase_items):
            detail = models.TransactionDetail(
                TRD_ID=db_transaction.TRD_ID,
                DTL_ID=idx + 1,  # 連番
                PRD_ID=item_data["product"].PRD_ID,
                PRD_CODE=item_data["product"].CODE,
                PRD_NAME=item_data["product"].NAME,
                PRD_PRICE=item_data["product"].PRICE,
                QTY=item_data["qty"],
                TAX_CD=DEFAULT_TAX_CD
            )
            db.add(detail)
            transaction_details.append(detail)

        # 3. 在庫を減らす
        for item_data in purchase_items:
            item_data["product"].STOCK -= item_data["qty"]

        # コミット
        db.commit()
        db.refresh(db_transaction)

        # レスポンス作成
        return schemas.TransactionResponse(
            TRD_ID=db_transaction.TRD_ID,
            DATETIME=db_transaction.DATETIME,
            EMP_CD=db_transaction.EMP_CD,
            STORE_CD=db_transaction.STORE_CD,
            POS_NO=db_transaction.POS_NO,
            TOTAL_AMT=db_transaction.TOTAL_AMT,
            TTL_AMT_EX_TAX=db_transaction.TTL_AMT_EX_TAX,
            details=[
                schemas.TransactionDetailResponse(
                    DTL_ID=detail.DTL_ID,
                    PRD_ID=detail.PRD_ID,
                    PRD_CODE=detail.PRD_CODE,
                    PRD_NAME=detail.PRD_NAME,
                    PRD_PRICE=detail.PRD_PRICE,
                    QTY=detail.QTY,
                    TAX_CD=detail.TAX_CD
                ) for detail in transaction_details
            ]
        )

    except Exception as e:
        db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Purchase processing failed: {str(e)}") 