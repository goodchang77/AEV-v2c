#!/usr/bin/env python3
"""
PDF處理功能測試腳本
Test PDF Processing Functionality
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加項目根目錄到Python路徑
sys.path.insert(0, str(Path(__file__).parent))

from src.services.pdf_processor import FinancialPDFProcessor

async def test_pdf_processing():
    """測試PDF處理功能"""
    print("🔍 開始PDF處理功能測試...")
    
    processor = FinancialPDFProcessor()
    
    # 測試PDF文件路徑
    # 測試PDF文件路徑
    # 使用相對路徑以兼容不同環境
    base_dir = Path(__file__).parent.parent
    pdf_path = base_dir / "testdata" / "NVDSA Q2FY25-CFO-Commentary.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"❌ 測試PDF文件不存在: {pdf_path}")
        return False
    
    try:
        # 讀取PDF文件
        with open(pdf_path, 'rb') as f:
            pdf_content = f.read()
        
        print(f"📄 載入PDF文件: {os.path.basename(pdf_path)} ({len(pdf_content):,} bytes)")
        
        # 處理PDF
        result = await processor.process_pdf(pdf_content, os.path.basename(pdf_path))
        
        print(f"📊 處理結果:")
        print(f"   - 狀態: {result['status']}")
        print(f"   - 提取方法: {result['extraction_methods']}")
        print(f"   - 財務數據項目數: {len(result['financial_data'])}")
        
        if result['status'] == 'success':
            print(f"📈 提取的財務數據:")
            for key, data in list(result['financial_data'].items())[:10]:  # 只顯示前10項
                print(f"   - {key}: {data['value']:,.2f} (方法: {data['extraction_method']})")
            
            if len(result['financial_data']) > 10:
                print(f"   ... 還有 {len(result['financial_data']) - 10} 項數據")
            
            # 驗證財務數據
            validation = await processor.validate_financial_data(result['financial_data'])
            print(f"✅ 數據驗證結果:")
            print(f"   - 有效: {validation['is_valid']}")
            print(f"   - 警告: {len(validation['warnings'])}")
            print(f"   - 錯誤: {len(validation['errors'])}")
            
            for warning in validation['warnings']:
                print(f"   ⚠️  {warning}")
            
            for error in validation['errors']:
                print(f"   ❌ {error}")
        
        else:
            print(f"❌ 處理失敗: {result.get('error_message', '未知錯誤')}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 測試過程中發生錯誤: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_pdf_processing())
    if success:
        print("\n✅ PDF處理功能測試完成")
    else:
        print("\n❌ PDF處理功能測試失敗")
        sys.exit(1)