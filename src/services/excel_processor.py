"""
Excel 文件處理服務
Excel Document Processing Service

用於從財務報表 Excel 文件中提取財務數字和關鍵資訊
"""

import io
import re
import logging
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class FinancialExcelProcessor:
    """財務報表 Excel 處理器"""
    
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
        """初始化財務指標識別模式 (與 PDF 處理器共用類似的模式)"""
        return {
            # 資產負債表項目
            'total_assets': [
                r'資產總額', r'總資產', r'資產總計', r'總資產計',
                r'Total\s+Assets?', r'TOTAL\s+ASSETS?'
            ],
            'current_assets': [
                r'流動資產', r'流動資產合計',
                r'Current\s+Assets?', r'CURRENT\s+ASSETS?'
            ],
            'total_liabilities': [
                r'負債總額', r'總負債', r'負債總計', r'負債合計',
                r'Total\s+Liabilities?', r'TOTAL\s+LIABILITIES?'
            ],
            'current_liabilities': [
                r'流動負債', r'流動負債合計',
                r'Current\s+Liabilities?', r'CURRENT\s+LIABILITIES?'
            ],
            'shareholders_equity': [
                r'股東權益', r'權益總額', r'股東權益總計', r'權益總計',
                r'Shareholders?.?\s*Equity', r'Total\s+Equity'
            ],
            
            # 損益表項目
            'revenue': [
                r'營業收入', r'營收', r'總收入', r'銷貨收入', r'收入淨額',
                r'Revenue', r'Sales', r'Net\s+Revenue'
            ],
            'gross_profit': [
                r'營業毛利', r'毛利', r'銷貨毛利',
                r'Gross\s+Profit'
            ],
            'operating_income': [
                r'營業利益', r'營業所得', r'營業收益',
                r'Operating\s+Income', r'Operating\s+Profit'
            ],
            'net_income': [
                r'本期淨利', r'淨利', r'稅後淨利', r'歸屬.+淨利',
                r'Net\s+Income', r'Net\s+Profit'
            ],
            'eps': [
                r'基本每股盈餘', r'每股盈餘', r'每股淨利', r'EPS',
                r'Basic\s+EPS', r'Earnings?\s+Per\s+Share'
            ],
            
            # 現金流量表項目
            'operating_cash_flow': [
                r'營業活動.+現金流量', r'來自營業活動.+現金',
                r'Operating\s+Cash\s+Flow'
            ],
            'investing_cash_flow': [
                r'投資活動.+現金流量', r'來自投資活動.+現金',
                r'Investing\s+Cash\s+Flow'
            ],
            'financing_cash_flow': [
                r'融資活動.+現金流量', r'來自融資活動.+現金',
                r'Financing\s+Cash\s+Flow'
            ]
        }
    
    async def process_excel(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        處理 Excel 文件，提取財務數字
        
        Args:
            file_content: Excel 文件內容
            filename: 文件名稱
            
        Returns:
            Dict: 提取的財務數據和元信息
        """
        try:
            # 讀取 Excel 文件
            excel_file = io.BytesIO(file_content)
            
            # 嘗試讀取所有工作表
            try:
                # 使用 pandas 讀取，header=None 因為我們不知道標題在哪一行
                dfs = pd.read_excel(excel_file, sheet_name=None, header=None)
            except Exception as e:
                logger.error(f"Pandas read_excel failed: {e}")
                raise ValueError(f"無法讀取 Excel 文件: {e}")
            
            extracted_data = {}
            total_rows = 0
            sheet_names = list(dfs.keys())
            
            # 遍歷每個工作表
            for sheet_name, df in dfs.items():
                # 清理 DataFrame: 移除全空的行和列
                df = df.dropna(how='all').dropna(axis=1, how='all')
                
                # 將所有內容轉為字串，方便處理
                df = df.astype(str)
                
                total_rows += len(df)
                
                # 從工作表中提取數據
                sheet_data = await self._extract_from_dataframe(df, sheet_name)
                
                # 合併數據 (如果有重複，保留置信度較高的或後面的)
                for key, value in sheet_data.items():
                    if key not in extracted_data:
                        extracted_data[key] = value
                    else:
                        # 如果已經存在，比較數值大小，通常保留較大的（假設是總計）
                        # 或者可以根據邏輯保留更精確的
                        pass
            
            if not extracted_data:
                logger.warning(f"No financial data extracted from {filename}")
            
            return {
                'filename': filename,
                'status': 'success',
                'financial_data': extracted_data,
                'extraction_methods': ['pandas_excel'],
                'metadata': {
                    'sheet_names': sheet_names,
                    'total_rows': total_rows,
                    'file_size': len(file_content)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to process Excel {filename}: {e}")
            return {
                'filename': filename,
                'status': 'error',
                'error_message': str(e),
                'financial_data': {},
                'extraction_methods': [],
                'metadata': {}
            }
    
    async def _extract_from_dataframe(self, df: pd.DataFrame, sheet_name: str) -> Dict[str, Any]:
        """從 DataFrame 中提取財務數據"""
        financial_data = {}
        
        # 檢測單位
        unit_multiplier = self._detect_unit_multiplier_in_df(df)
        
        # 遍歷每一行
        for idx, row in df.iterrows():
            row_text = " ".join(row.values)
            
            # 檢查是否包含財務指標關鍵字
            for metric_name, patterns in self.financial_patterns.items():
                # 如果已經找到該指標且置信度很高，可能不需要再找（這裡簡化處理，繼續找並覆蓋）
                
                for pattern in patterns:
                    if re.search(pattern, row_text, re.IGNORECASE):
                        # 找到關鍵字，嘗試在同一行中尋找數字
                        value = self._find_value_in_row(row, pattern)
                        
                        if value is not None:
                            # 儲存結果
                            final_value = value * unit_multiplier
                            financial_data[metric_name] = {
                                'value': final_value,
                                'unit_multiplier': unit_multiplier,
                                'source_sheet': sheet_name,
                                'row_index': idx,
                                'match_pattern': pattern
                            }
                            break # 找到一個模式就跳出該指標的循環
        
        return financial_data
    
    def _find_value_in_row(self, row: pd.Series, pattern: str) -> Optional[Decimal]:
        """在 DataFrame 的一行中尋找對應的數值"""
        # 找出包含關鍵字的欄位索引
        key_col_idx = -1
        for i, cell in enumerate(row):
            if re.search(pattern, str(cell), re.IGNORECASE):
                key_col_idx = i
                break
        
        if key_col_idx == -1:
            return None
        
        # 從關鍵字欄位往右找數字
        # 通常數值會在右邊的欄位
        for i in range(key_col_idx + 1, len(row)):
            cell_value = str(row.iloc[i]).strip()
            
            # 嘗試解析數字
            value = self._parse_number(cell_value)
            if value is not None:
                return value
        
        # 如果右邊沒找到，有些格式可能是 關鍵字 數值 在同一格 (雖然在 Excel 較少見，但也可能)
        # 或者在左邊 (極少見)
        
        return None

    def _parse_number(self, text: str) -> Optional[Decimal]:
        """解析數字字串"""
        if not text or text.lower() == 'nan' or text.lower() == 'none':
            return None
            
        # 移除常見的非數字字符
        clean_text = text.replace(',', '').replace('$', '').replace(' ', '')
        
        # 處理括號負數 (123) -> -123
        if clean_text.startswith('(') and clean_text.endswith(')'):
            clean_text = '-' + clean_text[1:-1]
            
        try:
            # 檢查是否為純數字
            if re.match(r'^-?\d+(?:\.\d+)?$', clean_text):
                return Decimal(clean_text)
        except:
            pass
            
        return None

    def _detect_unit_multiplier_in_df(self, df: pd.DataFrame) -> int:
        """在 DataFrame 中檢測單位"""
        # 檢查前幾行（通常標題或單位在上方）
        header_rows = df.head(10)
        text_content = header_rows.to_string()
        
        for unit, multiplier in sorted(self.unit_multipliers.items(), key=lambda x: len(x[0]), reverse=True):
            if unit in text_content:
                logger.debug(f"Detected unit in Excel: {unit} (multiplier: {multiplier})")
                return multiplier
        
        return 1
    
    async def validate_financial_data(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """驗證提取的財務數據 (複用 PDF 處理器的邏輯或實作類似邏輯)"""
        # 這裡簡單實作一個驗證，實際專案可以抽取共用邏輯
        validation_results = {
            'is_valid': True,
            'warnings': [],
            'errors': []
        }
        
        try:
            assets = financial_data.get('total_assets', {}).get('value', 0)
            liabilities = financial_data.get('total_liabilities', {}).get('value', 0)
            equity = financial_data.get('shareholders_equity', {}).get('value', 0)
            
            if assets and liabilities and equity:
                if abs(assets - (liabilities + equity)) > assets * Decimal('0.05'):
                    validation_results['warnings'].append("資產負債表不平衡")
                    
        except Exception as e:
            validation_results['errors'].append(str(e))
            
        return validation_results
