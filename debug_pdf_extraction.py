#!/usr/bin/env python3
"""
PDF提取調試腳本
"""
import asyncio
import sys
import os
import re
from pathlib import Path
import io

sys.path.insert(0, str(Path(__file__).parent))

import pdfplumber
import fitz  # PyMuPDF
import PyPDF2

async def debug_pdf_extraction():
    """調試PDF提取過程"""
    print("🔍 調試PDF提取過程...")
    
    pdf_path = "/mnt/d/Project/AEV-v2c/testdata/NVDSA Q2FY25-CFO-Commentary.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"❌ 測試PDF文件不存在: {pdf_path}")
        return
    
    # 讀取PDF文件
    with open(pdf_path, 'rb') as f:
        pdf_content = f.read()
    
    print(f"📄 載入PDF文件: {os.path.basename(pdf_path)} ({len(pdf_content):,} bytes)")
    
    # 測試不同的PDF提取方法
    await test_pdfplumber(pdf_content)
    await test_pymupdf(pdf_content)
    await test_pypdf2(pdf_content)

async def test_pdfplumber(pdf_content):
    """測試pdfplumber提取"""
    print("\n🔧 測試 pdfplumber 提取...")
    
    try:
        with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
            print(f"   - 總頁數: {len(pdf.pages)}")
            
            for page_num, page in enumerate(pdf.pages[:2], 1):  # 只測試前2頁
                print(f"\n   📄 頁面 {page_num}:")
                
                # 提取文字
                page_text = page.extract_text() or ""
                print(f"      - 文字長度: {len(page_text)}")
                
                # 查找數字模式
                numbers = re.findall(r'[\d,]+\.?\d*', page_text)
                print(f"      - 找到數字: {len(numbers)} 個")
                if numbers:
                    print(f"        前10個: {numbers[:10]}")
                
                # 查找財務關鍵詞
                financial_keywords = ['Revenue', 'Income', 'Assets', 'Liabilities', 'Cash', 'Margin']
                for keyword in financial_keywords:
                    if keyword.lower() in page_text.lower():
                        print(f"        找到關鍵詞: {keyword}")
                
                # 提取表格
                tables = page.extract_tables()
                if tables:
                    print(f"      - 找到表格: {len(tables)} 個")
                    for i, table in enumerate(tables[:1]):  # 只看第一個表格
                        print(f"        表格 {i+1}: {len(table)} 行 x {len(table[0]) if table and table[0] else 0} 列")
                        if table and len(table) > 0:
                            print(f"        第一行: {table[0]}")
    
    except Exception as e:
        print(f"❌ pdfplumber 測試失敗: {e}")

async def test_pymupdf(pdf_content):
    """測試PyMuPDF提取"""
    print("\n🔧 測試 PyMuPDF 提取...")
    
    try:
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        print(f"   - 總頁數: {doc.page_count}")
        
        for page_num in range(min(2, doc.page_count)):  # 只測試前2頁
            page = doc.load_page(page_num)
            page_text = page.get_text()
            
            print(f"\n   📄 頁面 {page_num + 1}:")
            print(f"      - 文字長度: {len(page_text)}")
            
            # 查找數字模式
            numbers = re.findall(r'[\d,]+\.?\d*', page_text)
            print(f"      - 找到數字: {len(numbers)} 個")
            if numbers:
                print(f"        前10個: {numbers[:10]}")
                
            # 顯示部分文字內容
            lines = page_text.split('\n')[:10]
            print(f"      - 前10行文字:")
            for i, line in enumerate(lines, 1):
                if line.strip():
                    print(f"        {i}: {line.strip()[:100]}")
        
        doc.close()
        
    except Exception as e:
        print(f"❌ PyMuPDF 測試失敗: {e}")

async def test_pypdf2(pdf_content):
    """測試PyPDF2提取"""
    print("\n🔧 測試 PyPDF2 提取...")
    
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
        print(f"   - 總頁數: {len(pdf_reader.pages)}")
        
        for page_num, page in enumerate(pdf_reader.pages[:2], 1):  # 只測試前2頁
            page_text = page.extract_text()
            
            print(f"\n   📄 頁面 {page_num}:")
            print(f"      - 文字長度: {len(page_text)}")
            
            # 查找數字模式
            numbers = re.findall(r'[\d,]+\.?\d*', page_text)
            print(f"      - 找到數字: {len(numbers)} 個")
            if numbers:
                print(f"        前10個: {numbers[:10]}")
    
    except Exception as e:
        print(f"❌ PyPDF2 測試失敗: {e}")

if __name__ == "__main__":
    asyncio.run(debug_pdf_extraction())