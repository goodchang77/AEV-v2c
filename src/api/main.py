# 此檔案已棄用。
#
# 應用程式唯一入口為 `src/main.py`（uvicorn src.main:app），
# Dockerfile 與根目錄 main.py（App Engine 入口）皆轉發該處的 `app` 實例。
#
# 本檔僅為避免歷史 import 引用中斷而保留，直接轉發 src.main 的 app。
from src.main import app

__all__ = ["app"]
