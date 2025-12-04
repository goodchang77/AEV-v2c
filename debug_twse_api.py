#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TWSE API 除錯腳本
檢查 API 回傳的實際資料格式
"""

import asyncio
import aiohttp
import json

async def debug_twse_api():
    """除錯 TWSE API"""
    print("🔍 除錯 TWSE API 資料格式...")
    
    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    print(f"✅ API 回應成功，狀態碼: {response.status}")
                    print(f"📊 資料類型: {type(data)}")
                    print(f"📊 資料長度: {len(data) if isinstance(data, (list, dict)) else 'N/A'}")
                    
                    # 檢查資料結構
                    if isinstance(data, list) and len(data) > 0:
                        print(f"\n📋 第一筆資料範例:")
                        print(f"   類型: {type(data[0])}")
                        print(f"   內容: {data[0]}")
                        
                        # 檢查是否為字典
                        if isinstance(data[0], dict):
                            print(f"   鍵值: {list(data[0].keys())}")
                        
                        # 顯示前3筆資料
                        print(f"\n📋 前3筆資料:")
                        for i in range(min(3, len(data))):
                            print(f"   [{i}]: {data[i]}")
                        
                        # 尋找台積電資料
                        print(f"\n🔍 尋找台積電 (2330) 資料:")
                        found_tsmc = False
                        for item in data:
                            if isinstance(item, dict):
                                # 檢查各種可能的鍵值
                                code_keys = ['Code', 'code', '證券代號', 'symbol']
                                for key in code_keys:
                                    if key in item and str(item[key]) == '2330':
                                        print(f"   ✅ 找到台積電資料: {item}")
                                        found_tsmc = True
                                        break
                                if found_tsmc:
                                    break
                        
                        if not found_tsmc:
                            print("   ❌ 未找到台積電資料")
                    
                    elif isinstance(data, dict):
                        print(f"\n📋 字典資料鍵值:")
                        print(f"   鍵值: {list(data.keys())}")
                        for key in list(data.keys())[:3]:  # 顯示前3個鍵值的內容
                            print(f"   {key}: {data[key]}")
                    
                    else:
                        print(f"\n📋 未知資料格式: {data}")
                
                else:
                    print(f"❌ API 回應失敗，狀態碼: {response.status}")
                    content = await response.text()
                    print(f"   回應內容: {content[:500]}...")
                    
        except Exception as e:
            print(f"❌ API 請求失敗: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_twse_api())