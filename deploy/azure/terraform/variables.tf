# =============================================================================
# 變數定義
# =============================================================================

variable "project_name" {
  description = "專案名稱（用於資源命名前綴）"
  type        = string
  default     = "aev"
}

variable "location" {
  description = "Azure 區域（對台灣延遲最低建議 japaneast）"
  type        = string
  default     = "japaneast"
}

variable "vm_size" {
  description = "VM 規格（2 vCPU / 8GB RAM；D 系列比 B 系列容量充足，Standard_D2as_v4 更便宜）"
  type        = string
  default     = "Standard_D2s_v3"
}

variable "admin_username" {
  description = "SSH 登入使用者名稱"
  type        = string
  default     = "azureuser"
}

variable "ssh_public_key_path" {
  description = "本機 SSH 公鑰路徑"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "ssh_source_cidr" {
  description = "允許 SSH 連入的來源 CIDR（建議設成自己的 IP，例如 1.2.3.4/32）"
  type        = string
  default     = "0.0.0.0/0" # 教學預設全開；上線請改成自己的 IP
}
