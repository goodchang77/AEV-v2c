# =============================================================================
# 輸出值
# =============================================================================

output "vm_public_ip" {
  description = "VM 公用 IP（deploy.sh 用這個 IP）"
  value       = azurerm_public_ip.pip.ip_address
}

output "ssh_command" {
  description = "SSH 連線指令"
  value       = "ssh ${var.admin_username}@${azurerm_public_ip.pip.ip_address}"
}

output "app_url" {
  description = "應用程式網址"
  value       = "http://${azurerm_public_ip.pip.ip_address}:8000"
}
