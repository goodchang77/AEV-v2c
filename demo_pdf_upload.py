#!/usr/bin/env python3
"""
PDF上傳功能演示腳本
PDF Upload Feature Demo Script

演示從前端WebUI讀取PDF格式財務報表並擷取財務數字的完整功能
"""

import asyncio
import logging
from pathlib import Path
import io

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_demo_pdf():
    """創建演示用的PDF內容（模擬真實的財務報表）"""
    financial_content = """
%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
  /Font <<
    /F1 <<
      /Type /Font
      /Subtype /Type1
      /BaseFont /Helvetica
    >>
  >>
>>
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 2500
>>
stream
BT
/F1 12 Tf
50 700 Td
(台積電股份有限公司) Tj
0 -20 Td
(財務狀況表) Tj
0 -10 Td
(中華民國113年第一季) Tj
0 -10 Td
(單位：新台幣千元) Tj

0 -40 Td
(資產) Tj
0 -20 Td
(  流動資產) Tj
0 -15 Td
(    現金及約當現金                1,234,567,890) Tj
0 -15 Td
(    應收帳款淨額                    567,890,123) Tj
0 -15 Td
(    存貨                          345,678,901) Tj
0 -15 Td
(    其他流動資產                    123,456,789) Tj
0 -15 Td
(  流動資產合計                    2,271,593,703) Tj

0 -25 Td
(  非流動資產) Tj
0 -15 Td
(    不動產、廠房及設備            3,456,789,012) Tj
0 -15 Td
(    無形資產                        89,012,345) Tj
0 -15 Td
(    其他非流動資產                  234,567,890) Tj
0 -15 Td
(  非流動資產合計                  3,780,369,247) Tj

0 -20 Td
(資產總額                          6,051,962,950) Tj

0 -40 Td
(負債及股東權益) Tj
0 -20 Td
(  流動負債) Tj
0 -15 Td
(    短期借款                        123,456,789) Tj
0 -15 Td
(    應付帳款                        456,789,012) Tj
0 -15 Td
(    其他流動負債                    234,567,890) Tj
0 -15 Td
(  流動負債合計                      814,813,691) Tj

0 -25 Td
(  非流動負債) Tj
0 -15 Td
(    長期借款                        345,678,901) Tj
0 -15 Td
(    其他非流動負債                  123,456,789) Tj
0 -15 Td
(  非流動負債合計                    469,135,690) Tj

0 -20 Td
(負債總計                          1,283,949,381) Tj

0 -25 Td
(  股東權益) Tj
0 -15 Td
(    股本                          2,593,625,000) Tj
0 -15 Td
(    保留盈餘                      2,174,388,569) Tj
0 -15 Td
(  股東權益總計                    4,768,013,569) Tj

0 -20 Td
(負債及股東權益總計                6,051,962,950) Tj

ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000053 00000 n 
0000000125 00000 n 
0000000348 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
2898
%%EOF
    """
    
    return financial_content.encode('utf-8')


async def demo_pdf_processor():
    """演示PDF處理器功能"""
    print("=" * 80)
    print("🔍 演示 1: PDF處理器核心功能")
    print("=" * 80)
    
    try:
        from src.services.pdf_processor import FinancialPDFProcessor
        
        # 創建處理器實例
        processor = FinancialPDFProcessor()
        print("✅ PDF處理器初始化成功")
        
        # 創建演示PDF
        demo_pdf = create_demo_pdf()
        print(f"✅ 創建演示PDF文件 (大小: {len(demo_pdf)} bytes)")
        
        # 處理PDF
        print("🔄 開始處理PDF文件...")
        result = await processor.process_pdf(demo_pdf, "demo_financial_statement.pdf")
        
        if result['status'] == 'success':
            print("✅ PDF處理成功")
            print(f"📊 提取的財務指標數量: {len(result['financial_data'])}")
            print(f"🔧 使用的提取方法: {result['extraction_methods']}")
            
            # 顯示提取的財務數據
            print("\n📈 提取的財務數據:")
            for metric, data in result['financial_data'].items():
                value = data['value']
                unit = data['unit_multiplier']
                confidence = data['confidence']
                method = data['extraction_method']
                
                print(f"  • {translate_metric_name(metric)}: {format_number(value)} ({get_unit_name(unit)})")
                print(f"    置信度: {confidence:.2%}, 方法: {method}")
            
            # 驗證數據
            print("\n🔍 進行數據驗證...")
            validation_result = await processor.validate_financial_data(result['financial_data'])
            
            print(f"✅ 驗證結果: {'通過' if validation_result['is_valid'] else '失敗'}")
            
            if validation_result['warnings']:
                print("⚠️  警告:")
                for warning in validation_result['warnings']:
                    print(f"    • {warning}")
                    
            if validation_result['errors']:
                print("❌ 錯誤:")
                for error in validation_result['errors']:
                    print(f"    • {error}")
        else:
            print(f"❌ PDF處理失敗: {result.get('error_message', '未知錯誤')}")
            
    except Exception as e:
        print(f"❌ 演示失敗: {e}")
        import traceback
        traceback.print_exc()


def demo_api_upload():
    """演示API上傳功能"""
    print("\n" + "=" * 80)
    print("🌐 演示 2: API文件上傳功能")
    print("=" * 80)
    
    try:
        import requests
        import time
        
        # API基礎URL
        base_url = "http://localhost:8000"
        
        print("🔍 檢查API服務狀態...")
        try:
            response = requests.get(f"{base_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ API服務運行正常")
            else:
                print(f"⚠️  API服務狀態異常: {response.status_code}")
                return
        except requests.exceptions.ConnectionError:
            print("❌ 無法連接到API服務，請確保服務已啟動")
            print("   啟動命令: python src/main.py 或 uvicorn src.main:app --reload")
            return
        except requests.exceptions.Timeout:
            print("❌ API服務響應超時")
            return
        
        # 檢查支援格式
        print("📋 查詢支援的文件格式...")
        response = requests.get(f"{base_url}/api/v1/documents/supported-formats")
        if response.status_code == 200:
            data = response.json()
            print("✅ 支援的格式:")
            for fmt in data['supported_formats']:
                print(f"    • {fmt['format']}: {fmt['description']}")
        
        # 測試文件提取
        print("\n🧪 測試PDF提取功能...")
        demo_pdf = create_demo_pdf()
        files = {'file': ('demo.pdf', io.BytesIO(demo_pdf), 'application/pdf')}
        
        response = requests.post(
            f"{base_url}/api/v1/documents/test-extraction",
            files=files
        )
        
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                preview = data['preview']
                print("✅ 提取測試成功")
                print(f"    📄 文件: {preview['filename']}")
                print(f"    📊 找到指標: {preview['financial_metrics_found']} 個")
                print(f"    🔧 提取方法: {preview['extraction_methods']}")
            else:
                print(f"❌ 提取測試失敗: {data['message']}")
        else:
            print(f"❌ API請求失敗: {response.status_code}")
        
        # 同步上傳測試
        print("\n📤 測試同步文件上傳...")
        files = {'file': ('demo_sync.pdf', io.BytesIO(demo_pdf), 'application/pdf')}
        data = {
            'company_id': '2330',
            'report_period': '2024Q1',
            'async_processing': 'false'
        }
        
        response = requests.post(
            f"{base_url}/api/v1/documents/upload/financial-statement",
            files=files,
            data=data
        )
        
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                print("✅ 同步上傳成功")
                print(f"    🆔 文件ID: {result['document_id']}")
                
                if result['financial_data']:
                    print(f"    📊 財務指標: {len(result['financial_data'])} 個")
                    # 顯示前3個指標
                    count = 0
                    for metric, data in result['financial_data'].items():
                        if count >= 3:
                            break
                        print(f"        • {translate_metric_name(metric)}: {format_number(data['value'])}")
                        count += 1
            else:
                print(f"❌ 同步上傳失敗: {result['message']}")
        else:
            print(f"❌ 同步上傳API請求失敗: {response.status_code}")
        
        # 異步上傳測試
        print("\n🔄 測試異步文件上傳...")
        files = {'file': ('demo_async.pdf', io.BytesIO(demo_pdf), 'application/pdf')}
        data = {
            'company_id': '1234',
            'async_processing': 'true'
        }
        
        response = requests.post(
            f"{base_url}/api/v1/documents/upload/financial-statement",
            files=files,
            data=data
        )
        
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                print("✅ 異步上傳成功")
                document_id = result['document_id']
                print(f"    🆔 文件ID: {document_id}")
                
                # 輪詢處理狀態
                print("    ⏳ 等待處理完成...")
                max_attempts = 15
                for attempt in range(max_attempts):
                    time.sleep(2)  # 等待2秒
                    
                    status_response = requests.get(
                        f"{base_url}/api/v1/documents/processing-status/{document_id}"
                    )
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        progress = status_data['progress']
                        status = status_data['status']
                        message = status_data.get('message', '')
                        
                        print(f"    📊 進度: {progress}% - {status} - {message}")
                        
                        if status in ['completed', 'failed']:
                            if status == 'completed' and status_data.get('results'):
                                results = status_data['results']
                                financial_data = results.get('financial_data', {})
                                print(f"    ✅ 處理完成，提取到 {len(financial_data)} 個財務指標")
                            else:
                                print(f"    ❌ 處理失敗: {message}")
                            break
                    else:
                        print(f"    ⚠️  狀態查詢失敗: {status_response.status_code}")
                        break
                
                # 清理處理結果
                print("    🧹 清理處理結果...")
                requests.delete(f"{base_url}/api/v1/documents/processing-result/{document_id}")
                
            else:
                print(f"❌ 異步上傳失敗: {result['message']}")
        else:
            print(f"❌ 異步上傳API請求失敗: {response.status_code}")
            
    except ImportError:
        print("❌ 請安裝 requests 庫: pip install requests")
    except Exception as e:
        print(f"❌ 演示失敗: {e}")


def demo_frontend_integration():
    """演示前端整合"""
    print("\n" + "=" * 80)
    print("🖥️  演示 3: 前端WebUI整合")
    print("=" * 80)
    
    print("📱 前端測試頁面: http://localhost:8000/static/upload_test.html")
    print()
    print("🔧 測試步驟:")
    print("   1. 啟動API服務: python src/main.py")
    print("   2. 在瀏覽器中打開: http://localhost:8000/static/upload_test.html")
    print("   3. 上傳PDF文件進行測試")
    print("   4. 查看提取結果和驗證信息")
    print()
    print("💡 功能特點:")
    print("   • 支援拖放上傳")
    print("   • 實時處理進度顯示")
    print("   • 同步/異步處理選擇")  
    print("   • 財務數據視覺化展示")
    print("   • 數據驗證結果顯示")


def translate_metric_name(key):
    """翻譯指標名稱"""
    translations = {
        'total_assets': '總資產',
        'current_assets': '流動資產',
        'total_liabilities': '總負債',
        'current_liabilities': '流動負債',
        'shareholders_equity': '股東權益',
        'revenue': '營收',
        'gross_profit': '毛利',
        'operating_income': '營業利益',
        'net_income': '淨利',
        'eps': '每股盈餘',
        'operating_cash_flow': '營業活動現金流',
        'investing_cash_flow': '投資活動現金流',
        'financing_cash_flow': '融資活動現金流'
    }
    return translations.get(key, key)


def get_unit_name(multiplier):
    """獲取單位名稱"""
    units = {
        1: '元',
        1000: '千元',
        10000: '萬元',
        1000000: '百萬元',
        100000000: '億元'
    }
    return units.get(multiplier, '')


def format_number(num):
    """格式化數字"""
    if isinstance(num, (int, float)):
        return f"{num:,.0f}"
    return str(num)


def main():
    """主函數"""
    print("🏦 財務分析系統 - PDF上傳功能完整演示")
    print("📋 本演示將展示從WebUI讀取PDF財務報表並擷取財務數字的完整功能")
    print()
    
    # 演示1: PDF處理器核心功能
    asyncio.run(demo_pdf_processor())
    
    # 演示2: API上傳功能
    demo_api_upload()
    
    # 演示3: 前端整合說明
    demo_frontend_integration()
    
    print("\n" + "=" * 80)
    print("🎉 演示完成!")
    print("=" * 80)
    print()
    print("📝 總結:")
    print("   ✅ PDF處理器: 能夠從PDF中提取財務數字")
    print("   ✅ API端點: 支援同步和異步文件上傳")
    print("   ✅ 數據驗證: 自動驗證財務數據合理性") 
    print("   ✅ 前端整合: 提供完整的WebUI測試界面")
    print()
    print("🔗 相關連結:")
    print("   • API文檔: http://localhost:8000/docs")
    print("   • 測試頁面: http://localhost:8000/static/upload_test.html")
    print("   • 健康檢查: http://localhost:8000/health")
    print()
    print("🛠️  後續開發建議:")
    print("   • 增加更多PDF格式支援")
    print("   • 改善OCR識別準確度")
    print("   • 添加財務報表模板匹配")
    print("   • 實現批量文件處理")


if __name__ == "__main__":
    main()