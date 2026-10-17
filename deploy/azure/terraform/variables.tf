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
  description = "允許 SSH 連入的來源 CIDR（必填，例如你的對外 IP 1.2.3.4/32）。不允許 0.0.0.0/0 或 *。"
  type        = string
  # 刻意不給預設值：SSH 來源必須由操作者明確指定。

  validation {
    condition = (
      can(cidrhost(var.ssh_source_cidr, 0)) &&
      !contains(["0.0.0.0/0", "::/0", "*", "Internet", "Any"], var.ssh_source_cidr) &&
      !can(regex("/0$", var.ssh_source_cidr))
    )
    error_message = "ssh_source_cidr 必須是明確的 CIDR（例如 203.0.113.10/32），不可為 0.0.0.0/0、::/0 或 *。"
  }
}

variable "https_source_cidrs" {
  description = <<-EOT
    允許連入 443（TLS 反向代理）的來源 CIDR 清單（必填）。
    - [] = 不建立 HTTPS 規則（只透過 SSH tunnel 存取 API）。
    - 限定來源，例如 ["203.0.113.0/24"]。
    - 若確定要對整個網際網路公開 TLS 站台，需「明確」填入 ["0.0.0.0/0"]（無預設值）。
  EOT
  type        = list(string)

  validation {
    condition     = alltrue([for c in var.https_source_cidrs : can(cidrhost(c, 0))])
    error_message = "https_source_cidrs 的每個元素都必須是合法 CIDR（不可用 * 或 service tag）。"
  }
}

variable "http_source_cidrs" {
  description = "選用：允許連入 80 的來源 CIDR（僅供 HTTP→HTTPS 轉址或 ACME HTTP-01）。預設 [] = 不開放。"
  type        = list(string)
  default     = []

  validation {
    condition     = alltrue([for c in var.http_source_cidrs : can(cidrhost(c, 0))])
    error_message = "http_source_cidrs 的每個元素都必須是合法 CIDR（不可用 * 或 service tag）。"
  }
}
