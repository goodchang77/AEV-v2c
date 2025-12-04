"""
PDF 文件處理服務
PDF Document Processing Service

用於從財務報表PDF文件中提取財務數字和關鍵資訊
"""

import io
import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from pathlib import Path
import fitz  # PyMuPDF
import pdfplumber
import PyPDF2

logger = logging.getLogger(__name__)


class FinancialPDFProcessor:
    """財務報表PDF處理器"""
    
    def __init__(self):
        self.financial_patterns = self._init_financial_patterns()
        self.unit_multipliers = {
            '千元': 1000,
            '千': 1000,
            '仟元': 1000,
            '仟': 1000,
            '萬元': 10000,
            '萬': 10000,
            '百萬元': 1000000,
            '百萬': 1000000,
            '億元': 100000000,
            '億': 100000000,
            '元': 1
        }
    
    def _init_financial_patterns(self) -> Dict[str, List[str]]:
        """初始化財務指標識別模式"""
        return {
            # 資產負債表項目
            'total_assets': [
                r'資產總額|總資產|資產總計|總資產計',
                r'Total\s+Assets?',
                r'TOTAL\s+ASSETS?'
            ],
            'current_assets': [
                r'流動資產|流動資產合計',
                r'Current\s+Assets?',
                r'CURRENT\s+ASSETS?'
            ],
            'total_liabilities': [
                r'負債總額|總負債|負債總計|負債合計',
                r'Total\s+Liabilities?',
                r'TOTAL\s+LIABILITIES?'
            ],
            'current_liabilities': [
                r'流動負債|流動負債合計',
                r'Current\s+Liabilities?',
                r'CURRENT\s+LIABILITIES?'
            ],
            'shareholders_equity': [
                r'股東權益|權益總額|股東權益總計|權益總計',
                r'Shareholders?.?\s*Equity',
                r'SHAREHOLDERS?.?\s*EQUITY',
                r'Total\s+Equity'
            ],
            
            # 損益表項目
            'revenue': [
                r'營業收入|營收|總收入|銷貨收入|收入淨額',
                r'Revenue|Sales|Net\s+Revenue',
                r'REVENUE|SALES|NET\s+REVENUE'
            ],
            'gross_profit': [
                r'營業毛利|毛利|銷貨毛利',
                r'Gross\s+Profit',
                r'GROSS\s+PROFIT'
            ],
            'operating_income': [
                r'營業利益|營業所得|營業收益',
                r'Operating\s+Income|Operating\s+Profit',
                r'OPERATING\s+INCOME|OPERATING\s+PROFIT'
            ],
            'net_income': [
                r'本期淨利|淨利|稅後淨利|歸屬.+淨利',
                r'Net\s+Income|Net\s+Profit|Net\s+Earnings',
                r'NET\s+INCOME|NET\s+PROFIT|NET\s+EARNINGS'
            ],
            'eps': [
                r'基本每股盈餘|每股盈餘|每股淨利|EPS',
                r'Basic\s+EPS|Earnings?\s+Per\s+Share',
                r'BASIC\s+EPS|EARNINGS?\s+PER\s+SHARE'
            ],
            
            # 現金流量表項目
            'operating_cash_flow': [
                r'營業活動.+現金流量|來自營業活動.+現金',
                r'Operating\s+Cash\s+Flow|Cash\s+Flow\s+from\s+Operations?',
                r'OPERATING\s+CASH\s+FLOW|CASH\s+FLOW\s+FROM\s+OPERATIONS?'
            ],
            'investing_cash_flow': [
                r'投資活動.+現金流量|來自投資活動.+現金',
                r'Investing\s+Cash\s+Flow|Cash\s+Flow\s+from\s+Investing',
                r'INVESTING\s+CASH\s+FLOW|CASH\s+FLOW\s+FROM\s+INVESTING'
            ],
            'financing_cash_flow': [
                r'融資活動.+現金流量|來自融資活動.+現金',
                r'Financing\s+Cash\s+Flow|Cash\s+Flow\s+from\s+Financing',
                r'FINANCING\s+CASH\s+FLOW|CASH\s+FLOW\s+FROM\s+FINANCING'
            ]
        }
    
    async def process_pdf(self, pdf_content: bytes, filename: str) -> Dict[str, Any]:
        """
        處理PDF文件，提取財務數字
        
        Args:
            pdf_content: PDF文件內容
            filename: 文件名稱
            
        Returns:
            Dict: 提取的財務數據和元信息
        """
        try:
            # 嘗試不同的PDF解析方法
            extracted_data = {}
            
            # 方法1: 使用 pdfplumber（推薦用於表格）
            try:
                plumber_data = await self._extract_with_pdfplumber(pdf_content)
                if plumber_data:
                    extracted_data['pdfplumber'] = plumber_data
                    logger.info(f"Successfully extracted data using pdfplumber from {filename}")
            except Exception as e:
                logger.warning(f"pdfplumber extraction failed for {filename}: {e}")
            
            # 方法2: 使用 PyMuPDF
            try:
                pymupdf_data = await self._extract_with_pymupdf(pdf_content)
                if pymupdf_data:
                    extracted_data['pymupdf'] = pymupdf_data
                    logger.info(f"Successfully extracted data using PyMuPDF from {filename}")
            except Exception as e:
                logger.warning(f"PyMuPDF extraction failed for {filename}: {e}")
            
            # 方法3: 使用 PyPDF2（備用）
            try:
                pypdf2_data = await self._extract_with_pypdf2(pdf_content)
                if pypdf2_data:
                    extracted_data['pypdf2'] = pypdf2_data
                    logger.info(f"Successfully extracted data using PyPDF2 from {filename}")
            except Exception as e:
                logger.warning(f"PyPDF2 extraction failed for {filename}: {e}")
            
            if not extracted_data:
                raise ValueError("無法從PDF中提取任何財務數據")
            
            # 合併和清理數據
            merged_data = await self._merge_extracted_data(extracted_data)
            
            # 返回結果
            return {
                'filename': filename,
                'status': 'success',
                'financial_data': merged_data,
                'extraction_methods': list(extracted_data.keys()),
                'metadata': {
                    'total_pages': self._get_page_count(pdf_content),
                    'file_size': len(pdf_content)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to process PDF {filename}: {e}")
            return {
                'filename': filename,
                'status': 'error',
                'error_message': str(e),
                'financial_data': {},
                'extraction_methods': [],
                'metadata': {}
            }
    
    async def _extract_with_pdfplumber(self, pdf_content: bytes) -> Dict[str, Any]:
        """使用 pdfplumber 提取數據（特別適合表格）"""
        financial_data = {}
        
        with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
            text_content = ""
            tables = []
            
            for page_num, page in enumerate(pdf.pages, 1):
                # 提取文字
                page_text = page.extract_text() or ""
                text_content += f"\\n--- Page {page_num} ---\\n{page_text}"
                
                # 提取表格
                page_tables = page.extract_tables()
                if page_tables:
                    tables.extend([(page_num, table) for table in page_tables])
        
        # 從表格中提取財務數據
        if tables:
            financial_data.update(await self._extract_from_tables(tables))
        
        # 從文字中提取財務數據
        if text_content:
            financial_data.update(await self._extract_from_text(text_content))
        
        return financial_data
    
    async def _extract_with_pymupdf(self, pdf_content: bytes) -> Dict[str, Any]:
        """使用 PyMuPDF 提取數據"""
        financial_data = {}
        
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        text_content = ""
        
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            page_text = page.get_text()
            text_content += f"\\n--- Page {page_num + 1} ---\\n{page_text}"
        
        doc.close()
        
        # 從文字中提取財務數據
        if text_content:
            financial_data.update(await self._extract_from_text(text_content))
        
        return financial_data
    
    async def _extract_with_pypdf2(self, pdf_content: bytes) -> Dict[str, Any]:
        """使用 PyPDF2 提取數據（備用方法）"""
        financial_data = {}
        
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
        text_content = ""
        
        for page_num, page in enumerate(pdf_reader.pages, 1):
            page_text = page.extract_text()
            text_content += f"\\n--- Page {page_num} ---\\n{page_text}"
        
        # 從文字中提取財務數據
        if text_content:
            financial_data.update(await self._extract_from_text(text_content))
        
        return financial_data
    
    async def _extract_from_tables(self, tables: List[Tuple[int, List[List]]]) -> Dict[str, Any]:
        """從表格中提取財務數據 (改進版：結構化解析)"""
        financial_data = {}
        
        for page_num, table in tables:
            if not table:
                continue
                
            try:
                # 遍歷表格的每一行
                for row in table:
                    if not row:
                        continue
                        
                    # 將行中的 None 轉換為空字串
                    clean_row = [str(cell).strip() if cell is not None else "" for cell in row]
                    row_text = " ".join(clean_row)
                    
                    # 檢查這一行是否包含財務指標關鍵字
                    for metric_name, patterns in self.financial_patterns.items():
                        for pattern in patterns:
                            # 使用較寬鬆的匹配（忽略大小寫）
                            if re.search(pattern, row_text, re.IGNORECASE):
                                # 如果找到關鍵字，嘗試在該行中尋找數值
                                value = self._find_value_in_row_list(clean_row, pattern)
                                
                                if value is not None:
                                    # 如果已經有值，且新值看起來更合理（例如非零），則更新
                                    # 這裡簡單策略：如果還沒找到，或者新值更大（假設是總計），則更新
                                    if metric_name not in financial_data or (value > 0 and abs(value) > abs(financial_data[metric_name]['value'])):
                                        financial_data[metric_name] = {
                                            'value': value,
                                            'unit_multiplier': 1,  # 表格內通常單位在表頭，這裡暫設為1，後續可優化
                                            'page': page_num,
                                            'original_matches': 1
                                        }
            except Exception as e:
                logger.warning(f"Error processing table on page {page_num}: {e}")
                continue
        
        return financial_data

    def _find_value_in_row_list(self, row: List[str], pattern: str) -> Optional[Decimal]:
        """在表格行列表中尋找數值"""
        # 1. 找出關鍵字所在的欄位索引
        key_idx = -1
        for i, cell in enumerate(row):
            if re.search(pattern, cell, re.IGNORECASE):
                key_idx = i
                break
        
        if key_idx == -1:
            return None
            
        # 2. 從關鍵字往右找數字
        for i in range(key_idx + 1, len(row)):
            cell_text = row[i]
            # 移除常見的非數字字符 (逗號, 括號等)
            clean_text = cell_text.replace(',', '').replace(' ', '')
            if '(' in clean_text and ')' in clean_text:
                clean_text = clean_text.replace('(', '-').replace(')', '')
            
            # 嘗試解析
            try:
                # 匹配數字格式
                if re.match(r'^-?\d+(?:\.\d+)?$', clean_text):
                    return Decimal(clean_text)
            except:
                continue
                
        return None
    
    async def _extract_from_text(self, text: str, source_prefix: str = "") -> Dict[str, Any]:
        """從純文字中提取財務數據"""
        financial_data = {}
        
        # 清理文字
        cleaned_text = self._clean_text(text)
        
        # 檢測金額單位
        unit_multiplier = self._detect_unit_multiplier(cleaned_text)
        
        # 搜尋每個財務指標
        for metric_name, patterns in self.financial_patterns.items():
            values = []
            
            for pattern in patterns:
                matches = await self._find_financial_values(cleaned_text, pattern, unit_multiplier)
                values.extend(matches)
            
            if values:
                # 選擇最可能的值（通常是最大的正值或最近的值）
                best_value = self._select_best_value(values, metric_name)
                if best_value is not None:
                    key = f"{source_prefix}_{metric_name}" if source_prefix else metric_name
                    financial_data[key] = {
                        'value': best_value,
                        'unit_multiplier': unit_multiplier,
                        'original_matches': len(values)
                    }
        
        return financial_data
    
    async def _find_financial_values(self, text: str, pattern: str, unit_multiplier: int = 1) -> List[Decimal]:
        """在文字中尋找符合模式的財務數值"""
        values = []
        
        # 改進的搜尋模式，查找項目名稱後的數字
        # 匹配更複雜的數字格式，包括千分位分隔符和小數
        search_pattern = f"({pattern}).*?(\\d[\\d,]*(?:\\.\\d+)?)"
        
        matches = re.finditer(search_pattern, text, re.IGNORECASE | re.MULTILINE)
        
        for match in matches:
            try:
                # 提取數字部分並清理格式
                number_str = match.group(2)
                
                # 移除千分位分隔符
                clean_number = number_str.replace(',', '')
                
                # 檢查是否為有效數字格式
                if not re.match(r'^\d+(?:\.\d+)?$', clean_number):
                    logger.debug(f"Skipping invalid number format: {number_str}")
                    continue
                
                # 處理負數（可能有括號表示）
                is_negative = False
                full_match = match.group(0)
                if '(' in full_match and ')' in full_match:
                    # 檢查數字是否在括號內
                    paren_pattern = f"\\({re.escape(number_str)}\\)"
                    if re.search(paren_pattern, full_match):
                        is_negative = True
                
                # 轉換為 Decimal
                try:
                    value = Decimal(clean_number)
                    if is_negative:
                        value = -value
                    
                    # 過濾明顯錯誤的值
                    if value == 0:
                        continue
                    
                    # 套用單位乘數
                    final_value = value * unit_multiplier
                    values.append(final_value)
                    
                    logger.debug(f"Successfully parsed: {number_str} -> {final_value}")
                    
                except (ValueError, TypeError) as e:
                    logger.debug(f"Failed to convert to Decimal: {clean_number}, error: {e}")
                    continue
                
            except (IndexError, AttributeError) as e:
                logger.debug(f"Failed to process match: {match}, error: {e}")
                continue
        
        return values
    
    def _clean_text(self, text: str) -> str:
        """清理文字內容"""
        if not text:
            return ""
        
        # 移除多餘的空白和換行
        cleaned = re.sub(r'\\s+', ' ', text.strip())
        
        # 統一數字格式（移除不必要的空格）
        cleaned = re.sub(r'(\\d)\\s+(\\d)', r'\\1\\2', cleaned)
        
        # 統一負數表示（括號轉換為負號）
        cleaned = re.sub(r'\\((\\d[\\d,]*(?:\\.\\d+)?)\\)', r'-\\1', cleaned)
        
        return cleaned
    
    def _detect_unit_multiplier(self, text: str) -> int:
        """檢測文字中的金額單位"""
        # 按優先順序檢查單位
        for unit, multiplier in sorted(self.unit_multipliers.items(), key=lambda x: len(x[0]), reverse=True):
            if unit in text:
                logger.debug(f"Detected unit: {unit} (multiplier: {multiplier})")
                return multiplier
        
        # 預設單位為元
        return 1
    
    def _table_to_text(self, table: List[List]) -> str:
        """將表格轉換為可搜尋的文字格式"""
        text_lines = []
        
        for row in table:
            if row:  # 確保行不為空
                # 過濾空值並連接
                row_text = " | ".join([str(cell) for cell in row if cell is not None and str(cell).strip()])
                if row_text.strip():
                    text_lines.append(row_text)
        
        return "\\n".join(text_lines)
    
    def _select_best_value(self, values: List[Decimal], metric_name: str) -> Optional[Decimal]:
        """從多個候選值中選擇最佳值"""
        if not values:
            return None
        
        if len(values) == 1:
            return values[0]
        
        # 移除明顯錯誤的值（如過小的值）
        filtered_values = [v for v in values if abs(v) >= 0.01]  # 至少0.01元
        
        if not filtered_values:
            return values[0] if values else None
        
        # 對於資產、負債、收入等，通常選擇最大的正值
        if metric_name in ['total_assets', 'current_assets', 'total_liabilities', 'current_liabilities', 'shareholders_equity', 'revenue', 'gross_profit']:
            positive_values = [v for v in filtered_values if v > 0]
            if positive_values:
                return max(positive_values)
        
        # 對於淨利、現金流等，可能為負值，選擇絕對值最大的
        return max(filtered_values, key=abs)
    
    async def _merge_extracted_data(self, extracted_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """合併從不同方法提取的數據"""
        merged = {}
        
        # 收集所有提取到的指標
        all_metrics = set()
        for method_data in extracted_data.values():
            all_metrics.update(method_data.keys())
        
        # 對每個指標選擇最佳值
        for metric in all_metrics:
            candidates = []
            
            for method, data in extracted_data.items():
                if metric in data:
                    candidates.append({
                        'method': method,
                        'value': data[metric]['value'],
                        'unit_multiplier': data[metric]['unit_multiplier'],
                        'confidence': self._calculate_confidence(method, data[metric])
                    })
            
            if candidates:
                # 選擇置信度最高的值
                best_candidate = max(candidates, key=lambda x: x['confidence'])
                merged[metric] = {
                    'value': float(best_candidate['value']),
                    'unit_multiplier': best_candidate['unit_multiplier'],
                    'extraction_method': best_candidate['method'],
                    'confidence': best_candidate['confidence'],
                    'candidates_count': len(candidates)
                }
        
        return merged
    
    def _calculate_confidence(self, method: str, data: Dict[str, Any]) -> float:
        """計算提取數據的置信度"""
        base_confidence = {
            'pdfplumber': 0.8,  # pdfplumber 最適合表格
            'pymupdf': 0.6,     # PyMuPDF 文字提取能力好
            'pypdf2': 0.4       # PyPDF2 作為備用
        }.get(method, 0.5)
        
        # 根據匹配數量調整置信度
        matches_count = data.get('original_matches', 1)
        if matches_count > 1:
            base_confidence *= 1.1  # 多次匹配增加置信度
        
        # 根據數值合理性調整
        value = abs(float(data['value']))
        if value > 0:
            if value < 1000:  # 可能過小
                base_confidence *= 0.8
            elif value > 1000000000000:  # 可能過大
                base_confidence *= 0.7
        else:
            base_confidence *= 0.5  # 零值或負值降低置信度
        
        return min(base_confidence, 1.0)
    
    def _get_page_count(self, pdf_content: bytes) -> int:
        """獲取PDF頁數"""
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
            return len(pdf_reader.pages)
        except:
            return 0
    
    async def validate_financial_data(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """驗證提取的財務數據合理性"""
        validation_results = {
            'is_valid': True,
            'warnings': [],
            'errors': [],
            'suggestions': []
        }
        
        try:
            # 基本合理性檢查
            assets = financial_data.get('total_assets', {}).get('value', 0)
            liabilities = financial_data.get('total_liabilities', {}).get('value', 0)
            equity = financial_data.get('shareholders_equity', {}).get('value', 0)
            
            # 資產負債表平衡檢查
            if assets and liabilities and equity:
                balance_diff = abs(assets - (liabilities + equity))
                balance_ratio = balance_diff / assets if assets > 0 else 0
                
                if balance_ratio > 0.05:  # 5% 的容差
                    validation_results['warnings'].append(
                        f"資產負債表可能不平衡: 資產({assets:,.0f}) ≠ 負債({liabilities:,.0f}) + 權益({equity:,.0f})"
                    )
            
            # 流動性比率檢查
            current_assets = financial_data.get('current_assets', {}).get('value', 0)
            current_liabilities = financial_data.get('current_liabilities', {}).get('value', 0)
            
            if current_assets and current_liabilities and current_liabilities > 0:
                current_ratio = current_assets / current_liabilities
                if current_ratio < 0.5:
                    validation_results['warnings'].append(
                        f"流動比率過低({current_ratio:.2f})，可能面臨流動性風險"
                    )
                elif current_ratio > 10:
                    validation_results['warnings'].append(
                        f"流動比率過高({current_ratio:.2f})，可能資金運用效率不佳"
                    )
            
            # 獲利能力檢查
            revenue = financial_data.get('revenue', {}).get('value', 0)
            net_income = financial_data.get('net_income', {}).get('value', 0)
            
            if revenue and net_income and revenue > 0:
                net_margin = net_income / revenue
                if abs(net_margin) > 1:
                    validation_results['warnings'].append(
                        f"淨利率異常({net_margin:.2%})，請檢查數據準確性"
                    )
            
        except Exception as e:
            validation_results['errors'].append(f"驗證過程發生錯誤: {e}")
            validation_results['is_valid'] = False
        
        return validation_results