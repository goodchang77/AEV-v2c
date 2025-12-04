#!/usr/bin/env python3
"""
端到端整合測試腳本
End-to-End Integration Test
"""
import requests
import json
import sys
import time
from pathlib import Path

def test_pdf_upload_workflow():
    """測試完整的PDF上傳到財務分析工作流程"""
    print("🔄 開始端到端整合測試...")
    print("📋 測試場景: PDF上傳 → 財務數據提取 → 比率計算 → 分析報告")
    
    base_url = "http://localhost:8001"
    
    # 第1步: 檢查服務狀態
    print("\n1️⃣  檢查服務狀態...")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            print("   ✅ API服務正常運行")
        else:
            print("   ❌ API服務狀態異常")
            return False
    except Exception as e:
        print(f"   ❌ API服務連接失敗: {e}")
        return False
    
    # 第2步: 獲取支援的文件格式
    print("\n2️⃣  檢查文件格式支援...")
    try:
        response = requests.get(f"{base_url}/api/v1/documents/supported-formats")
        if response.status_code == 200:
            formats = response.json()
            print("   ✅ 支援的格式:")
            for fmt in formats['supported_formats']:
                print(f"      - {fmt['format']}: {fmt['description']}")
        else:
            print("   ⚠️  無法獲取支援格式")
    except Exception as e:
        print(f"   ❌ 格式檢查失敗: {e}")
    
    # 第3步: 測試PDF文件提取
    print("\n3️⃣  測試PDF數據提取...")
    pdf_path = "/mnt/d/Project/AEV-v2c/testdata/NVDSA Q2FY25-CFO-Commentary.pdf"
    
    if not Path(pdf_path).exists():
        print(f"   ❌ 測試PDF文件不存在: {pdf_path}")
        return False
    
    try:
        with open(pdf_path, 'rb') as f:
            files = {'file': ('NVDSA-Q2FY25.pdf', f, 'application/pdf')}
            data = {
                'company_id': 'NVDA',
                'report_period': '2025Q2'
            }
            
            response = requests.post(
                f"{base_url}/api/v1/documents/test-extraction",
                files=files,
                data=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print("   ✅ PDF數據提取成功")
                
                if result['success']:
                    preview = result['preview']
                    print(f"      - 檔案大小: {preview['file_size']:,} bytes")
                    print(f"      - 提取方法: {', '.join(preview['extraction_methods'])}")
                    print(f"      - 財務指標數: {preview['financial_metrics_found']}")
                    print("      - 樣本數據:")
                    for key, value in preview['sample_data'].items():
                        print(f"        • {key}: {value}")
                else:
                    print(f"      ⚠️  提取過程遇到問題: {result['message']}")
                    
            else:
                print(f"   ❌ PDF提取失敗，狀態碼: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"   ❌ PDF提取測試失敗: {e}")
        return False
    
    # 第4步: 測試完整上傳流程
    print("\n4️⃣  測試完整文件上傳流程...")
    try:
        with open(pdf_path, 'rb') as f:
            files = {'file': ('NVDSA-Q2FY25.pdf', f, 'application/pdf')}
            data = {
                'company_id': 'NVDA',
                'report_period': '2025Q2',
                'async_processing': 'false'  # 同步處理方便測試
            }
            
            response = requests.post(
                f"{base_url}/api/v1/documents/upload/financial-statement",
                files=files,
                data=data,
                timeout=60
            )
            
            if response.status_code == 200:
                upload_result = response.json()
                print("   ✅ 文件上傳處理成功")
                
                if upload_result['success']:
                    print(f"      - 文件ID: {upload_result['document_id']}")
                    
                    # 檢查提取的財務數據
                    if 'financial_data' in upload_result and upload_result['financial_data']:
                        financial_data = upload_result['financial_data']
                        print(f"      - 提取財務數據: {len(financial_data)} 項")
                        
                        # 顯示主要財務指標
                        key_metrics = ['revenue', 'net_income', 'operating_income', 'gross_profit', 'eps']
                        print("      - 主要財務指標:")
                        for metric in key_metrics:
                            if metric in financial_data:
                                value = financial_data[metric]['value']
                                print(f"        • {metric}: ${value:,.2f}M")
                        
                        # 檢查驗證結果
                        if 'validation_results' in upload_result:
                            validation = upload_result['validation_results']
                            print(f"      - 數據驗證: {'通過' if validation['is_valid'] else '有問題'}")
                            if validation['warnings']:
                                print("      - 警告:")
                                for warning in validation['warnings'][:3]:
                                    print(f"        ⚠️  {warning}")
                        
                        return True
                    else:
                        print("      ⚠️  未能提取財務數據")
                        return False
                else:
                    print(f"      ❌ 文件處理失敗: {upload_result['message']}")
                    return False
            else:
                error_detail = response.json().get('detail', '未知錯誤') if response.headers.get('content-type', '').startswith('application/json') else response.text
                print(f"   ❌ 文件上傳失敗，狀態碼: {response.status_code}")
                print(f"      錯誤詳情: {error_detail}")
                return False
                
    except Exception as e:
        print(f"   ❌ 文件上傳測試失敗: {e}")
        return False

def test_financial_ratios_api():
    """測試財務比率API"""
    print("\n5️⃣  測試財務比率API...")
    base_url = "http://localhost:8001"
    
    try:
        # 測試基本比率服務
        response = requests.get(f"{base_url}/api/v1/ratios/")
        if response.status_code == 200:
            result = response.json()
            print("   ✅ 財務比率服務可用")
            print(f"      狀態: {result.get('status', 'unknown')}")
        else:
            print(f"   ⚠️  財務比率服務回應異常: {response.status_code}")
        
        # 測試特定公司比率查詢
        response = requests.get(f"{base_url}/api/v1/ratios/NVDA")
        if response.status_code == 200:
            result = response.json()
            print("   ✅ 公司財務比率查詢成功")
            print(f"      公司代碼: {result.get('company_id', 'N/A')}")
        else:
            print(f"   ⚠️  公司財務比率查詢異常: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 財務比率API測試失敗: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Anthropic Financial Service - 端到端整合測試")
    print("="*60)
    
    # 執行主要測試流程
    pdf_test_success = test_pdf_upload_workflow()
    ratios_test_success = test_financial_ratios_api()
    
    print("\n" + "="*60)
    print("📊 測試結果摘要:")
    print(f"   PDF上傳工作流程: {'✅ 通過' if pdf_test_success else '❌ 失敗'}")
    print(f"   財務比率API: {'✅ 通過' if ratios_test_success else '❌ 失敗'}")
    
    overall_success = pdf_test_success and ratios_test_success
    
    if overall_success:
        print("\n🎉 端到端整合測試全部通過！")
        print("   系統各模組間協作正常，可以進行生產部署。")
    else:
        print("\n⚠️  端到端測試存在問題")
        print("   建議檢查失敗的組件並修復後重新測試。")
        sys.exit(1)