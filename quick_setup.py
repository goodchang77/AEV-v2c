#!/usr/bin/env python3
"""
快速配置 Alpha Vantage API Key
"""

import sys

def update_env_file(api_key):
    """更新.env檔案中的API Key"""
    try:
        # 讀取現有.env檔案
        with open('.env', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 替換API Key
        if 'ALPHA_VANTAGE_API_KEY=' in content:
            lines = content.split('\n')
            new_lines = []
            for line in lines:
                if line.startswith('ALPHA_VANTAGE_API_KEY='):
                    new_lines.append(f'ALPHA_VANTAGE_API_KEY={api_key}')
                else:
                    new_lines.append(line)
            content = '\n'.join(new_lines)
        else:
            # 添加新的API Key
            content += f'\n\n# Alpha Vantage API Key\nALPHA_VANTAGE_API_KEY={api_key}\n'
        
        # 寫回檔案
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ 已成功配置 Alpha Vantage API Key: {api_key[:8]}...")
        return True
        
    except Exception as e:
        print(f"❌ 配置失敗: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("使用方法: python quick_setup.py YOUR_API_KEY")
        sys.exit(1)
    
    api_key = sys.argv[1].strip()
    if update_env_file(api_key):
        print("🎉 配置完成！請重新啟動應用程式")
    else:
        sys.exit(1)