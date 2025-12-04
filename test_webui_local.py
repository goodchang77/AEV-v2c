#!/usr/bin/env python3
"""
本地WebUI測試程式
Local WebUI Testing Program
"""
import requests
import json
import webbrowser
import time
import os
import sys
from pathlib import Path

class LocalWebUITester:
    """本地WebUI測試器"""
    
    def __init__(self):
        self.base_url = "http://localhost:8001"
        self.webui_url = f"{self.base_url}/static/upload_test.html"
        
    def test_server_status(self):
        """測試服務器狀態"""
        print("🔍 檢查本地服務器狀態...")
        
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ 服務器正常運行")
                print(f"      - 服務: {data.get('service', 'N/A')}")
                print(f"      - 版本: {data.get('version', 'N/A')}")
                print(f"      - 狀態: {data.get('status', 'N/A')}")
                return True
            else:
                print(f"   ❌ 服務器回應異常: {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ 無法連接服務器: {e}")
            return False
    
    def test_webui_access(self):
        """測試WebUI訪問"""
        print("\n🌐 測試WebUI訪問...")
        
        try:
            response = requests.get(self.webui_url, timeout=5)
            if response.status_code == 200 and "財務報表PDF上傳測試" in response.text:
                print(f"   ✅ WebUI頁面可以正常訪問")
                print(f"   📄 頁面大小: {len(response.content):,} bytes")
                return True
            else:
                print(f"   ❌ WebUI頁面訪問異常: {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ WebUI頁面訪問失敗: {e}")
            return False
    
    def test_api_endpoints(self):
        """測試API端點"""
        print("\n🔧 測試相關API端點...")
        
        endpoints = [
            ("/", "根端點"),
            ("/api/v1/documents/supported-formats", "支援格式"),
            ("/api/v1/health", "API健康檢查")
        ]
        
        results = {}
        for endpoint, name in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                if response.status_code == 200:
                    print(f"   ✅ {name}: 正常")
                    results[endpoint] = True
                else:
                    print(f"   ❌ {name}: {response.status_code}")
                    results[endpoint] = False
            except Exception as e:
                print(f"   ❌ {name}: {e}")
                results[endpoint] = False
        
        return results
    
    def show_webui_info(self):
        """顯示WebUI資訊"""
        print("\n📋 本地WebUI資訊:")
        print(f"   🌐 訪問網址: {self.webui_url}")
        print(f"   🏠 本地服務器: {self.base_url}")
        print(f"   📁 靜態文件目錄: src/static/")
        print(f"   🎯 主要功能:")
        print(f"      - PDF財務報表上傳")
        print(f"      - 公司代碼輸入 (如: TSMC, 2330)")
        print(f"      - 報告期間選擇 (如: 2024Q1)")
        print(f"      - 同步/異步處理選擇")
        print(f"      - 即時結果顯示")
        print(f"      - 財務指標中文翻譯")
    
    def show_usage_guide(self):
        """顯示使用指南"""
        print("\n📖 WebUI使用指南:")
        print("   1️⃣ 打開瀏覽器，訪問上述網址")
        print("   2️⃣ 選擇PDF財務報表文件")
        print("   3️⃣ 輸入公司代碼 (4位數字，如2330)")
        print("   4️⃣ 輸入報告期間 (格式: 2024Q1)")
        print("   5️⃣ 選擇處理模式 (同步/異步)")
        print("   6️⃣ 點擊'上傳並分析'或'測試提取'")
        print("   7️⃣ 查看分析結果和財務指標")
        
        print("\n💡 功能特色:")
        print("   ✨ 拖拽上傳支援")
        print("   ✨ 即時進度顯示") 
        print("   ✨ 財務術語中文化")
        print("   ✨ 結果數據視覺化")
        print("   ✨ 錯誤訊息友好提示")
    
    def compare_with_cloud_version(self, cloud_url):
        """對比雲端版本"""
        print(f"\n☁️ 本地版vs雲端版對比:")
        print(f"   本地版: {self.webui_url}")
        print(f"   雲端版: {cloud_url}")
        
        print("\n📊 功能對比:")
        features = [
            ("PDF上傳分析", "✅", "✅"),
            ("多種評價方法", "✅", "✅"), 
            ("AI智能解析", "✅", "✅"),
            ("中英文支援", "✅", "✅"),
            ("即時結果", "✅", "✅"),
            ("雲端部署", "❌", "✅"),
            ("本地隱私", "✅", "❌"),
            ("離線使用", "✅", "❌"),
            ("自定義配置", "✅", "⚠️")
        ]
        
        print(f"   {'功能':15} {'本地版':8} {'雲端版':8}")
        print(f"   {'-'*15} {'-'*8} {'-'*8}")
        for feature, local, cloud in features:
            print(f"   {feature:15} {local:8} {cloud:8}")
    
    def open_webui_in_browser(self):
        """在瀏覽器中打開WebUI"""
        print(f"\n🚀 準備在瀏覽器中打開WebUI...")
        
        try:
            webbrowser.open(self.webui_url)
            print(f"   ✅ 已在預設瀏覽器中開啟: {self.webui_url}")
            return True
        except Exception as e:
            print(f"   ❌ 無法開啟瀏覽器: {e}")
            print(f"   💡 請手動複製此網址到瀏覽器: {self.webui_url}")
            return False
    
    def run_comprehensive_test(self):
        """執行綜合測試"""
        print("🧪 本地WebUI綜合測試開始...")
        print("="*60)
        
        # 測試服務器
        server_ok = self.test_server_status()
        
        # 測試WebUI
        webui_ok = self.test_webui_access()
        
        # 測試API
        api_results = self.test_api_endpoints()
        
        # 顯示資訊
        self.show_webui_info()
        self.show_usage_guide()
        self.compare_with_cloud_version("https://auto-enterprise-valuation-6d7utpbpna-de.a.run.app/")
        
        # 計算總體結果
        total_tests = 2 + len(api_results)  # server + webui + api endpoints
        passed_tests = int(server_ok) + int(webui_ok) + sum(api_results.values())
        
        print("\n" + "="*60)
        print("📊 測試結果摘要:")
        print(f"   - 總測試項目: {total_tests}")
        print(f"   - 通過項目: {passed_tests}")
        print(f"   - 成功率: {passed_tests/total_tests*100:.1f}%")
        
        if server_ok and webui_ok:
            print("\n🎉 本地WebUI測試成功！")
            
            # 詢問是否開啟瀏覽器
            try:
                user_input = input("\n❓ 是否要在瀏覽器中打開WebUI? (y/n): ").strip().lower()
                if user_input in ['y', 'yes', '是', '']:
                    self.open_webui_in_browser()
                else:
                    print(f"   💡 您可以手動訪問: {self.webui_url}")
            except KeyboardInterrupt:
                print(f"\n   💡 您可以手動訪問: {self.webui_url}")
            
            return True
        else:
            print("\n⚠️ 本地WebUI測試失敗，請檢查服務器狀態")
            return False

def main():
    """主函數"""
    print("🌟 Anthropic Financial Service - 本地WebUI測試程式")
    print("Local WebUI Testing Program")
    print("="*60)
    
    # 檢查是否有可用的PDF測試文件
    test_files = [
        "testdata/NVDSA Q2FY25-CFO-Commentary.pdf",
        "testdata/*.pdf"
    ]
    
    available_files = []
    for pattern in test_files:
        files = list(Path(".").glob(pattern))
        available_files.extend(files)
    
    if available_files:
        print(f"\n📁 發現可用的測試PDF文件:")
        for i, file in enumerate(available_files[:3], 1):  # 只顯示前3個
            print(f"   {i}. {file}")
    
    # 執行測試
    tester = LocalWebUITester()
    success = tester.run_comprehensive_test()
    
    if not success:
        print(f"\n🔧 故障排除建議:")
        print(f"   1. 確認服務器已啟動: uvicorn src.main:app --host 0.0.0.0 --port 8001")
        print(f"   2. 檢查端口8001是否被其他程序占用")
        print(f"   3. 確認在正確的專案目錄中執行")
        print(f"   4. 檢查防火牆設定")
        return 1
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️ 測試被用戶中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 測試執行失敗: {e}")
        sys.exit(1)