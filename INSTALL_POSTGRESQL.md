# PostgreSQL 安裝指南 (WSL/Ubuntu)

## 📋 安裝 PostgreSQL

### 步驟 1: 更新套件列表

```bash
sudo apt update
```

### 步驟 2: 安裝 PostgreSQL

```bash
sudo apt install postgresql postgresql-contrib -y
```

這會安裝：
- `postgresql` - PostgreSQL 資料庫伺服器
- `postgresql-contrib` - 額外的工具和擴展

### 步驟 3: 檢查 PostgreSQL 版本

```bash
psql --version
```

應該顯示類似：`psql (PostgreSQL) 14.x` 或更高版本

## 🚀 啟動 PostgreSQL 服務

### 在 WSL 中啟動 PostgreSQL

```bash
sudo service postgresql start
```

### 檢查服務狀態

```bash
sudo service postgresql status
```

應該看到：`* postgresql is running`

### 設定開機自動啟動 (可選)

在 WSL 中，每次重新啟動 WSL 時需要手動啟動 PostgreSQL。可以在 `~/.bashrc` 中添加：

```bash
echo "# 自動啟動 PostgreSQL" >> ~/.bashrc
echo "sudo service postgresql start > /dev/null 2>&1" >> ~/.bashrc
```

## 🔐 設定 PostgreSQL

### 步驟 1: 切換到 postgres 用戶

```bash
sudo -i -u postgres
```

### 步驟 2: 進入 PostgreSQL 命令行

```bash
psql
```

### 步驟 3: 設定 postgres 用戶密碼

在 psql 提示符中執行：

```sql
ALTER USER postgres WITH PASSWORD 'dev_password_2024';
```

### 步驟 4: 創建資料庫

```sql
CREATE DATABASE financial_analysis;
CREATE DATABASE timeseries_financial;
```

### 步驟 5: 驗證資料庫已創建

```sql
\l
```

應該看到兩個資料庫列在清單中。

### 步驟 6: 退出 psql

```sql
\q
```

### 步驟 7: 退出 postgres 用戶

```bash
exit
```

## 🔧 配置遠端連線 (如需要)

### 編輯 postgresql.conf

```bash
sudo nano /etc/postgresql/*/main/postgresql.conf
```

找到並修改：
```conf
listen_addresses = 'localhost'  # 或 '*' 允許所有連線
```

### 編輯 pg_hba.conf

```bash
sudo nano /etc/postgresql/*/main/pg_hba.conf
```

添加以下行（在檔案末尾）：
```conf
# TYPE  DATABASE        USER            ADDRESS                 METHOD
host    all             all             127.0.0.1/32            md5
host    all             all             ::1/128                 md5
```

### 重啟 PostgreSQL

```bash
sudo service postgresql restart
```

## ✅ 測試連線

### 方法 1: 使用 psql

```bash
psql -h localhost -U postgres -d financial_analysis
```

輸入密碼：`dev_password_2024`

如果成功連接，您會看到 `financial_analysis=#` 提示符。

### 方法 2: 使用 Python 測試

創建測試腳本：

```bash
python << 'EOF'
import asyncpg
import asyncio

async def test_connection():
    try:
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='dev_password_2024',
            database='financial_analysis'
        )
        print("✓ 資料庫連線成功！")

        # 測試查詢
        version = await conn.fetchval('SELECT version()')
        print(f"✓ PostgreSQL 版本: {version[:50]}...")

        await conn.close()
        return True
    except Exception as e:
        print(f"✗ 連線失敗: {e}")
        return False

asyncio.run(test_connection())
EOF
```

## 🛠️ 常用 PostgreSQL 命令

### 服務管理

```bash
# 啟動服務
sudo service postgresql start

# 停止服務
sudo service postgresql stop

# 重啟服務
sudo service postgresql restart

# 檢查狀態
sudo service postgresql status
```

### 資料庫操作

```bash
# 連接到資料庫
psql -h localhost -U postgres -d financial_analysis

# 列出所有資料庫
psql -h localhost -U postgres -c "\l"

# 列出所有表格
psql -h localhost -U postgres -d financial_analysis -c "\dt"
```

### psql 內部命令

在 psql 提示符中：

```sql
\l              -- 列出所有資料庫
\c database     -- 連接到指定資料庫
\dt             -- 列出當前資料庫的所有表格
\d table_name   -- 顯示表格結構
\du             -- 列出所有用戶
\q              -- 退出 psql
```

## 🔍 故障排除

### 問題 1: 無法連接到伺服器

**錯誤訊息**: `could not connect to server: Connection refused`

**解決方案**:
```bash
# 確認服務正在運行
sudo service postgresql status

# 如果未運行，啟動它
sudo service postgresql start
```

### 問題 2: 密碼認證失敗

**錯誤訊息**: `password authentication failed for user "postgres"`

**解決方案**:
```bash
# 重設 postgres 用戶密碼
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'dev_password_2024';"
```

### 問題 3: 資料庫不存在

**錯誤訊息**: `database "financial_analysis" does not exist`

**解決方案**:
```bash
# 創建資料庫
sudo -u postgres psql -c "CREATE DATABASE financial_analysis;"
sudo -u postgres psql -c "CREATE DATABASE timeseries_financial;"
```

### 問題 4: 端口被佔用

**錯誤訊息**: `could not bind IPv4 address "127.0.0.1": Address already in use`

**解決方案**:
```bash
# 檢查哪個進程佔用端口 5432
sudo lsof -i :5432

# 終止舊的 PostgreSQL 進程
sudo killall postgres

# 重新啟動服務
sudo service postgresql start
```

## 📊 驗證設定

執行完整驗證：

```bash
#!/bin/bash
echo "=== PostgreSQL 安裝驗證 ==="
echo ""

# 1. 檢查安裝
echo "1. 檢查 PostgreSQL 是否安裝:"
which psql && echo "✓ psql 已安裝" || echo "✗ psql 未安裝"
echo ""

# 2. 檢查服務
echo "2. 檢查服務狀態:"
sudo service postgresql status | grep -q "is running" && echo "✓ PostgreSQL 正在運行" || echo "✗ PostgreSQL 未運行"
echo ""

# 3. 檢查連線
echo "3. 測試資料庫連線:"
PGPASSWORD=dev_password_2024 psql -h localhost -U postgres -d financial_analysis -c "SELECT 1;" > /dev/null 2>&1 && echo "✓ 連線成功" || echo "✗ 連線失敗"
echo ""

# 4. 檢查資料庫
echo "4. 檢查資料庫是否存在:"
PGPASSWORD=dev_password_2024 psql -h localhost -U postgres -lqt | cut -d \| -f 1 | grep -qw financial_analysis && echo "✓ financial_analysis 存在" || echo "✗ financial_analysis 不存在"
PGPASSWORD=dev_password_2024 psql -h localhost -U postgres -lqt | cut -d \| -f 1 | grep -qw timeseries_financial && echo "✓ timeseries_financial 存在" || echo "✗ timeseries_financial 不存在"
echo ""

echo "=== 驗證完成 ==="
```

保存為 `check_postgresql.sh` 並執行：

```bash
chmod +x check_postgresql.sh
./check_postgresql.sh
```

## 🚀 安裝後啟動應用程式

完成 PostgreSQL 安裝後：

```bash
# 1. 確認 PostgreSQL 正在運行
sudo service postgresql status

# 2. 切換到專案目錄
cd /mnt/d/Project/AEV-v2c

# 3. 啟動應用程式
./start_server.sh
```

## 📝 .env 檔案配置

確認您的 `.env` 檔案包含正確的資料庫設定：

```env
DATABASE_URL=postgresql://postgres:dev_password_2024@localhost:5432/financial_analysis
TIMESERIES_DATABASE_URL=postgresql://postgres:dev_password_2024@localhost:5433/timeseries_financial
```

**注意**: 如果只有一個 PostgreSQL 實例，兩個資料庫可以使用相同的端口 5432。

## 🔐 安全性建議

### 生產環境

1. **使用強密碼**:
   ```sql
   ALTER USER postgres WITH PASSWORD 'your_strong_random_password_here';
   ```

2. **創建專用用戶**:
   ```sql
   CREATE USER financial_user WITH PASSWORD 'secure_password';
   GRANT ALL PRIVILEGES ON DATABASE financial_analysis TO financial_user;
   ```

3. **限制連線**:
   編輯 `pg_hba.conf`，只允許特定 IP 連線

4. **啟用 SSL**:
   ```conf
   ssl = on
   ssl_cert_file = '/path/to/server.crt'
   ssl_key_file = '/path/to/server.key'
   ```

## 📚 進階配置

### 效能調整

編輯 `postgresql.conf`:

```conf
# 記憶體設定
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 16MB

# 連線設定
max_connections = 100

# WAL 設定
wal_buffers = 16MB
checkpoint_completion_target = 0.9
```

### 安裝 TimescaleDB (時序資料庫擴展)

如果需要處理時序資料：

```bash
# 添加 TimescaleDB 儲存庫
sudo add-apt-repository ppa:timescale/timescaledb-ppa
sudo apt update

# 安裝 TimescaleDB
sudo apt install timescaledb-2-postgresql-14

# 啟用擴展
sudo -u postgres psql -d timeseries_financial -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"
```

## 🆘 需要更多幫助？

- PostgreSQL 官方文件: https://www.postgresql.org/docs/
- Ubuntu PostgreSQL 安裝指南: https://help.ubuntu.com/community/PostgreSQL
- TimescaleDB 文件: https://docs.timescale.com/

---

**最後更新**: 2025-12-04
**適用於**: WSL/Ubuntu 20.04+
