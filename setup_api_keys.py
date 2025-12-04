#!/usr/bin/env python3
"""
API Keys 快速配置腳本
Quick Setup Script for API Keys
"""

import os
import sys
from pathlib import Path


def setup_alpha_vantage_key():
    """配置Alpha Vantage API Key"""
    print("🔧 配置 Alpha Vantage API Key")
    print("=" * 50)
    
    # 取得當前.env檔案
    env_file = Path(".env")
    
    if not env_file.exists():
        print("❌ 找不到 .env 檔案，正在創建...")
        # 從範例檔案複製
        example_file = Path(".env.example")
        if example_file.exists():
            import shutil
            shutil.copy(example_file, env_file)
            print("✅ 已從 .env.example 創建 .env 檔案")
        else:
            print("❌ 找不到 .env.example 檔案")
            return False
    
    # 讀取現有配置
    with open(env_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 提示用戶輸入API Key
    print("\n📝 請輸入您的 Alpha Vantage API Key:")
    print("   (從 https://www.alphavantage.co/support/#api-key 取得)")
    print("   範例格式: ABC123DEF456GHI789")
    
    api_key = input("\n🔑 API Key: ").strip()
    
    if not api_key:
        print("❌ API Key 不能為空")
        return False
    
    if len(api_key) < 8:
        print("⚠️  API Key 長度似乎不對，但將繼續配置...")
    
    # 更新.env檔案
    updated = False
    new_lines = []
    
    for line in lines:
        if line.startswith('ALPHA_VANTAGE_API_KEY='):
            new_lines.append(f'ALPHA_VANTAGE_API_KEY={api_key}\n')
            updated = True
            print(f"✅ 已更新現有的 ALPHA_VANTAGE_API_KEY")
        else:
            new_lines.append(line)
    
    # 如果沒有找到現有配置，添加新的
    if not updated:
        new_lines.append(f'\n# Alpha Vantage API Key\nALPHA_VANTAGE_API_KEY={api_key}\n')
        print(f"✅ 已添加新的 ALPHA_VANTAGE_API_KEY")
    
    # 寫回檔案
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print(f"\n🎉 Alpha Vantage API Key 配置完成!")
    print(f"   檔案: {env_file.absolute()}")
    
    return True


def setup_other_optional_keys():
    """配置其他可選的API Keys"""
    print("\n🔧 配置其他可選 API Keys")
    print("=" * 50)
    
    optional_keys = {
        "FUGLE_API_KEY": {
            "name": "Fugle 富果 API",
            "url": "https://developer.fugle.tw",
            "description": "台股專業資料服務"
        },
        "FMP_API_KEY": {
            "name": "Financial Modeling Prep API", 
            "url": "https://financialmodelingprep.com/developer/docs",
            "description": "全球金融資料服務"
        }
    }
    
    env_file = Path(".env")
    
    for key_name, info in optional_keys.items():
        print(f"\n📊 {info['name']}")
        print(f"   網址: {info['url']}")
        print(f"   說明: {info['description']}")
        
        choice = input(f"   是否要設定 {key_name}? (y/N): ").strip().lower()
        
        if choice in ['y', 'yes']:
            api_key = input(f"   請輸入 {key_name}: ").strip()
            
            if api_key:
                # 更新.env檔案
                with open(env_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                updated = False
                new_lines = []
                
                for line in lines:
                    if line.startswith(f'{key_name}='):
                        new_lines.append(f'{key_name}={api_key}\n')
                        updated = True
                    else:
                        new_lines.append(line)
                
                if not updated:
                    new_lines.append(f'\n# {info["name"]}\n{key_name}={api_key}\n')
                
                with open(env_file, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
                
                print(f"   ✅ {key_name} 配置完成")
            else:
                print(f"   ⏩ 跳過 {key_name}")
        else:
            print(f"   ⏩ 跳過 {key_name}")


def verify_configuration():
    """驗證配置"""
    print("\n🔍 驗證配置...")
    print("=" * 50)
    
    env_file = Path(".env")
    
    if not env_file.exists():
        print("❌ .env 檔案不存在")
        return False
    
    # 讀取環境變數
    with open(env_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 檢查重要的配置
    checks = {
        "DATABASE_URL": "資料庫連線",
        "REDIS_URL": "Redis快取", 
        "ALPHA_VANTAGE_API_KEY": "Alpha Vantage API",
        "SECRET_KEY": "系統密鑰"
    }
    
    results = []
    
    for key, description in checks.items():
        if f"{key}=" in content:
            # 檢查是否不是預設值
            lines = content.split('\n')
            for line in lines:
                if line.startswith(f"{key}="):
                    value = line.split('=', 1)[1].strip()
                    if value and not value.startswith('your_') and value != 'change-this':
                        results.append((key, description, "✅", "已配置"))
                        break
                    else:
                        results.append((key, description, "⚠️", "需要更新"))
                        break
        else:
            results.append((key, description, "❌", "未找到"))
    
    print("\n📋 配置檢查結果:")
    for key, desc, status, msg in results:
        print(f"   {status} {desc:<20} {msg}")
    
    # 統計
    configured = sum(1 for _, _, status, _ in results if status == "✅")
    total = len(results)
    
    print(f"\n📊 配置完成度: {configured}/{total} ({configured/total*100:.0f}%)")
    
    return configured >= 2  # 至少需要資料庫和API Key


def main():
    """主函數"""
    print("🚀 財務分析系統 API Keys 配置工具")
    print("=" * 60)
    print("此工具將幫助您快速配置系統所需的API Keys")
    print()
    
    try:
        # 1. 配置Alpha Vantage (必需)
        if not setup_alpha_vantage_key():
            print("❌ Alpha Vantage API Key 配置失敗")
            return False
        
        # 2. 配置其他可選Keys
        choice = input("\n是否要配置其他可選的API Keys? (y/N): ").strip().lower()
        if choice in ['y', 'yes']:
            setup_other_optional_keys()
        
        # 3. 驗證配置
        if verify_configuration():
            print("\n🎉 配置完成！")
            print("\n📝 後續步驟:")
            print("   1. 重新啟動應用程式以載入新配置")
            print("   2. 執行測試確認API連線正常:")
            print("      python test_multi_sources.py")
            print("   3. 開始使用增強版市場資料API")
            
            return True
        else:
            print("\n⚠️  配置未完全完成，請檢查設定")
            return False
            
    except KeyboardInterrupt:
        print("\n\n⏹️  配置被用戶中斷")
        return False
    except Exception as e:
        print(f"\n❌ 配置過程發生錯誤: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)