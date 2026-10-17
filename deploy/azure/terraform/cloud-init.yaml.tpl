#cloud-config
# 首次開機自動安裝 Docker Engine + compose plugin
# 安全：不再使用 `curl https://get.docker.com | sh`（把未驗證的下載內容直接交給 root shell）。
# 改用 Docker 官方「已簽章」APT 套件庫：金鑰放 /etc/apt/keyrings，並以 signed-by 限定只信任該金鑰，
# 安裝前先比對 Docker 官方公布的金鑰指紋。
package_update: true

packages:
  - ca-certificates
  - curl
  - gnupg
  - rsync

runcmd:
  - install -m 0755 -d /etc/apt/keyrings
  - curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  - chmod a+r /etc/apt/keyrings/docker.asc
  # Docker 官方 APT 簽章金鑰指紋：9DC8 5822 9FC7 DD38 854A E2D8 8D81 803C 0EBF CD88
  # 指紋不符時刪除金鑰 → signed-by 找不到金鑰 → apt 不會安裝來源不明的套件
  - [sh, -c, "gpg --show-keys --with-colons /etc/apt/keyrings/docker.asc | grep -q '^fpr:::::::::9DC858229FC7DD38854AE2D88D81803C0EBFCD88:' || { rm -f /etc/apt/keyrings/docker.asc; echo 'Docker APT key fingerprint mismatch; key removed, docker will NOT be installed' >&2; exit 1; }"]
  - [sh, -c, "echo \"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable\" > /etc/apt/sources.list.d/docker.list"]
  - apt-get update
  - DEBIAN_FRONTEND=noninteractive apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  # 將登入使用者加入 docker 群組，免 sudo 跑 docker。
  # ⚠️ docker 群組成員等同 root 權限（可掛載 host 檔案系統、啟動特權容器），只給可信任的管理者。
  - usermod -aG docker ${admin_username}
  - systemctl enable --now docker
  # 整行加引號：避免 YAML 把 "cloud-init: ..." 誤解析成 mapping（原本的潛在錯誤）
  - 'echo "cloud-init: docker installed" > /var/log/cloud-init-done.log'
