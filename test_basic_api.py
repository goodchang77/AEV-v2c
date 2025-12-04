#!/usr/bin/env python3
"""
基礎 API 測試腳本
Basic API Testing Script
"""

import httpx
import asyncio
import time
import json

async def test_health_endpoint():
    """測試健康檢查端點"""
    print("🔍 測試健康檢查端點...")
    
    try:
        async with httpx.AsyncClient() as client:
            # 基本健康檢查
            response = await client.get("http://localhost:8000/health")
            print(f"  /health 狀態碼: {response.status_code}")
            print(f"  回應內容: {response.json()}")
            
            # 詳細健康檢查
            try:
                response = await client.get("http://localhost:8000/api/v1/health/detailed")
                print(f"  /api/v1/health/detailed 狀態碼: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"  系統狀態: {data.get('status', 'unknown')}")
                    checks = data.get('checks', {})
                    for check_name, check_result in checks.items():
                        status = check_result.get('status', 'unknown')
                        message = check_result.get('message', '')
                        print(f"    {check_name}: {status} - {message}")
                else:
                    print(f"  回應內容: {response.text}")
            except Exception as e:
                print(f"  詳細健康檢查錯誤: {e}")
                
    except httpx.ConnectError:
        print("  ❌ 無法連接到 API 服務，可能未啟動")
        return False
    except Exception as e:
        print(f"  ❌ 測試失敗: {e}")
        return False
    
    return True

async def test_basic_endpoints():
    """測試基本 API 端點"""
    print("\n🔍 測試基本 API 端點...")
    
    endpoints = [
        ("/", "根路徑"),
        ("/docs", "API 文檔"),
        ("/api/v1/health/", "健康檢查")
    ]
    
    async with httpx.AsyncClient() as client:
        for endpoint, description in endpoints:
            try:
                response = await client.get(f"http://localhost:8000{endpoint}")
                print(f"  {description} ({endpoint}): {response.status_code}")
                if response.status_code == 200 and endpoint == "/":
                    data = response.json()
                    print(f"    訊息: {data.get('message', 'N/A')}")
                    print(f"    版本: {data.get('version', 'N/A')}")
            except Exception as e:
                print(f"  {description} ({endpoint}): 錯誤 - {e}")

async def test_nonexistent_endpoint():
    """測試不存在的端點"""
    print("\n🔍 測試錯誤處理 (404)...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/nonexistent")
            print(f"  /nonexistent 狀態碼: {response.status_code}")
            if response.status_code == 404:
                print("  ✅ 404 錯誤處理正常")
            else:
                print(f"  ⚠️  預期 404，實際收到 {response.status_code}")
    except Exception as e:
        print(f"  ❌ 測試失敗: {e}")

async def main():
    """主測試函數"""
    print("🚀 開始基礎 API 測試")
    print("=" * 50)
    
    # 等待API啟動
    print("⏳ 等待 API 服務啟動...")
    await asyncio.sleep(2)
    
    # 執行測試
    health_ok = await test_health_endpoint()
    if health_ok:
        await test_basic_endpoints()
        await test_nonexistent_endpoint()
        print("\n✅ 基礎 API 測試完成")
    else:
        print("\n❌ API 服務未正常運行，跳過其他測試")
    
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())