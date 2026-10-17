# =============================================================================
# 輸出值
# =============================================================================

output "vm_public_ip" {
  description = "VM 公用 IP（deploy.sh 用這個 IP）"
  value       = azurerm_public_ip.pip.ip_address
}

output "ssh_command" {
  description = "SSH 連線指令（只允許 ssh_source_cidr 來源）"
  value       = "ssh ${var.admin_username}@${azurerm_public_ip.pip.ip_address}"
}

output "ssh_tunnel_command" {
  description = "API 只綁 VM 的 127.0.0.1:8000；用此 SSH tunnel 後在本機開 http://127.0.0.1:8000"
  value       = "ssh -N -L 8000:127.0.0.1:8000 ${var.admin_username}@${azurerm_public_ip.pip.ip_address}"
}

output "app_url" {
  description = "對外網址：需在 VM 上設定 TLS 反向代理（443 → 127.0.0.1:8000）並把網域指到此 IP"
  value       = length(var.https_source_cidrs) > 0 ? "https://<your-domain>  (DNS A record -> ${azurerm_public_ip.pip.ip_address})" : "未開放 443；請使用 ssh_tunnel_command"
}
