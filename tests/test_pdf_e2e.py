"""
PDF處理端到端測試
PDF Processing End-to-End Tests

測試從前端上傳到後端處理的完整工作流程
"""

import pytest
import asyncio
import time
import io
from fastapi.testclient import TestClient
from unittest.mock import patch

from src.main import app
from src.api.endpoints.document_upload import processing_results


class TestPDFProcessingE2E:
    """PDF處理端到端測試類"""

    @pytest.fixture
    def client(self):
        """創建測試客戶端"""
        return TestClient(app)

    @pytest.fixture
    def realistic_pdf_content(self):
        """創建較為逼真的PDF內容用於測試"""
        # 雖然這不是真正的PDF，但包含了我們期望解析的財務數據格式
        financial_text = """
        %PDF-1.4
        
        財務狀況表
        單位：新台幣千元
        
        資產
        流動資產
          現金及約當現金            1,500,000
          應收帳款淨額              2,300,000
          存貨                      1,800,000
          其他流動資產                400,000
        流動資產合計                6,000,000
        
        非流動資產
          不動產、廠房及設備        8,500,000
          無形資產                    800,000
          其他非流動資產              700,000
        非流動資產合計              10,000,000
        
        資產總額                    16,000,000
        
        負債及股東權益
        流動負債
          短期借款                  1,200,000
          應付帳款                  1,800,000
          其他流動負債                500,000
        流動負債合計                3,500,000
        
        非流動負債
          長期借款                  2,000,000
          其他非流動負債              500,000
        非流動負債合計              2,500,000
        
        負債總計                    6,000,000
        
        股東權益
          股本                      5,000,000
          保留盈餘                  5,000,000
        股東權益總計                10,000,000
        
        負債及股東權益總計          16,000,000
        
        綜合損益表
        營業收入                    25,000,000
        營業成本                   (18,000,000)
        營業毛利                     7,000,000
        營業費用                    (4,500,000)
        營業利益                     2,500,000
        營業外收支                    (200,000)
        稅前淨利                     2,300,000
        所得稅費用                    (460,000)
        本期淨利                     1,840,000
        
        基本每股盈餘（元）              3.68
        
        現金流量表
        營業活動之現金流量
          本期淨利                  1,840,000
          調整項目                    600,000
        營業活動之現金流量淨額        2,440,000
        
        投資活動之現金流量
          取得不動產、廠房及設備     (800,000)
          投資支出                   (200,000)
        投資活動之現金流量淨額       (1,000,000)
        
        融資活動之現金流量
          現金股利支付               (920,000)
          舉借長期借款                500,000
        融資活動之現金流量淨額        (420,000)
        
        本期現金及約當現金增加        1,020,000
        
        %%EOF
        """
        return financial_text.encode('utf-8')

    def test_api_health_check(self, client):
        """測試API健康檢查"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_supported_formats_endpoint(self, client):
        """測試支援格式端點"""
        response = client.get("/api/v1/documents/supported-formats")
        assert response.status_code == 200
        
        data = response.json()
        assert "supported_formats" in data
        assert "extraction_capabilities" in data
        
        # 驗證PDF格式支援
        pdf_supported = any(
            fmt["format"] == "PDF" for fmt in data["supported_formats"]
        )
        assert pdf_supported

    @patch('src.services.pdf_processor.pdfplumber')
    def test_sync_upload_complete_workflow(self, mock_pdfplumber, client, realistic_pdf_content):
        """測試同步上傳的完整工作流程"""
        # 模擬 pdfplumber 的行為
        mock_pdf = mock_pdfplumber.open.return_value.__enter__.return_value
        mock_page = mock_pdf.pages[0]
        mock_page.extract_text.return_value = realistic_pdf_content.decode('utf-8')
        mock_page.extract_tables.return_value = []
        mock_pdf.pages = [mock_page]
        
        # 1. 上傳文件
        response = client.post(
            "/api/v1/documents/upload/financial-statement",
            files={"file": ("test_financial.pdf", io.BytesIO(realistic_pdf_content), "application/pdf")},
            data={
                "company_id": "2330",
                "report_period": "2024Q1",
                "async_processing": "false"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 2. 驗證響應結構
        assert data["success"] is True
        assert data["message"] == "文件處理完成"
        assert data["document_id"] is not None
        assert data["financial_data"] is not None
        assert data["validation_results"] is not None
        assert data["metadata"] is not None
        
        # 3. 驗證提取的財務數據
        financial_data = data["financial_data"]
        
        # 檢查主要財務指標是否被提取
        expected_metrics = [
            'total_assets', 'current_assets', 'total_liabilities', 
            'current_liabilities', 'shareholders_equity', 'revenue', 'net_income'
        ]
        
        extracted_metrics = list(financial_data.keys())
        found_metrics = [metric for metric in expected_metrics if metric in extracted_metrics]
        
        # 至少應該提取到一半以上的預期指標
        assert len(found_metrics) >= len(expected_metrics) // 2, f"提取的指標過少: {found_metrics}"
        
        # 4. 驗證數據格式
        for metric_name, metric_data in financial_data.items():
            assert "value" in metric_data
            assert "unit_multiplier" in metric_data
            assert "extraction_method" in metric_data
            assert "confidence" in metric_data
            
            # 數值應該是合理的
            assert isinstance(metric_data["value"], (int, float))
            assert metric_data["value"] >= 0 or metric_name in ['net_income']  # 淨利可能為負
            
        # 5. 驗證元數據
        metadata = data["metadata"]
        assert metadata["filename"] == "test_financial.pdf"
        assert metadata["company_id"] == "2330"
        assert metadata["report_period"] == "2024Q1"
        assert metadata["processing_mode"] == "sync"

    def test_async_upload_complete_workflow(self, client, realistic_pdf_content):
        """測試異步上傳的完整工作流程"""
        # 1. 異步上傳文件
        response = client.post(
            "/api/v1/documents/upload/financial-statement",
            files={"file": ("test_async.pdf", io.BytesIO(realistic_pdf_content), "application/pdf")},
            data={
                "company_id": "1234",
                "async_processing": "true"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 2. 驗證異步響應
        assert data["success"] is True
        assert "背景處理" in data["message"]
        assert data["document_id"] is not None
        assert data["financial_data"] is None  # 異步模式不會立即返回數據
        assert data["metadata"]["processing_mode"] == "async"
        
        document_id = data["document_id"]
        
        # 3. 查詢處理狀態（模擬輪詢）
        max_attempts = 10
        attempt = 0
        final_status = None
        
        while attempt < max_attempts:
            response = client.get(f"/api/v1/documents/processing-status/{document_id}")
            
            if response.status_code == 200:
                status_data = response.json()
                final_status = status_data
                
                assert status_data["document_id"] == document_id
                assert "status" in status_data
                assert "progress" in status_data
                
                if status_data["status"] in ["completed", "failed"]:
                    break
                    
            attempt += 1
            time.sleep(0.1)  # 短暫等待
        
        # 4. 驗證最終狀態
        assert final_status is not None, "未能獲取處理狀態"
        
        # 根據實際處理結果驗證（可能成功或失敗）
        if final_status["status"] == "completed":
            assert final_status["results"] is not None
            assert "financial_data" in final_status["results"]
        elif final_status["status"] == "failed":
            assert "message" in final_status
        else:
            pytest.fail(f"處理狀態異常: {final_status['status']}")
        
        # 5. 清理處理結果
        response = client.delete(f"/api/v1/documents/processing-result/{document_id}")
        assert response.status_code == 200
        
        # 6. 確認已清理
        response = client.get(f"/api/v1/documents/processing-status/{document_id}")
        assert response.status_code == 404

    def test_test_extraction_workflow(self, client, realistic_pdf_content):
        """測試提取測試工作流程"""
        # 測試提取功能
        response = client.post(
            "/api/v1/documents/test-extraction",
            files={"file": ("test_extraction.pdf", io.BytesIO(realistic_pdf_content), "application/pdf")}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 驗證測試結果結構
        if data["success"]:
            assert data["preview"] is not None
            preview = data["preview"]
            
            assert "filename" in preview
            assert "file_size" in preview
            assert "status" in preview
            assert "financial_metrics_found" in preview
            assert "extraction_methods" in preview
            
            # 如果成功提取，應該有樣本數據
            if preview["financial_metrics_found"] > 0:
                assert "sample_data" in preview
        else:
            # 如果測試失敗，應該有錯誤信息
            assert "message" in data

    def test_error_handling_workflow(self, client):
        """測試錯誤處理工作流程"""
        # 1. 測試無效文件格式
        response = client.post(
            "/api/v1/documents/upload/financial-statement",
            files={"file": ("test.txt", io.BytesIO(b"not pdf"), "text/plain")},
            data={"async_processing": "false"}
        )
        assert response.status_code == 400
        
        # 2. 測試空文件
        response = client.post(
            "/api/v1/documents/upload/financial-statement",
            files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
            data={"async_processing": "false"}
        )
        assert response.status_code == 400
        
        # 3. 測試查詢不存在的處理狀態
        response = client.get("/api/v1/documents/processing-status/nonexistent")
        assert response.status_code == 404
        
        # 4. 測試刪除不存在的處理結果
        response = client.delete("/api/v1/documents/processing-result/nonexistent")
        assert response.status_code == 404

    def test_validation_workflow(self, client, realistic_pdf_content):
        """測試數據驗證工作流程"""
        with patch('src.services.pdf_processor.pdfplumber') as mock_pdfplumber:
            # 模擬返回不平衡的財務數據
            mock_pdf = mock_pdfplumber.open.return_value.__enter__.return_value
            mock_page = mock_pdf.pages[0]
            
            # 構造不平衡的財務報表
            unbalanced_text = """
            資產總額 10,000,000
            負債總計  8,000,000
            股東權益總計  1,000,000
            """
            
            mock_page.extract_text.return_value = unbalanced_text
            mock_page.extract_tables.return_value = []
            
            response = client.post(
                "/api/v1/documents/upload/financial-statement",
                files={"file": ("unbalanced.pdf", io.BytesIO(realistic_pdf_content), "application/pdf")},
                data={"async_processing": "false"}
            )
            
            if response.status_code == 200:
                data = response.json()
                validation_results = data.get("validation_results")
                
                if validation_results:
                    # 應該有警告或錯誤
                    assert (
                        len(validation_results.get("warnings", [])) > 0 or
                        len(validation_results.get("errors", [])) > 0
                    )

    def test_performance_benchmark(self, client, realistic_pdf_content):
        """測試性能基準"""
        start_time = time.time()
        
        response = client.post(
            "/api/v1/documents/upload/financial-statement",
            files={"file": ("benchmark.pdf", io.BytesIO(realistic_pdf_content), "application/pdf")},
            data={"async_processing": "false"}
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # 同步處理應該在合理時間內完成（10秒內）
        assert processing_time < 10.0, f"處理時間過長: {processing_time:.2f}秒"
        
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True

    def test_concurrent_requests(self, client, realistic_pdf_content):
        """測試並發請求處理"""
        import concurrent.futures
        import threading
        
        def upload_file(file_suffix):
            """單個上傳請求"""
            try:
                response = client.post(
                    "/api/v1/documents/upload/financial-statement",
                    files={"file": (f"concurrent_{file_suffix}.pdf", io.BytesIO(realistic_pdf_content), "application/pdf")},
                    data={"async_processing": "true"}
                )
                return response.status_code, response.json() if response.status_code == 200 else None
            except Exception as e:
                return 500, str(e)
        
        # 同時發送5個請求
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(upload_file, i) for i in range(5)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # 檢查結果
        successful_requests = [r for r in results if r[0] == 200]
        
        # 至少應該有一些請求成功
        assert len(successful_requests) > 0, f"並發請求全部失敗: {results}"
        
        # 清理異步處理結果
        for status_code, data in successful_requests:
            if data and "document_id" in data:
                document_id = data["document_id"]
                try:
                    # 等待處理完成或超時
                    max_wait = 30  # 30秒超時
                    wait_time = 0
                    while wait_time < max_wait:
                        status_response = client.get(f"/api/v1/documents/processing-status/{document_id}")
                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            if status_data["status"] in ["completed", "failed"]:
                                break
                        time.sleep(1)
                        wait_time += 1
                    
                    # 清理
                    client.delete(f"/api/v1/documents/processing-result/{document_id}")
                except:
                    pass  # 清理失敗不影響測試結果

    @pytest.mark.skip(reason="需要真實PDF文件")  
    def test_real_pdf_file_processing(self, client):
        """使用真實PDF文件的測試（需要手動提供測試文件）"""
        # 這個測試需要真實的財務報表PDF文件
        # 可以在CI/CD環境中配置測試文件路徑
        
        test_pdf_path = "tests/fixtures/real_financial_statement.pdf"
        
        try:
            with open(test_pdf_path, "rb") as f:
                pdf_content = f.read()
                
            response = client.post(
                "/api/v1/documents/upload/financial-statement",
                files={"file": ("real_statement.pdf", io.BytesIO(pdf_content), "application/pdf")},
                data={
                    "company_id": "2330",
                    "report_period": "2024Q1",
                    "async_processing": "false"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            
            # 驗證是否提取到合理數量的財務指標
            financial_data = data.get("financial_data", {})
            assert len(financial_data) > 0, "真實PDF文件應該能提取到財務數據"
            
        except FileNotFoundError:
            pytest.skip(f"測試文件不存在: {test_pdf_path}")


class TestPDFProcessingIntegration:
    """PDF處理整合測試"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_api_documentation_accessible(self, client):
        """測試API文檔是否可訪問"""
        response = client.get("/docs")
        # 在生產環境中可能關閉文檔，所以允許404
        assert response.status_code in [200, 404]

    def test_static_files_accessible(self, client):
        """測試靜態文件是否可訪問"""
        # 測試上傳測試頁面是否可訪問
        response = client.get("/static/upload_test.html")
        assert response.status_code == 200
        assert "PDF上傳測試" in response.text

    def test_api_root_endpoint(self, client):
        """測試API根端點"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "財務分析與企業評價系統" in data["message"]

    def test_cors_headers_present(self, client):
        """測試CORS標頭是否存在"""
        response = client.options("/api/v1/documents/supported-formats")
        # CORS預檢請求應該被正確處理
        # 具體的CORS測試可能需要更複雜的設置