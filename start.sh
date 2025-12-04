#!/bin/bash
# 財務分析系統啟動腳本
# Financial Analysis System Startup Script

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日誌函數
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 檢查必要檔案
check_requirements() {
    log_step "檢查必要檔案..."
    
    if [ ! -f "docker-compose.dev.yml" ]; then
        log_error "docker-compose.dev.yml 不存在"
        exit 1
    fi
    
    if [ ! -f ".env.example" ]; then
        log_error ".env.example 不存在"
        exit 1
    fi
    
    log_info "檔案檢查完成"
}

# 創建環境變數檔案
setup_env() {
    log_step "設定環境變數..."
    
    if [ ! -f ".env" ]; then
        log_info "複製 .env.example 到 .env"
        cp .env.example .env
    else
        log_warn ".env 檔案已存在，跳過複製"
    fi
}

# 創建必要目錄
create_directories() {
    log_step "創建必要目錄..."
    
    directories=(
        "logs"
        "uploads" 
        "backups"
        "data"
    )
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_info "創建目錄: $dir"
        fi
    done
}

# 啟動資料庫服務
start_databases() {
    log_step "啟動資料庫服務..."
    
    # 檢查 Docker 是否運行
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker 未運行，請先啟動 Docker"
        exit 1
    fi
    
    # 啟動資料庫容器
    log_info "啟動 PostgreSQL, TimescaleDB, Redis..."
    docker-compose -f docker-compose.dev.yml up -d postgres timescaledb redis
    
    # 等待資料庫啟動
    log_info "等待資料庫服務啟動..."
    sleep 10
    
    # 檢查服務狀態
    if docker-compose -f docker-compose.dev.yml ps postgres | grep -q "Up"; then
        log_info "PostgreSQL 啟動成功"
    else
        log_error "PostgreSQL 啟動失敗"
        exit 1
    fi
    
    if docker-compose -f docker-compose.dev.yml ps timescaledb | grep -q "Up"; then
        log_info "TimescaleDB 啟動成功"
    else
        log_error "TimescaleDB 啟動失敗"
        exit 1
    fi
    
    if docker-compose -f docker-compose.dev.yml ps redis | grep -q "Up"; then
        log_info "Redis 啟動成功"
    else
        log_error "Redis 啟動失敗"
        exit 1
    fi
}

# 啟動 pgAdmin
start_pgadmin() {
    log_step "啟動 pgAdmin..."
    docker-compose -f docker-compose.dev.yml up -d pgadmin
    
    if docker-compose -f docker-compose.dev.yml ps pgadmin | grep -q "Up"; then
        log_info "pgAdmin 啟動成功，訪問地址: http://localhost:5050"
        log_info "登入帳號: admin@financial.dev"
        log_info "登入密碼: admin123"
    else
        log_warn "pgAdmin 啟動失敗"
    fi
}

# 初始化資料庫
init_database() {
    log_step "檢查資料庫初始化..."
    
    # 等待資料庫完全啟動
    sleep 5
    
    # 檢查是否已初始化
    if docker exec financial_postgres psql -U postgres -d financial_analysis -c "SELECT 1 FROM companies LIMIT 1;" > /dev/null 2>&1; then
        log_info "資料庫已初始化，跳過初始化步驟"
    else
        log_info "資料庫需要初始化"
        # 這裡可以加入資料庫初始化邏輯
    fi
}

# 安裝 Python 依賴
install_dependencies() {
    log_step "安裝 Python 依賴..."
    
    if [ ! -d "venv" ]; then
        log_info "創建 Python 虛擬環境..."
        python3 -m venv venv
    fi
    
    # 啟動虛擬環境
    source venv/bin/activate
    
    # 升級 pip
    pip install --upgrade pip
    
    # 安裝依賴
    if [ -f "requirements.txt" ]; then
        log_info "安裝 requirements.txt 中的依賴..."
        pip install -r requirements.txt
    else
        log_error "requirements.txt 不存在"
        exit 1
    fi
    
    log_info "Python 依賴安裝完成"
}

# 啟動 FastAPI 應用
start_api() {
    log_step "啟動 FastAPI 應用..."
    
    # 啟動虛擬環境
    source venv/bin/activate
    
    # 設定環境變數
    export PYTHONPATH="${PYTHONPATH}:$(pwd)"
    
    # 啟動應用
    log_info "啟動應用在 http://localhost:8000"
    log_info "API 文檔: http://localhost:8000/docs"
    log_info "健康檢查: http://localhost:8000/health"
    
    uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
}

# 顯示使用說明
show_help() {
    echo "財務分析系統啟動腳本"
    echo ""
    echo "使用方法:"
    echo "  $0 [選項]"
    echo ""
    echo "選項:"
    echo "  start     - 啟動完整系統 (預設)"
    echo "  db        - 僅啟動資料庫服務"
    echo "  api       - 僅啟動 API 服務"
    echo "  stop      - 停止所有服務"
    echo "  restart   - 重新啟動所有服務"
    echo "  status    - 查看服務狀態"
    echo "  logs      - 查看服務日誌"
    echo "  help      - 顯示此說明"
    echo ""
}

# 停止服務
stop_services() {
    log_step "停止服務..."
    docker-compose -f docker-compose.dev.yml down
    log_info "所有服務已停止"
}

# 查看服務狀態
show_status() {
    log_step "服務狀態:"
    docker-compose -f docker-compose.dev.yml ps
}

# 查看日誌
show_logs() {
    log_step "查看服務日誌:"
    docker-compose -f docker-compose.dev.yml logs -f
}

# 主要執行邏輯
main() {
    case "${1:-start}" in
        "start")
            log_info "啟動財務分析系統..."
            check_requirements
            setup_env
            create_directories
            start_databases
            start_pgadmin
            init_database
            install_dependencies
            start_api
            ;;
        "db")
            log_info "啟動資料庫服務..."
            check_requirements
            setup_env
            start_databases
            start_pgadmin
            ;;
        "api")
            log_info "啟動 API 服務..."
            install_dependencies
            start_api
            ;;
        "stop")
            stop_services
            ;;
        "restart")
            stop_services
            sleep 2
            main start
            ;;
        "status")
            show_status
            ;;
        "logs")
            show_logs
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            log_error "未知選項: $1"
            show_help
            exit 1
            ;;
    esac
}

# 執行主函數
main "$@"