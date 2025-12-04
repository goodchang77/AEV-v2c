#!/usr/bin/env python3
"""
測試執行腳本
Test Runner Script

用於執行不同類型的測試並生成報告
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, description):
    """執行命令並處理輸出"""
    print(f"\n{'='*60}")
    print(f"🔄 {description}")
    print(f"{'='*60}")
    print(f"執行命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ 成功完成")
        if result.stdout:
            print("輸出:")
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 失敗 (退出碼: {e.returncode})")
        if e.stdout:
            print("標準輸出:")
            print(e.stdout)
        if e.stderr:
            print("錯誤輸出:")
            print(e.stderr)
        return False
    except FileNotFoundError:
        print(f"❌ 命令未找到: {cmd[0]}")
        return False


def check_dependencies():
    """檢查依賴項"""
    print("🔍 檢查測試依賴項...")
    
    dependencies = [
        "pytest",
        "pytest-asyncio", 
        "pytest-cov",
        "httpx"  # for TestClient
    ]
    
    missing = []
    for dep in dependencies:
        try:
            __import__(dep.replace('-', '_'))
            print(f"✅ {dep}")
        except ImportError:
            print(f"❌ {dep} (未安裝)")
            missing.append(dep)
    
    if missing:
        print(f"\n缺少依賴項: {', '.join(missing)}")
        print("請執行: pip install " + " ".join(missing))
        return False
    
    return True


def run_unit_tests():
    """執行單元測試"""
    cmd = [
        "python", "-m", "pytest",
        "tests/test_pdf_processor.py",
        "-v",
        "--tb=short",
        "-m", "not slow"
    ]
    return run_command(cmd, "單元測試 - PDF處理器")


def run_api_tests():
    """執行API測試"""
    cmd = [
        "python", "-m", "pytest", 
        "tests/test_document_upload_api.py",
        "-v",
        "--tb=short"
    ]
    return run_command(cmd, "API測試 - 文件上傳端點")


def run_e2e_tests():
    """執行端到端測試"""
    cmd = [
        "python", "-m", "pytest",
        "tests/test_pdf_e2e.py",
        "-v", 
        "--tb=short",
        "-x"  # 第一個失敗就停止
    ]
    return run_command(cmd, "端到端測試 - 完整工作流程")


def run_all_tests():
    """執行所有測試"""
    cmd = [
        "python", "-m", "pytest",
        "tests/",
        "-v",
        "--tb=short"
    ]
    return run_command(cmd, "所有測試")


def run_tests_with_coverage():
    """執行測試並生成覆蓋率報告"""
    cmd = [
        "python", "-m", "pytest",
        "tests/",
        "--cov=src",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-report=xml",
        "-v"
    ]
    return run_command(cmd, "測試覆蓋率分析")


def run_specific_test():
    """執行特定測試"""
    if len(sys.argv) > 2:
        test_path = sys.argv[2]
        cmd = [
            "python", "-m", "pytest",
            test_path,
            "-v",
            "--tb=long"
        ]
        return run_command(cmd, f"特定測試 - {test_path}")
    else:
        print("❌ 請指定測試文件路徑")
        print("範例: python run_tests.py specific tests/test_pdf_processor.py::TestFinancialPDFProcessor::test_processor_initialization")
        return False


def lint_code():
    """代碼品質檢查"""
    print("\n🔍 代碼品質檢查")
    
    # 檢查是否安裝了linting工具
    linters = ["black", "isort", "flake8"]
    available_linters = []
    
    for linter in linters:
        try:
            subprocess.run([linter, "--version"], capture_output=True, check=True)
            available_linters.append(linter)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"⚠️  {linter} 未安裝，跳過檢查")
    
    success = True
    
    # Black 格式化檢查
    if "black" in available_linters:
        success &= run_command(
            ["black", "--check", "--diff", "src/", "tests/"],
            "Black 代碼格式檢查"
        )
    
    # isort 導入排序檢查  
    if "isort" in available_linters:
        success &= run_command(
            ["isort", "--check-only", "--diff", "src/", "tests/"],
            "isort 導入排序檢查"
        )
    
    # Flake8 代碼風格檢查
    if "flake8" in available_linters:
        success &= run_command(
            ["flake8", "src/", "tests/", "--max-line-length=100"],
            "Flake8 代碼風格檢查"
        )
    
    return success


def clean_test_artifacts():
    """清理測試產生的文件"""
    print("🧹 清理測試產生的文件...")
    
    artifacts = [
        ".pytest_cache",
        "htmlcov",
        "coverage.xml",
        ".coverage",
        "__pycache__"
    ]
    
    for artifact in artifacts:
        path = Path(artifact)
        if path.exists():
            if path.is_dir():
                import shutil
                shutil.rmtree(path)
                print(f"🗑️  刪除目錄: {artifact}")
            else:
                path.unlink()
                print(f"🗑️  刪除文件: {artifact}")
    
    # 清理Python緩存文件
    for pycache in Path(".").rglob("__pycache__"):
        if pycache.is_dir():
            import shutil
            shutil.rmtree(pycache)
    
    print("✅ 清理完成")


def show_help():
    """顯示幫助信息"""
    help_text = """
📋 測試執行腳本使用說明

用法: python run_tests.py [命令] [選項]

可用命令:
  unit        執行單元測試
  api         執行API測試  
  e2e         執行端到端測試
  all         執行所有測試
  coverage    執行測試並生成覆蓋率報告
  specific    執行特定測試 (需要指定測試路徑)
  lint        代碼品質檢查
  clean       清理測試產生的文件
  help        顯示此幫助信息

範例:
  python run_tests.py unit
  python run_tests.py coverage
  python run_tests.py specific tests/test_pdf_processor.py
  python run_tests.py lint
  
注意:
  - 首次執行前請確保已安裝測試依賴: pip install pytest pytest-asyncio pytest-cov httpx
  - 代碼品質檢查需要安裝: pip install black isort flake8
  - 覆蓋率報告將生成在 htmlcov/ 目錄中
    """
    print(help_text)


def main():
    """主函數"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    print("🧪 財務分析系統 - PDF處理測試套件")
    print(f"Python 版本: {sys.version}")
    print(f"工作目錄: {os.getcwd()}")
    
    # 設置環境變數
    os.environ["PYTHONPATH"] = os.getcwd()
    
    if command == "help":
        show_help()
        return
    
    if command == "clean":
        clean_test_artifacts()
        return
        
    if command == "lint":
        success = lint_code()
        sys.exit(0 if success else 1)
    
    # 檢查依賴項
    if not check_dependencies():
        sys.exit(1)
    
    success = True
    
    if command == "unit":
        success = run_unit_tests()
    elif command == "api":
        success = run_api_tests()
    elif command == "e2e":
        success = run_e2e_tests()
    elif command == "all":
        success = run_all_tests()
    elif command == "coverage":
        success = run_tests_with_coverage()
    elif command == "specific":
        success = run_specific_test()
    else:
        print(f"❌ 未知命令: {command}")
        show_help()
        sys.exit(1)
    
    print(f"\n{'='*60}")
    if success:
        print("🎉 測試執行完成")
        sys.exit(0)
    else:
        print("💥 測試執行失敗")
        sys.exit(1)


if __name__ == "__main__":
    main()