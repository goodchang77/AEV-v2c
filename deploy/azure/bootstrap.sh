#!/usr/bin/env bash
# Azure VM 首次初始化（在 VM 上以登入使用者執行一次；Terraform 佈建者 cloud-init 已做過）
# 用途：從 Docker 官方「已簽章」APT 套件庫安裝 Docker Engine + compose plugin，並設定防火牆。
# 安全：不使用 `curl https://get.docker.com | sudo sh`（未驗證內容直接交給 root shell）。
set -euo pipefail

DOCKER_KEY_FPR="9DC858229FC7DD38854AE2D88D81803C0EBFCD88" # Docker 官方 APT 簽章金鑰指紋

echo "==> 安裝前置套件"
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

echo "==> 下載並驗證 Docker 官方 APT 金鑰"
sudo install -m 0755 -d /etc/apt/keyrings
tmp_key="$(mktemp)"
trap 'rm -f "$tmp_key"' EXIT
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o "$tmp_key"
if ! gpg --show-keys --with-colons "$tmp_key" | grep -q "^fpr:::::::::${DOCKER_KEY_FPR}:"; then
  echo "❌ Docker APT 金鑰指紋不符，中止安裝" >&2
  exit 1
fi
sudo install -m 0644 "$tmp_key" /etc/apt/keyrings/docker.asc

echo "==> 加入 Docker APT 套件庫（signed-by 限定金鑰）"
# shellcheck disable=SC1091
codename="$(. /etc/os-release && echo "$VERSION_CODENAME")"
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${codename} stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

echo "==> 安裝 Docker 與 compose plugin"
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker

# ⚠️ docker 群組成員等同 root 權限（可掛載 host 檔案系統、啟動特權容器），只加入可信任的管理者。
sudo usermod -aG docker "$USER"

echo "==> 設定本機防火牆"
# 只放行 SSH（與選用的 443 TLS 反向代理）。API 只綁 127.0.0.1:8000，不需也不應放行 8000。
# 注意：Docker 發布的 port 會繞過 ufw，因此 compose 內已將 API 綁在 127.0.0.1。
sudo ufw allow OpenSSH
if [ "${ALLOW_HTTPS:-0}" = "1" ]; then
  sudo ufw allow 443/tcp
fi
sudo ufw --force enable

echo "==> 完成"
echo "請重新登入讓 docker 群組生效，然後回到本機執行 deploy.sh。"
echo "提醒：API 只在 VM 的 127.0.0.1:8000；對外請設 TLS 反向代理（443），或用 SSH tunnel："
echo "  ssh -N -L 8000:127.0.0.1:8000 ${USER}@<VM_IP>"
