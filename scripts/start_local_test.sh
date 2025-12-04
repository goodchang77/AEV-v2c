#!/bin/bash
# 本地測試環境快速啟動腳本
# Local Testing Environment Quick Start Script

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 專案根目錄
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}🚀 財務分析系統 - 本地測試環境啟動腳本${NC}"
echo -e "${BLUE}=================================================${NC}"

# 檢查 Docker 和 Docker Compose
check_dependencies() {
    echo -e "\n${YELLOW}📋 檢查相依性...${NC}"
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker 未安裝${NC}"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}❌ Docker Compose 未安裝${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ 相依性檢查通過${NC}"
}

# 清理舊的容器
cleanup_old_containers() {
    echo -e "\n${YELLOW}🧹 清理舊的容器...${NC}"
    
    if [ -f "docker-compose.local-test.yml" ]; then
        docker-compose -f docker-compose.local-test.yml down --volumes --remove-orphans 2>/dev/null || true
    fi
    
    echo -e "${GREEN}✅ 舊容器清理完成${NC}"
}

# 建構應用程式映像
build_app_image() {
    echo -e "\n${YELLOW}🔨 建構應用程式映像...${NC}"
    
    if [ -f "Dockerfile" ]; then
        docker build -t financial-app-local:latest . || {
            echo -e "${RED}❌ 映像建構失敗${NC}"
            exit 1
        }
        echo -e "${GREEN}✅ 映像建構成功${NC}"
    else
        echo -e "${YELLOW}⚠️  Dockerfile 不存在，跳過映像建構${NC}"
    fi
}

# 啟動服務
start_services() {
    echo -e "\n${YELLOW}🚀 啟動本地測試服務...${NC}"
    
    if [ ! -f "docker-compose.local-test.yml" ]; then
        echo -e "${RED}❌ docker-compose.local-test.yml 不存在${NC}"
        exit 1
    fi
    
    # 設定環境變數檔案
    if [ -f ".env.local" ]; then
        export $(cat .env.local | grep -v '^#' | xargs)
        echo -e "${GREEN}✅ 載入本地環境變數${NC}"
    fi
    
    # 啟動服務
    docker-compose -f docker-compose.local-test.yml up -d
    
    echo -e "${GREEN}✅ 服務啟動命令執行完成${NC}"
}

# 等待服務準備就緒
wait_for_services() {
    echo -e "\n${YELLOW}⏳ 等待服務準備就緒...${NC}"
    
    # 等待 PostgreSQL
    echo -e "${YELLOW}  📊 等待 PostgreSQL...${NC}"
    for i in {1..30}; do
        if docker exec financial_postgres_local pg_isready -U postgres -d financial_analysis >/dev/null 2>&1; then
            echo -e "${GREEN}  ✅ PostgreSQL 已準備就緒${NC}"
            break
        fi
        if [ $i -eq 30 ]; then
            echo -e "${RED}  ❌ PostgreSQL 啟動超時${NC}"
            exit 1
        fi
        sleep 2
    done
    
    # 等待 Redis
    echo -e "${YELLOW}  📊 等待 Redis...${NC}"
    for i in {1..30}; do
        if docker exec financial_redis_local redis-cli -a dev_redis_2024 ping >/dev/null 2>&1; then
            echo -e "${GREEN}  ✅ Redis 已準備就緒${NC}"
            break
        fi
        if [ $i -eq 30 ]; then
            echo -e "${RED}  ❌ Redis 啟動超時${NC}"
            exit 1
        fi
        sleep 2
    done
    
    # 等待 TimescaleDB
    echo -e "${YELLOW}  📊 等待 TimescaleDB...${NC}"
    for i in {1..30}; do
        if docker exec financial_timescale_local pg_isready -U postgres -d timeseries_financial >/dev/null 2>&1; then
            echo -e "${GREEN}  ✅ TimescaleDB 已準備就緒${NC}"
            break
        fi
        if [ $i -eq 30 ]; then
            echo -e "${RED}  ❌ TimescaleDB 啟動超時${NC}"
            exit 1
        fi
        sleep 2
    done
    
    # 等待應用程式
    if docker ps | grep -q financial_app_local; then
        echo -e "${YELLOW}  🔧 等待應用程式...${NC}"
        for i in {1..60}; do
            if curl -f http://localhost:8000/health >/dev/null 2>&1; then
                echo -e "${GREEN}  ✅ 應用程式已準備就緒${NC}"
                break
            fi
            if [ $i -eq 60 ]; then
                echo -e "${RED}  ❌ 應用程式啟動超時${NC}"
                show_logs
                exit 1
            fi
            sleep 2
        done
    fi
}

# 初始化資料庫
initialize_databases() {
    echo -e "\n${YELLOW}📊 初始化資料庫...${NC}"
    
    # 初始化 PostgreSQL
    echo -e "${YELLOW}  📊 初始化 PostgreSQL...${NC}"
    docker exec financial_postgres_local psql -U postgres -d financial_analysis -c "
        CREATE TABLE IF NOT EXISTS companies (
            company_id VARCHAR(10) PRIMARY KEY,
            company_name VARCHAR(100) NOT NULL,
            industry_code VARCHAR(10),
            market_type VARCHAR(20),
            listing_date DATE,
            capital_amount DECIMAL(15,2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        INSERT INTO companies (company_id, company_name, industry_code, market_type) 
        VALUES 
            ('2330', '台積電', 'SEMI', '上市'),
            ('2317', '鴻海', 'ELEC', '上市'),
            ('1301', '台塑', 'CHEM', '上市'),
            ('1216', '統一', 'FOOD', '上市'),
            ('2454', '聯發科', 'SEMI', '上市')
        ON CONFLICT (company_id) DO NOTHING;
    " >/dev/null 2>&1 || true
    
    # 初始化 TimescaleDB
    echo -e "${YELLOW}  📈 初始化 TimescaleDB...${NC}"
    docker exec financial_timescale_local psql -U postgres -d timeseries_financial -c "
        CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
        
        CREATE TABLE IF NOT EXISTS stock_prices (
            time TIMESTAMPTZ NOT NULL,
            company_id VARCHAR(10) NOT NULL,
            open_price DECIMAL(8,2),
            high_price DECIMAL(8,2),
            low_price DECIMAL(8,2),
            close_price DECIMAL(8,2),
            volume BIGINT,
            adj_close DECIMAL(8,2)
        );
    " >/dev/null 2>&1 || true
    
    # 嘗試建立 Hypertable
    docker exec financial_timescale_local psql -U postgres -d timeseries_financial -c "
        SELECT create_hypertable('stock_prices', 'time', if_not_exists => TRUE);
        CREATE INDEX IF NOT EXISTS idx_stock_prices_company_time 
        ON stock_prices (company_id, time DESC);
    " >/dev/null 2>&1 || true
    
    echo -e "${GREEN}✅ 資料庫初始化完成${NC}"
}

# 顯示服務狀態
show_status() {
    echo -e "\n${BLUE}📋 服務狀態檢查${NC}"
    echo -e "${BLUE}==================${NC}"
    
    docker-compose -f docker-compose.local-test.yml ps
}

# 顯示日誌
show_logs() {
    echo -e "\n${YELLOW}📝 應用程式日誌（最近 20 行）:${NC}"
    docker-compose -f docker-compose.local-test.yml logs --tail=20 app 2>/dev/null || true
}

# 測試服務連線
test_services() {
    echo -e "\n${YELLOW}🧪 測試服務連線...${NC}"
    
    # 測試健康檢查端點
    if curl -f http://localhost:8000/health >/dev/null 2>&1; then
        echo -e "${GREEN}✅ 應用程式健康檢查通過${NC}"
    else
        echo -e "${RED}❌ 應用程式健康檢查失敗${NC}"
    fi
    
    # 測試 API 文檔
    if curl -f http://localhost:8000/docs >/dev/null 2>&1; then
        echo -e "${GREEN}✅ API 文檔可訪問${NC}"
    else
        echo -e "${YELLOW}⚠️  API 文檔無法訪問${NC}"
    fi
    
    # 測試資料庫連線
    if docker exec financial_postgres_local pg_isready -U postgres -d financial_analysis >/dev/null 2>&1; then
        echo -e "${GREEN}✅ PostgreSQL 連線正常${NC}"
    else
        echo -e "${RED}❌ PostgreSQL 連線異常${NC}"
    fi
    
    # 測試 Redis 連線
    if docker exec financial_redis_local redis-cli -a dev_redis_2024 ping >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Redis 連線正常${NC}"
    else
        echo -e "${RED}❌ Redis 連線異常${NC}"
    fi
}

# 顯示訪問資訊
show_access_info() {
    echo -e "\n${GREEN}🎉 本地測試環境啟動完成！${NC}"
    echo -e "${BLUE}================================${NC}"
    
    echo -e "\n${YELLOW}📋 服務訪問資訊:${NC}"
    echo -e "  🔗 主應用程式: ${GREEN}http://localhost:8000${NC}"
    echo -e "  🔗 API 文檔:   ${GREEN}http://localhost:8000/docs${NC}"
    echo -e "  🔗 健康檢查:   ${GREEN}http://localhost:8000/health${NC}"
    echo -e "  🔗 pgAdmin:    ${GREEN}http://localhost:5050${NC}"
    echo -e "  🔗 Redis Insight: ${GREEN}http://localhost:8001${NC}"
    echo -e "  🔗 Adminer:    ${GREEN}http://localhost:8080${NC}"
    
    echo -e "\n${YELLOW}🔑 資料庫連線資訊:${NC}"
    echo -e "  PostgreSQL: ${GREEN}localhost:5432${NC} (postgres / dev_password_2024)"
    echo -e "  TimescaleDB: ${GREEN}localhost:5433${NC} (postgres / dev_password_2024)"
    echo -e "  Redis: ${GREEN}localhost:6379${NC} (密碼: dev_redis_2024)"
    
    echo -e "\n${YELLOW}🛠️  管理指令:${NC}"
    echo -e "  查看日誌: ${GREEN}docker-compose -f docker-compose.local-test.yml logs -f${NC}"
    echo -e "  停止服務: ${GREEN}docker-compose -f docker-compose.local-test.yml down${NC}"
    echo -e "  重啟服務: ${GREEN}docker-compose -f docker-compose.local-test.yml restart${NC}"
    echo -e "  清理所有: ${GREEN}docker-compose -f docker-compose.local-test.yml down -v${NC}"
}

# 主要執行流程
main() {
    check_dependencies
    cleanup_old_containers
    build_app_image
    start_services
    wait_for_services
    initialize_databases
    show_status
    test_services
    show_access_info
}

# 錯誤處理
handle_error() {
    echo -e "\n${RED}❌ 腳本執行失敗！${NC}"
    echo -e "${YELLOW}📝 查看詳細日誌:${NC}"
    show_logs
    exit 1
}

# 設定錯誤陷阱
trap handle_error ERR

# 執行主要流程
main "$@"