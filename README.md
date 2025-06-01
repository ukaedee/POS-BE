# POSアプリ Backend API

FastAPIを使用したPOSアプリのバックエンドAPIです。

## セットアップ

### 1. 依存関係のインストール
```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定
プロジェクトルートに`.env`ファイルを作成し、以下の環境変数を設定してください：

```env
# Azure MySQL接続URL例
DATABASE_URL=mysql://username:password@servername.mysql.database.azure.com:3306/database_name

# SSL CA証明書のパス（Azure MySQLの場合）
SSL_CA_PATH=/path/to/DigiCertGlobalRootG2.crt.pem
```

### 3. アプリケーションの起動
```bash
python run.py
```

アプリケーションは `http://localhost:8000` で起動します。
API ドキュメントは `http://localhost:8000/docs` で確認できます。

## テスト用APIエンドポイント

### ヘルスチェック
- **GET** `/ping`
- 接続確認用（データベース接続不要）

### 全商品取得
- **GET** `/products`
- product_masterテーブルの全データを取得

### 商品マスタ検索API
- **GET** `/products/{code}`
- 商品コードから商品情報を取得

### 購入登録API
- **POST** `/purchase`
- 購入データを登録

## Azure MySQL接続確認手順

1. `/ping` エンドポイントで基本的な動作確認
2. `/products` エンドポイントでMySQL接続確認
3. データが返ってくれば接続成功！ 