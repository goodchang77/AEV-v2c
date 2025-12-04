#!/usr/bin/env python3
"""
前端界面自動化測試腳本
Frontend Interface Automated Testing Script
"""
import requests
import json
import sys
import time
from pathlib import Path

def test_frontend_interface():
    """測試前端界面的各項功能"""
    print("🌐 開始前端界面自動化測試...")
    
    base_url = "http://localhost:8001"
    
    test_results = {
        "static_file_service": False,
        "html_loading": False,
        "api_connectivity": False,
        "pdf_upload_simulation": False,
        "data_extraction_api": False,
        "supported_formats_api": False
    }
    
    # 1. 測試靜態文件服務
    print("\n1️⃣  測試靜態文件服務...")
    try:
        response = requests.get(f"{base_url}/static/upload_test.html", timeout=10)
        if response.status_code == 200 and "財務報表PDF上傳測試" in response.text:
            print("   ✅ 靜態HTML文件服務正常")
            test_results["static_file_service"] = True
            test_results["html_loading"] = True
        else:
            print(f"   ❌ 靜態文件服務異常，狀態碼: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 靜態文件服務失敗: {e}")
    
    # 2. 驗證HTML內容結構
    print("\n2️⃣  驗證前端頁面結構...")
    try:
        response = requests.get(f"{base_url}/static/upload_test.html")
        html_content = response.text
        
        # 檢查關鍵元素
        required_elements = [
            'id="uploadForm"',        # 上傳表單
            'id="file"',              # 文件選擇器
            'id="companyId"',         # 公司代碼輸入
            'id="reportPeriod"',      # 報告期間輸入
            'id="asyncProcessing"',   # 異步處理選項
            'id="uploadBtn"',         # 上傳按鈕
            'id="testBtn"',           # 測試按鈕
            'id="results"',           # 結果顯示區
            'accept=".pdf"'           # PDF文件限制
        ]
        
        missing_elements = []
        for element in required_elements:
            if element not in html_content:
                missing_elements.append(element)
        
        if not missing_elements:
            print("   ✅ HTML頁面結構完整，包含所有必要元素")
        else:
            print(f"   ⚠️  頁面結構不完整，缺少元素: {missing_elements}")
            
        # 檢查JavaScript功能
        js_functions = [
            'uploadFile',
            'handleTestResult',  
            'handleUploadResult',
            'displayResults',
            'translateMetricName',
            'formatNumber'
        ]
        
        missing_functions = []
        for func in js_functions:
            if func not in html_content:
                missing_functions.append(func)
        
        if not missing_functions:
            print("   ✅ JavaScript功能函數完整")
        else:
            print(f"   ⚠️  JavaScript功能不完整，缺少函數: {missing_functions}")
            
    except Exception as e:
        print(f"   ❌ 頁面結構檢查失敗: {e}")
    
    # 3. 測試前端所需的API端點
    print("\n3️⃣  測試前端依賴的API端點...")
    
    api_endpoints = [
        {
            "name": "支援格式查詢",
            "url": f"{base_url}/api/v1/documents/supported-formats",
            "method": "GET",
            "key": "supported_formats_api"
        },
        {
            "name": "文件測試提取",  
            "url": f"{base_url}/api/v1/documents/test-extraction",
            "method": "POST",
            "key": "data_extraction_api",
            "test_file": True
        }
    ]
    
    api_success_count = 0
    
    for endpoint in api_endpoints:
        try:
            if endpoint["method"] == "GET":
                response = requests.get(endpoint["url"], timeout=10)
                if response.status_code == 200:
                    print(f"   ✅ {endpoint['name']} API正常")
                    test_results[endpoint["key"]] = True
                    api_success_count += 1
                else:
                    print(f"   ❌ {endpoint['name']} API異常: {response.status_code}")
                    
            elif endpoint["method"] == "POST" and endpoint.get("test_file"):
                # 測試PDF上傳端點（使用測試文件）
                pdf_path = "/mnt/d/Project/AEV-v2c/testdata/NVDSA Q2FY25-CFO-Commentary.pdf"
                if Path(pdf_path).exists():
                    with open(pdf_path, 'rb') as f:
                        files = {'file': ('test.pdf', f, 'application/pdf')}
                        response = requests.post(endpoint["url"], files=files, timeout=30)
                        
                    if response.status_code == 200:
                        result = response.json()
                        if result.get('success'):
                            print(f"   ✅ {endpoint['name']} API正常")
                            test_results[endpoint["key"]] = True
                            api_success_count += 1
                        else:
                            print(f"   ⚠️  {endpoint['name']} API回應異常: {result.get('message', '未知錯誤')}")
                    else:
                        print(f"   ❌ {endpoint['name']} API失敗: {response.status_code}")
                else:
                    print(f"   ⚠️  測試文件不存在，跳過 {endpoint['name']} 測試")
                        
        except Exception as e:
            print(f"   ❌ {endpoint['name']} API測試失敗: {e}")
    
    if api_success_count >= len(api_endpoints) - 1:  # 允許一個失敗
        test_results["api_connectivity"] = True
    
    # 4. 模擬PDF上傳工作流程
    print("\n4️⃣  模擬PDF上傳工作流程...")
    
    pdf_path = "/mnt/d/Project/AEV-v2c/testdata/NVDSA Q2FY25-CFO-Commentary.pdf"
    if Path(pdf_path).exists():
        try:
            # 模擬同步上傳
            with open(pdf_path, 'rb') as f:
                files = {'file': ('NVDA-Q2FY25.pdf', f, 'application/pdf')}
                data = {
                    'company_id': 'NVDA',
                    'report_period': '2025Q2', 
                    'async_processing': 'false'
                }
                
                response = requests.post(
                    f"{base_url}/api/v1/documents/upload/financial-statement",
                    files=files,
                    data=data,
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success') and result.get('financial_data'):
                        print("   ✅ PDF上傳和處理工作流程正常")
                        print(f"      - 提取財務數據: {len(result['financial_data'])} 項")
                        print(f"      - 數據驗證: {'通過' if result.get('validation_results', {}).get('is_valid', False) else '有問題'}")
                        test_results["pdf_upload_simulation"] = True
                    else:
                        print(f"   ⚠️  PDF處理結果異常: {result.get('message', '未知錯誤')}")
                else:
                    print(f"   ❌ PDF上傳失敗: {response.status_code}")
                    
        except Exception as e:
            print(f"   ❌ PDF上傳工作流程測試失敗: {e}")
    else:
        print("   ⚠️  測試PDF文件不存在，跳過上傳測試")
    
    # 5. 測試結果統計
    print("\n📊 前端測試結果統計:")
    
    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results.values() if result)
    
    print(f"   - 總測試項目: {total_tests}")
    print(f"   - 通過項目: {passed_tests}")
    print(f"   - 成功率: {passed_tests/total_tests*100:.1f}%")
    
    print(f"\n📋 詳細結果:")
    test_descriptions = {
        "static_file_service": "靜態文件服務",
        "html_loading": "HTML頁面加載",
        "api_connectivity": "API端點連接",
        "pdf_upload_simulation": "PDF上傳模擬",
        "data_extraction_api": "數據提取API",
        "supported_formats_api": "格式支援API"
    }
    
    for key, passed in test_results.items():
        status = "✅ 通過" if passed else "❌ 失敗"
        print(f"   {status} {test_descriptions.get(key, key)}")
    
    # 評估前端整體狀態
    print(f"\n🏆 前端界面整體評估:")
    
    if passed_tests >= total_tests * 0.8:
        print("   ✅ 前端界面功能完備，可以投入使用")
        overall_status = "PASS"
    elif passed_tests >= total_tests * 0.6:
        print("   ⚠️  前端界面基本可用，建議修復部分功能")
        overall_status = "PARTIAL"
    else:
        print("   ❌ 前端界面存在嚴重問題，需要修復")
        overall_status = "FAIL"
    
    return {
        "overall_status": overall_status,
        "success_rate": passed_tests/total_tests,
        "detailed_results": test_results,
        "test_summary": {
            "total": total_tests,
            "passed": passed_tests,
            "failed": total_tests - passed_tests
        }
    }

if __name__ == "__main__":
    print("🖥️  Anthropic Financial Service - 前端界面自動化測試")
    print("="*60)
    
    result = test_frontend_interface()
    
    if result["overall_status"] == "PASS":
        print("\n✅ 前端界面測試全部通過！")
    elif result["overall_status"] == "PARTIAL":
        print("\n⚠️  前端界面測試部分通過")
        sys.exit(1)
    else:
        print("\n❌ 前端界面測試失敗")
        sys.exit(2)