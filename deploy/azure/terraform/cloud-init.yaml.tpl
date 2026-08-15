#cloud-config
# 首次開機自動安裝 Docker + compose plugin
package_update: true

packages:
  - ca-certificates
  - curl
  - rsync

runcmd:
  # 安裝 Docker（官方一鍵腳本，含 docker compose plugin）
  - curl -fsSL https://get.docker.com | sh
  # 將登入使用者加入 docker 群組，免 sudo 跑 docker
  - usermod -aG docker ${admin_username}
  - systemctl enable --now docker
  - echo "cloud-init: docker installed" > /var/log/cloud-init-done.log
