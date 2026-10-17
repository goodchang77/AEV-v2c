# 貢獻指南 / Contributing

AEV-v2c 是早期開發專案，歡迎小範圍、可驗證的修正。請先閱讀 [README](README.md) 的環境需求、限制與測試方式。

## 提出問題

1. 先搜尋既有 issue，避免重複。
2. 說明環境、重現步驟、預期與實際結果。
3. 僅附可公開的最小資料；不得上傳客戶財報、個資、存取憑證或私人部署資訊。
4. 安全問題請依 [SECURITY.md](SECURITY.md) 私下回報。

## 提交 Pull Request

1. Fork 專案並建立聚焦單一主題的分支。
2. 錯誤修正請附回歸測試；財務模型變動須說明公式、假設、資料來源、幣別、單位與邊界條件。
3. 更新受影響文件，勿把規劃寫成已完成或把示範資料寫成正式財報。
4. 在隔離的開發環境執行適用檢查：

```bash
python scripts/import_smoke_test.py
python -m pytest tests/ -q -W ignore
python scripts/api_db_test.py
```

完整流程需要測試用 PostgreSQL／Redis；不可使用正式資料庫。若部分檢查無法執行，請在 PR 清楚列出原因與實際執行結果。

5. PR 請列出變更摘要、測試證據及已知限制，等待維護者審查與 CI 結果。

## AI 輔助貢獻

可以使用 AI 協助，但提交者仍須閱讀差異、檢查第三方權利並對內容負責。不得提交虛構測試結果、虛構資料來源或未經核准的機密資料。

本專案原創程式碼採 [MIT License](LICENSE)；請保留第三方內容原有的授權與標示。
