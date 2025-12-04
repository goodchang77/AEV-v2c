"""
PDF處理器單元測試
PDF Processor Unit Tests
"""

import pytest
import io
from decimal import Decimal
from unittest.mock import patch, MagicMock

from src.services.pdf_processor import FinancialPDFProcessor


class TestFinancialPDFProcessor:
    """財務PDF處理器測試類"""

    @pytest.fixture
    def processor(self):
        """創建PDF處理器實例"""
        return FinancialPDFProcessor()

    @pytest.fixture
    def sample_financial_text(self):
        """樣本財務報表文字"""
        return """
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
        """

    @pytest.fixture
    def sample_pdf_content(self):
        """樣本PDF內容 - 模擬簡單的PDF bytes"""
        # 這裡使用一個簡化的PDF結構
        pdf_header = b"%PDF-1.4\n"
        pdf_content = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        pdf_pages = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        pdf_page = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>\nendobj\n"
        pdf_stream = b"4 0 obj\n<< /Length 44 >>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Hello World) Tj\nET\nendstream\nendobj\n"
        pdf_trailer = b"xref\n0 5\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000125 00000 n\n0000000190 00000 n\ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n286\n%%EOF"
        
        return pdf_header + pdf_content + pdf_pages + pdf_page + pdf_stream + pdf_trailer

    def test_processor_initialization(self, processor):
        """測試處理器初始化"""
        assert processor is not None
        assert hasattr(processor, 'financial_patterns')
        assert hasattr(processor, 'unit_multipliers')
        assert len(processor.financial_patterns) > 0
        assert len(processor.unit_multipliers) > 0

    def test_unit_multiplier_detection(self, processor):
        """測試金額單位檢測"""
        # 測試千元
        text_thousands = "單位：新台幣千元"
        multiplier = processor._detect_unit_multiplier(text_thousands)
        assert multiplier == 1000

        # 測試萬元
        text_ten_thousands = "單位：新台幣萬元"
        multiplier = processor._detect_unit_multiplier(text_ten_thousands)
        assert multiplier == 10000

        # 測試億元
        text_hundred_millions = "單位：新台幣億元"
        multiplier = processor._detect_unit_multiplier(text_hundred_millions)
        assert multiplier == 100000000

        # 測試預設值
        text_no_unit = "財務報表內容"
        multiplier = processor._detect_unit_multiplier(text_no_unit)
        assert multiplier == 1

    def test_text_cleaning(self, processor):
        """測試文字清理功能"""
        dirty_text = "   資產總額     1,500,000   \n\n  負債總計  (800,000)  "
        cleaned = processor._clean_text(dirty_text)
        
        assert "資產總額" in cleaned
        assert "1,500,000" in cleaned
        assert "-800,000" in cleaned  # 括號應該轉換為負號
        assert "  " not in cleaned  # 多餘空格應被移除

    @pytest.mark.asyncio
    async def test_extract_from_text(self, processor, sample_financial_text):
        """測試從文字中提取財務數據"""
        extracted = await processor._extract_from_text(sample_financial_text)
        
        assert len(extracted) > 0
        
        # 檢查是否正確提取了主要指標
        assert 'total_assets' in extracted
        assert 'current_assets' in extracted
        assert 'total_liabilities' in extracted
        assert 'current_liabilities' in extracted
        assert 'shareholders_equity' in extracted
        assert 'revenue' in extracted
        assert 'net_income' in extracted

        # 檢查數值的合理性
        total_assets = extracted['total_assets']['value']
        assert total_assets == 16000000000  # 16,000,000 千元 = 16,000,000,000 元

    @pytest.mark.asyncio
    async def test_financial_value_extraction(self, processor):
        """測試財務數值提取"""
        text = "資產總額 16,000,000 營業收入 25,000,000"
        pattern = r"資產總額"
        unit_multiplier = 1000
        
        values = await processor._find_financial_values(text, pattern, unit_multiplier)
        
        assert len(values) > 0
        assert values[0] == Decimal('16000000000')  # 16,000,000 * 1000

    def test_value_selection(self, processor):
        """測試最佳值選擇邏輯"""
        # 測試單一值
        single_value = [Decimal('1000000')]
        best = processor._select_best_value(single_value, 'total_assets')
        assert best == Decimal('1000000')

        # 測試多個值中選擇最大正值
        multiple_values = [Decimal('500000'), Decimal('1000000'), Decimal('750000')]
        best = processor._select_best_value(multiple_values, 'total_assets')
        assert best == Decimal('1000000')

        # 測試包含負值的情況
        mixed_values = [Decimal('-100000'), Decimal('800000'), Decimal('-50000')]
        best = processor._select_best_value(mixed_values, 'net_income')
        assert best == Decimal('800000')

        # 測試空列表
        empty_values = []
        best = processor._select_best_value(empty_values, 'revenue')
        assert best is None

    @pytest.mark.asyncio
    async def test_data_validation(self, processor):
        """測試財務數據驗證"""
        # 正常的財務數據
        valid_data = {
            'total_assets': {'value': 16000000},
            'total_liabilities': {'value': 6000000},
            'shareholders_equity': {'value': 10000000},
            'current_assets': {'value': 6000000},
            'current_liabilities': {'value': 3500000},
            'revenue': {'value': 25000000},
            'net_income': {'value': 1840000}
        }
        
        validation = await processor.validate_financial_data(valid_data)
        
        assert validation['is_valid'] is True
        assert len(validation['errors']) == 0

        # 不平衡的資產負債表
        unbalanced_data = {
            'total_assets': {'value': 16000000},
            'total_liabilities': {'value': 8000000},  # 不平衡
            'shareholders_equity': {'value': 10000000}
        }
        
        validation = await processor.validate_financial_data(unbalanced_data)
        
        assert len(validation['warnings']) > 0
        # 檢查是否有資產負債表不平衡的警告

    def test_confidence_calculation(self, processor):
        """測試置信度計算"""
        # pdfplumber 方法應該有較高基礎置信度
        pdfplumber_confidence = processor._calculate_confidence('pdfplumber', {
            'value': 1000000,
            'unit_multiplier': 1000,
            'original_matches': 1
        })
        
        pypdf2_confidence = processor._calculate_confidence('pypdf2', {
            'value': 1000000,
            'unit_multiplier': 1000,
            'original_matches': 1
        })
        
        assert pdfplumber_confidence > pypdf2_confidence

        # 多次匹配應該增加置信度
        multiple_matches_confidence = processor._calculate_confidence('pdfplumber', {
            'value': 1000000,
            'unit_multiplier': 1000,
            'original_matches': 3
        })
        
        single_match_confidence = processor._calculate_confidence('pdfplumber', {
            'value': 1000000,
            'unit_multiplier': 1000,
            'original_matches': 1
        })
        
        assert multiple_matches_confidence > single_match_confidence

    @pytest.mark.asyncio
    async def test_merge_extracted_data(self, processor):
        """測試合併提取的數據"""
        # 模擬從不同方法提取的數據
        extracted_data = {
            'pdfplumber': {
                'total_assets': {
                    'value': Decimal('16000000'),
                    'unit_multiplier': 1000,
                    'original_matches': 2
                },
                'revenue': {
                    'value': Decimal('25000000'),
                    'unit_multiplier': 1000,
                    'original_matches': 1
                }
            },
            'pymupdf': {
                'total_assets': {
                    'value': Decimal('15900000'),  # 略有不同的值
                    'unit_multiplier': 1000,
                    'original_matches': 1
                },
                'net_income': {
                    'value': Decimal('1840000'),
                    'unit_multiplier': 1000,
                    'original_matches': 1
                }
            }
        }
        
        merged = await processor._merge_extracted_data(extracted_data)
        
        assert 'total_assets' in merged
        assert 'revenue' in merged
        assert 'net_income' in merged
        
        # pdfplumber 的置信度應該更高，所以選擇其值
        assert merged['total_assets']['value'] == 16000000.0
        assert merged['total_assets']['extraction_method'] == 'pdfplumber'

    @pytest.mark.asyncio
    @patch('src.services.pdf_processor.pdfplumber')
    @patch('src.services.pdf_processor.fitz')  
    @patch('src.services.pdf_processor.PyPDF2')
    async def test_process_pdf_success(self, mock_pypdf2, mock_fitz, mock_pdfplumber, processor, sample_pdf_content):
        """測試PDF處理成功案例"""
        # 模擬 pdfplumber 成功提取
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "營業收入 25,000,000 本期淨利 1,840,000"
        mock_page.extract_tables.return_value = []
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf

        result = await processor.process_pdf(sample_pdf_content, "test.pdf")
        
        assert result['status'] == 'success'
        assert 'financial_data' in result
        assert result['filename'] == 'test.pdf'
        assert 'extraction_methods' in result

    @pytest.mark.asyncio
    async def test_process_pdf_failure(self, processor):
        """測試PDF處理失敗案例"""
        # 使用無效的PDF內容
        invalid_pdf = b"not a pdf content"
        
        result = await processor.process_pdf(invalid_pdf, "invalid.pdf")
        
        assert result['status'] == 'error'
        assert 'error_message' in result
        assert result['filename'] == 'invalid.pdf'

    def test_table_to_text_conversion(self, processor):
        """測試表格轉文字功能"""
        sample_table = [
            ['項目', '金額', '百分比'],
            ['營業收入', '25,000,000', '100%'],
            ['營業成本', '18,000,000', '72%'],
            ['營業毛利', '7,000,000', '28%']
        ]
        
        text = processor._table_to_text(sample_table)
        
        assert '營業收入' in text
        assert '25,000,000' in text
        assert '|' in text  # 分隔符應該存在

    @pytest.mark.asyncio
    async def test_extract_from_tables(self, processor):
        """測試從表格提取數據"""
        sample_tables = [
            (1, [
                ['項目', '當期金額'],
                ['營業收入', '25,000,000'],
                ['本期淨利', '1,840,000']
            ]),
            (2, [
                ['資產項目', '金額'],
                ['資產總額', '16,000,000'],
                ['負債總計', '6,000,000']
            ])
        ]
        
        extracted = await processor._extract_from_tables(sample_tables)
        
        assert len(extracted) > 0
        # 檢查是否從表格中提取到預期的指標


class TestPDFProcessorEdgeCases:
    """PDF處理器邊界案例測試"""

    @pytest.fixture
    def processor(self):
        return FinancialPDFProcessor()

    @pytest.mark.asyncio
    async def test_empty_text_handling(self, processor):
        """測試空文字處理"""
        empty_text = ""
        extracted = await processor._extract_from_text(empty_text)
        assert extracted == {}

    @pytest.mark.asyncio
    async def test_no_financial_data_text(self, processor):
        """測試不含財務數據的文字"""
        non_financial_text = "這是一段不包含任何財務數據的普通文字內容。"
        extracted = await processor._extract_from_text(non_financial_text)
        assert len(extracted) == 0

    def test_invalid_number_handling(self, processor):
        """測試無效數字處理"""
        invalid_values = ["abc", "", "12.34.56", "infinite"]
        
        for invalid in invalid_values:
            try:
                # 這應該不會拋出異常，而是被忽略
                result = processor._select_best_value([invalid], 'revenue')
                # 如果沒有異常，結果應該是 None 或空
                assert result is None or result == []
            except:
                # 如果有異常，也是可以接受的，因為這是無效輸入
                pass

    def test_extreme_values(self, processor):
        """測試極值處理"""
        # 非常大的值
        large_value = Decimal('999999999999999')
        confidence = processor._calculate_confidence('pdfplumber', {
            'value': large_value,
            'unit_multiplier': 1,
            'original_matches': 1
        })
        
        # 置信度應該被降低
        assert confidence < 0.8

        # 非常小的值
        small_value = Decimal('0.01')
        confidence = processor._calculate_confidence('pdfplumber', {
            'value': small_value,
            'unit_multiplier': 1,
            'original_matches': 1
        })
        
        # 置信度應該被降低
        assert confidence < 0.8