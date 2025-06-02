import logging
import sys
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
import os

from . import models, schemas
from .database import get_db

# Azure App Service用のログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.StreamHandler(sys.stderr)
    ]
)

logger = logging.getLogger(__name__)

app = FastAPI(title="POS API", description="POS Application Backend API")

# 設定値
TAX_RATE = 0.10  # 10%
DEFAULT_STORE_CD = "00001"  # デフォルト店舗コード
DEFAULT_POS_NO = "001"      # デフォルトPOS番号
DEFAULT_TAX_CD = "10"       # デフォルト税区分（10%）
DEFAULT_EMP_CD = "9999999999"  # デフォルト従業員コード

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 POS API is starting up...")
    logger.info("📋 Application configuration:")
    logger.info(f"  TAX_RATE: {TAX_RATE}")
    logger.info(f"  DEFAULT_STORE_CD: {DEFAULT_STORE_CD}")
    logger.info(f"  DEFAULT_POS_NO: {DEFAULT_POS_NO}")
    
    # データベース接続テスト
    try:
        logger.info("🔍 Testing database connection...")
        # より安全なインポート
        import app.database as db_module
        with db_module.engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test")).fetchone()
            logger.info("✅ Database connection successful")
    except ImportError as e:
        logger.error(f"❌ Database module import failed: {e}")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")

@app.get("/")
def root():
    """ルートエンドポイント"""
    logger.info("🏠 Root endpoint accessed")
    return {
        "message": "POS API is running",
        "status": "ok",
        "endpoints": {
            "products": "/products",
            "purchase": "/purchase",
            "transactions": "/transactions/{id}"
        }
    }



@app.get("/products", response_model=List[schemas.Product])
def get_all_products(db: Session = Depends(get_db)):
    try:
        logger.info("📦 Fetching all products")
        products = db.query(models.Product).all()
        logger.info(f"✅ Found {len(products)} products")
        return products
    except Exception as e:
        logger.error(f"❌ Error fetching products: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/products/{code}", response_model=schemas.Product)
def get_product(code: str, db: Session = Depends(get_db)):
    try:
        logger.info(f"🔍 Searching for product with code: {code}")
        product = db.query(models.Product).filter(models.Product.CODE == code).first()
        if product is None:
            logger.warning(f"⚠️ Product not found: {code}")
            raise HTTPException(status_code=404, detail="Product not found")
        logger.info(f"✅ Found product: {product.NAME}")
        return product
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching product {code}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/transactions/{transaction_id}", response_model=schemas.TransactionDetailWithTotals)
def get_transaction_details(transaction_id: int, db: Session = Depends(get_db)):
    try:
        logger.info(f"🔍 Fetching transaction details for ID: {transaction_id}")
        
        # トランザクション存在チェック
        transaction = db.query(models.Transaction).filter(models.Transaction.TRD_ID == transaction_id).first()
        if not transaction:
            logger.warning(f"⚠️ Transaction not found: {transaction_id}")
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
        
        # 明細データが存在するかチェック
        if not details_with_tax:
            logger.warning(f"⚠️ Transaction details not found: {transaction_id}")
            raise HTTPException(status_code=404, detail="Transaction details not found")
        
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
        
        logger.info(f"✅ Transaction details fetched: {len(items)} items, total: {total_incl_tax}")
        
        return schemas.TransactionDetailWithTotals(
            transaction_id=transaction_id,
            items=items,
            total_excl_tax=total_excl_tax,
            total_tax=total_tax,
            total_incl_tax=total_incl_tax
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching transaction details {transaction_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/purchase", response_model=schemas.TransactionResponse)
def create_purchase(purchase_data: schemas.PurchaseRequest, db: Session = Depends(get_db)):
    try:
        logger.info(f"💳 Processing purchase for emp_cd: {purchase_data.emp_cd}")
        logger.info(f"📦 Items: {len(purchase_data.items)}")
        
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
                logger.warning(f"⚠️ Product not found: {item.prd_code}")
                raise HTTPException(status_code=404, detail=f"Product not found: {item.prd_code}")
            
            # 在庫チェック
            if product.STOCK < item.qty:
                logger.warning(f"⚠️ Insufficient stock for {product.NAME}: available={product.STOCK}, requested={item.qty}")
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

        logger.info(f"💰 Calculated totals: excl_tax={total_amount_ex_tax}, tax={tax_amount}, incl_tax={total_amount}")

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

        logger.info(f"✅ Transaction created: TRD_ID={db_transaction.TRD_ID}")

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
            old_stock = item_data["product"].STOCK
            item_data["product"].STOCK -= item_data["qty"]
            logger.info(f"📦 Stock updated for {item_data['product'].NAME}: {old_stock} -> {item_data['product'].STOCK}")

        # コミット
        db.commit()
        db.refresh(db_transaction)

        logger.info(f"✅ Purchase completed successfully: TRD_ID={db_transaction.TRD_ID}")

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

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"❌ Purchase processing failed: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Purchase processing failed: {str(e)}")

@app.get("/debug")
def debug_info():
    """デバッグ情報エンドポイント"""
    logger.info("🔍 Debug info requested")
    
    try:
        # 環境変数の確認
        env_vars = {
            "DATABASE_URL": os.getenv("DATABASE_URL", "Not set")[:50] + "..." if os.getenv("DATABASE_URL") else "Not set",
            "SSL_CA_PATH": os.getenv("SSL_CA_PATH", "Not set"),
            "PORT": os.getenv("PORT", "Not set"),
            "PYTHONPATH": os.getenv("PYTHONPATH", "Not set"),
            "WEBSITE_HOSTNAME": os.getenv("WEBSITE_HOSTNAME", "Not set")
        }
        
        # システム情報
        system_info = {
            "python_version": sys.version,
            "current_working_directory": os.getcwd(),
            "python_path": sys.path[:3]  # 最初の3つのパスのみ
        }
        
        # モジュールのインポートテスト
        import_status = {}
        modules_to_test = ["sqlalchemy", "pymysql", "fastapi", "uvicorn", "pydantic"]
        
        for module in modules_to_test:
            try:
                __import__(module)
                import_status[module] = "✅ OK"
            except ImportError as e:
                import_status[module] = f"❌ Failed: {str(e)}"
        
        return {
            "status": "debug_info",
            "environment_variables": env_vars,
            "system_info": system_info,
            "import_status": import_status,
            "message": "Debug information collected successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Debug info collection failed: {e}")
        return {
            "status": "debug_error",
            "error": str(e),
            "message": "Failed to collect debug information"
        }