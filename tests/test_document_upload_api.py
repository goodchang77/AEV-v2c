"""
文件上傳API端點測試
Document Upload API Endpoints Tests
"""

import pytest
import io
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import UploadFile

from src.main import app
from src.api.endpoints.document_upload import processing_results


class TestDocumentUploadAPI:
    """文件上傳API測試類"""

    @pytest.fixture
    def client(self):
        """創建測試客戶端"""
        return TestClient(app)

    @pytest.fixture
    def sample_pdf_file(self):
        """創建樣本PDF文件"""
        # 簡化的PDF內容
        pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\nxref\n0 2\ntrailer\n<< /Size 2 /Root 1 0 R >>\nstartxref\n%%EOF"
        return ("test_financial.pdf", pdf_content, "application/pdf")

    @pytest.fixture
    def mock_processing_result(self):
        """模擬PDF處理結果"""
        return {
            'status': 'success',
            'filename': 'test_financial.pdf',
            'financial_data': {
                'total_assets': {
                    'value': 16000000.0,
                    'unit_multiplier': 1000,
                    'extraction_method': 'pdfplumber',
                    'confidence': 0.85,
                    'candidates_count': 1
                },
                'revenue': {
                    'value': 25000000.0,
                    'unit_multiplier': 1000,
                    'extraction_method': 'pdfplumber',
                    'confidence': 0.90,
                    'candidates_count': 1
                },
                'net_income': {
                    'value': 1840000.0,
                    'unit_multiplier': 1000,
                    'extraction_method': 'pdfplumber',
                    'confidence': 0.88,
                    'candidates_count': 1
                }
            },
            'extraction_methods': ['pdfplumber'],
            'metadata': {
                'total_pages': 10,
                'file_size': 1024000
            }
        }

    @pytest.fixture
    def mock_validation_result(self):
        """模擬數據驗證結果"""
        return {
            'is_valid': True,
            'warnings': ['流動比率偏低，請注意流動性風險'],
            'errors': [],
            'suggestions': ['建議增加現金及約當現金比重']
        }

    def test_get_supported_formats(self, client):
        """測試獲取支援格式端點"""
        response = client.get("/api/v1/documents/supported-formats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "supported_formats" in data
        assert "extraction_capabilities" in data
        assert "processing_methods" in data
        
        # 確認支援PDF格式
        formats = data["supported_formats"]
        pdf_format = next((f for f in formats if f["format"] == "PDF"), None)
        assert pdf_format is not None
        assert ".pdf" in pdf_format["extensions"]

    @patch('src.api.endpoints.document_upload.pdf_processor.process_pdf')
    @patch('src.api.endpoints.document_upload.pdf_processor.validate_financial_data')
    def test_upload_financial_statement_sync_success(
        self, 
        mock_validate, 
        mock_process, 
        client, 
        sample_pdf_file,
        mock_processing_result,
        mock_validation_result
    ):
        """測試同步上傳財務報表成功"""
        # 設置模擬返回值
        mock_process.return_value = mock_processing_result
        mock_validate.return_value = mock_validation_result

        filename, content, content_type = sample_pdf_file
        
        response = client.post(
            "/api/v1/documents/upload/financial-statement",
            files={"file": (filename, io.BytesIO(content), content_type)},
            data={
                "company_id": "2330",
                "report_period": "2024Q1",
                "async_processing": "false"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["message"] == "文件處理完成"
        assert data["document_id"] is not None
        assert data["financial_data"] is not None
        assert data["validation_results"] is not None
        
        # 檢查財務數據
        financial_data = data["financial_data"]
        assert "total_assets" in financial_data
        assert "revenue" in financial_data
        assert "net_income" in financial_data
        
        # 檢查元數據
        metadata = data["metadata"]
        assert metadata["filename"] == filename
        assert metadata["company_id"] == "2330"
        assert metadata["report_period"] == "2024Q1"
        assert metadata["processing_mode"] == "sync"

    def test_upload_financial_statement_async_success(self, client, sample_pdf_file):
        """測試異步上傳財務報表成功"""
        filename, content, content_type = sample_pdf_file
        
        response = client.post(
            "/api/v1/documents/upload/financial-statement",
            files={"file": (filename, io.BytesIO(content), content_type)},
            data={
                "company_id": "2330",
                "async_processing": "true"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["message"] == "文件上傳成功，正在背景處理中"
        assert data["document_id"] is not None
        assert data["financial_data"] is None  # 異步模式下不會立即返回數據
        assert data["metadata"]["processing_mode"] == "async"

    def test_upload_invalid_file_format(self, client):
        """測試上傳無效文件格式"""
        # 上傳非PDF文件
        response = client.post(
            "/api/v1/documents/upload/financial-statement",
            files={"file": ("test.txt", io.BytesIO(b"plain text"), "text/plain")},
            data={"async_processing": "false"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "僅支援PDF格式文件" in data["detail"]

    def test_upload_empty_file(self, client):
        """測試上傳空文件"""
        response = client.post(
            "/api/v1/documents/upload/financial-statement",
            files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
            data={"async_processing": "false"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "上傳的文件為空" in data["detail"]

    def test_upload_oversized_file(self, client):
        """測試上傳超大文件"""
        # 創建超過50MB的文件
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB
        
        response = client.post(
            "/api/v1/documents/upload/financial-statement",
            files={"file": ("large.pdf", io.BytesIO(large_content), "application/pdf")},
            data={"async_processing": "false"}
        )
        
        assert response.status_code == 413
        data = response.json()
        assert "檔案大小超過限制" in data["detail"]

    def test_upload_no_filename(self, client):
        """測試上傳沒有文件名的文件"""
        response = client.post(
            "/api/v1/documents/upload/financial-statement",
            files={"file": ("", io.BytesIO(b"content"), "application/pdf")},
            data={"async_processing": "false"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "請提供有效的檔案名稱" in data["detail"]

    def test_upload_invalid_company_id(self, client, sample_pdf_file):
        """測試上傳無效公司代碼"""
        filename, content, content_type = sample_pdf_file
        
        # 無效的公司代碼格式
        response = client.post(
            "/api/v1/documents/upload/financial-statement",
            files={"file": (filename, io.BytesIO(content), content_type)},
            data={
                "company_id": "invalid_id",  # 應該是4位數字
                "async_processing": "false"
            }
        )
        
        # 注意：此錯誤可能在表單驗證階段就被捕獲
        # 如果FastAPI的表單驗證沒有處理，則會在處理階段處理

    @patch('src.api.endpoints.document_upload.pdf_processor.process_pdf')
    def test_upload_processing_failure(self, mock_process, client, sample_pdf_file):
        """測試PDF處理失敗"""
        # 模擬處理失敗
        mock_process.return_value = {
            'status': 'error',
            'error_message': '無法解析PDF文件',
            'filename': 'test_financial.pdf',
            'financial_data': {},
            'extraction_methods': [],
            'metadata': {}
        }

        filename, content, content_type = sample_pdf_file
        
        response = client.post(
            "/api/v1/documents/upload/financial-statement",
            files={"file": (filename, io.BytesIO(content), content_type)},
            data={"async_processing": "false"}
        )
        
        # 應該返回500錯誤
        assert response.status_code == 500
        data = response.json()
        assert data["error"]["code"] == "PDF_PROCESSING_FAILED"

    def test_get_processing_status_success(self, client):
        """測試查詢處理狀態成功"""
        # 先添加一個處理結果到模擬存儲中
        document_id = "test-doc-id"
        processing_results[document_id] = {
            'status': 'completed',
            'progress': 100,
            'message': '處理完成',
            'results': {
                'financial_data': {'revenue': {'value': 1000000}},
                'validation_results': {'is_valid': True, 'warnings': [], 'errors': []},
                'metadata': {'filename': 'test.pdf'}
            }
        }
        
        response = client.get(f"/api/v1/documents/processing-status/{document_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["document_id"] == document_id
        assert data["status"] == "completed"
        assert data["progress"] == 100
        assert data["results"] is not None
        
        # 清理
        del processing_results[document_id]

    def test_get_processing_status_not_found(self, client):
        """測試查詢不存在的處理狀態"""
        response = client.get("/api/v1/documents/processing-status/nonexistent-id")
        
        assert response.status_code == 404
        data = response.json()
        assert "找不到文件處理記錄" in data["detail"]

    def test_delete_processing_result_success(self, client):
        """測試刪除處理結果成功"""
        # 先添加一個處理結果
        document_id = "test-doc-id-delete"
        processing_results[document_id] = {
            'status': 'completed',
            'progress': 100,
            'message': '處理完成'
        }
        
        response = client.delete(f"/api/v1/documents/processing-result/{document_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["message"] == "處理結果已刪除"
        
        # 確認已被刪除
        assert document_id not in processing_results

    def test_delete_processing_result_not_found(self, client):
        """測試刪除不存在的處理結果"""
        response = client.delete("/api/v1/documents/processing-result/nonexistent-id")
        
        assert response.status_code == 404
        data = response.json()
        assert "找不到文件處理記錄" in data["detail"]

    @patch('src.api.endpoints.document_upload.pdf_processor.process_pdf')
    def test_test_extraction_success(self, mock_process, client, sample_pdf_file):
        """測試文件提取測試成功"""
        # 模擬成功的處理結果
        mock_process.return_value = {
            'status': 'success',
            'filename': 'test.pdf',
            'financial_data': {
                'revenue': {'value': 1000000, 'unit_multiplier': 1000, 'confidence': 0.85},
                'total_assets': {'value': 5000000, 'unit_multiplier': 1000, 'confidence': 0.90}
            },
            'extraction_methods': ['pdfplumber'],
            'metadata': {'total_pages': 5}
        }

        filename, content, content_type = sample_pdf_file
        
        response = client.post(
            "/api/v1/documents/test-extraction",
            files={"file": (filename, io.BytesIO(content), content_type)}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["message"] == "測試提取完成"
        assert data["preview"] is not None
        
        preview = data["preview"]
        assert preview["filename"] == filename
        assert preview["status"] == "success"
        assert preview["financial_metrics_found"] == 2
        assert "sample_data" in preview

    def test_test_extraction_invalid_format(self, client):
        """測試提取測試無效格式"""
        response = client.post(
            "/api/v1/documents/test-extraction",
            files={"file": ("test.txt", io.BytesIO(b"text content"), "text/plain")}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "僅支援PDF格式文件" in data["detail"]

    @patch('src.api.endpoints.document_upload.pdf_processor.process_pdf')
    def test_test_extraction_failure(self, mock_process, client, sample_pdf_file):
        """測試提取測試處理失敗"""
        # 模擬處理異常
        mock_process.side_effect = Exception("PDF解析錯誤")

        filename, content, content_type = sample_pdf_file
        
        response = client.post(
            "/api/v1/documents/test-extraction",
            files={"file": (filename, io.BytesIO(content), content_type)}
        )
        
        assert response.status_code == 200  # API設計為不拋出異常
        data = response.json()
        
        assert data["success"] is False
        assert "測試失敗" in data["message"]
        assert data["preview"] is None


class TestDocumentUploadValidation:
    """文件上傳驗證測試"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_form_validation_company_id_pattern(self, client):
        """測試公司代碼格式驗證"""
        # 這個測試可能需要根據實際的表單驗證實現來調整
        pass  # 表單驗證通常在FastAPI層面處理

    def test_form_validation_report_period_pattern(self, client):
        """測試報告期間格式驗證"""
        # 這個測試可能需要根據實際的表單驗證實現來調整
        pass  # 表單驗證通常在FastAPI層面處理


class TestDocumentUploadIntegration:
    """文件上傳整合測試"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_full_upload_workflow_sync(self, client):
        """測試完整的同步上傳工作流程"""
        # 這個測試需要真實的PDF文件和完整的處理流程
        # 在實際環境中，可能需要準備測試用的PDF文件
        pass

    def test_full_upload_workflow_async(self, client):
        """測試完整的異步上傳工作流程"""
        # 這個測試包括：上傳 -> 狀態查詢 -> 結果獲取 -> 清理
        pass

    @pytest.mark.skip(reason="需要真實的PDF文件進行整合測試")
    def test_real_pdf_processing(self, client):
        """使用真實PDF文件的整合測試"""
        # 這個測試需要真實的財務報表PDF文件
        # 可以在CI/CD環境中準備測試文件
        pass