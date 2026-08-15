#!/usr/bin/env bash
# Azure VM 首次初始化（在 VM 上以登入使用者執行一次）
# 用途：安裝 Docker、設定防火牆。
set -euo pipefail

echo "==> 安裝 Docker 與 compose plugin"
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"

echo "==> 設定本機防火牆（Azure NSG 需另於入口放行 port）"
sudo ufw allow OpenSSH || true
sudo ufw allow 8000/tcp || true
sudo ufw --force enable || true

echo "==> 完成"
echo "請重新登入讓 docker 群組生效，然後回到本機執行 deploy.sh。"
echo "提醒：在 Azure 入口的 VM「網路」→「輸入連接埠規則(NSG)」也要放行 8000（或之後改用 80/443 + Nginx/TLS）。"
