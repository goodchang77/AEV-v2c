#!/usr/bin/env python3
"""
API端點連接性測試腳本
Test API Endpoints Connectivity
"""
import requests
import json
import time
import sys
from pathlib import Path

def test_api_endpoints():
    """測試所有API端點的連接性"""
    print("🌐 開始API端點連接性測試...")
    
    base_url = "http://localhost:8001"
    
    # 測試端點列表
    endpoints = [
        {
            "name": "健康檢查",
            "method": "GET",
            "url": f"{base_url}/health",
            "expected_status": 200
        },
        {
            "name": "API資訊",
            "method": "GET", 
            "url": f"{base_url}/",
            "expected_status": 200
        },
        {
            "name": "公司列表",
            "method": "GET",
            "url": f"{base_url}/api/v1/companies/",
            "expected_status": 200
        },
        {
            "name": "財務比率",
            "method": "GET",
            "url": f"{base_url}/api/v1/ratios/",
            "expected_status": 200
        },
        {
            "name": "市場資料",
            "method": "GET",
            "url": f"{base_url}/api/v1/market-data/",
            "expected_status": 200
        },
        {
            "name": "支援的文件格式",
            "method": "GET",
            "url": f"{base_url}/api/v1/documents/supported-formats",
            "expected_status": 200
        }
    ]
    
    results = []
    
    for endpoint in endpoints:
        print(f"\n📡 測試: {endpoint['name']}")
        print(f"   URL: {endpoint['url']}")
        
        try:
            # 發送請求
            if endpoint['method'] == 'GET':
                response = requests.get(endpoint['url'], timeout=10)
            elif endpoint['method'] == 'POST':
                response = requests.post(endpoint['url'], timeout=10)
            
            print(f"   狀態碼: {response.status_code}")
            
            # 檢查狀態碼
            if response.status_code == endpoint['expected_status']:
                print("   ✅ 連接成功")
                success = True
            else:
                print(f"   ❌ 狀態碼錯誤，期望: {endpoint['expected_status']}")
                success = False
            
            # 嘗試解析JSON響應
            try:
                json_data = response.json()
                print(f"   📄 響應內容: {json.dumps(json_data, indent=2, ensure_ascii=False)[:200]}...")
            except:
                print(f"   📄 響應內容: {response.text[:200]}...")
            
            results.append({
                'name': endpoint['name'],
                'url': endpoint['url'],
                'status_code': response.status_code,
                'success': success,
                'response_time': response.elapsed.total_seconds()
            })
            
        except requests.exceptions.ConnectionError:
            print("   ❌ 連接失敗 - 無法連接到服務器")
            results.append({
                'name': endpoint['name'],
                'url': endpoint['url'],
                'success': False,
                'error': 'Connection Error'
            })
        except requests.exceptions.Timeout:
            print("   ❌ 連接失敗 - 請求超時")
            results.append({
                'name': endpoint['name'],
                'url': endpoint['url'],
                'success': False,
                'error': 'Timeout'
            })
        except Exception as e:
            print(f"   ❌ 連接失敗 - 其他錯誤: {e}")
            results.append({
                'name': endpoint['name'],
                'url': endpoint['url'],
                'success': False,
                'error': str(e)
            })
        
        time.sleep(0.5)  # 短暫延遲避免過載
    
    # 統計結果
    successful = sum(1 for r in results if r.get('success', False))
    total = len(results)
    
    print(f"\n📊 API端點測試結果:")
    print(f"   - 總計: {total} 個端點")
    print(f"   - 成功: {successful} 個")
    print(f"   - 失敗: {total - successful} 個")
    print(f"   - 成功率: {successful/total*100:.1f}%")
    
    # 詳細結果
    print(f"\n📋 詳細結果:")
    for result in results:
        status_icon = "✅" if result.get('success', False) else "❌"
        print(f"   {status_icon} {result['name']}")
        if 'response_time' in result:
            print(f"      響應時間: {result['response_time']:.3f}s")
        if 'error' in result:
            print(f"      錯誤: {result['error']}")
    
    return successful == total

if __name__ == "__main__":
    print("等待API服務器啟動...")
    time.sleep(2)
    
    success = test_api_endpoints()
    if success:
        print("\n✅ 所有API端點測試通過")
    else:
        print("\n⚠️  部分API端點測試失敗")
        sys.exit(1)