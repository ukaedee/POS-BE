import os
import uvicorn

if __name__ == "__main__":
    # Azure App Serviceでは環境変数PORTが設定される
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False) 