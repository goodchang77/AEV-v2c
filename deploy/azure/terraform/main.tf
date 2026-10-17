# =============================================================================
# Azure VM 佈建（Terraform）
# 建立單一 Ubuntu VM + 網路 + 安全群組，供 docker-compose 整包部署。
# =============================================================================

terraform {
  required_version = ">= 1.3"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0" # 若你的 terraform 較舊，可降為 "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

# -----------------------------------------------------------------------------
# 資源群組
# -----------------------------------------------------------------------------
resource "azurerm_resource_group" "rg" {
  name     = "${var.project_name}-rg"
  location = var.location
}

# -----------------------------------------------------------------------------
# 網路：VNet + 子網路 + NSG + 公用 IP + NIC
# NSG 預設只放行 SSH（且來源必須是明確的 CIDR）；HTTPS/HTTP 需顯式設定來源。
# -----------------------------------------------------------------------------
resource "azurerm_virtual_network" "vnet" {
  name                = "${var.project_name}-vnet"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  address_space       = ["10.0.0.0/16"]
}

resource "azurerm_subnet" "subnet" {
  name                 = "${var.project_name}-subnet"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.1.0/24"]
}

resource "azurerm_network_security_group" "nsg" {
  name                = "${var.project_name}-nsg"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location

  security_rule {
    name                       = "SSH"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = var.ssh_source_cidr
    destination_address_prefix = "*"
  }

  # 安全：不再開放 8000（API 明文 HTTP）與任意來源的 80/443。
  # API 只綁 VM 的 127.0.0.1:8000，對外必須經由 VM 上的 TLS 反向代理（443），
  # 且 443 / 80 的來源 CIDR 必須由 var.https_source_cidrs / var.http_source_cidrs 明確指定。
  dynamic "security_rule" {
    for_each = length(var.https_source_cidrs) > 0 ? [1] : []
    content {
      name                       = "HTTPS"
      priority                   = 130
      direction                  = "Inbound"
      access                     = "Allow"
      protocol                   = "Tcp"
      source_port_range          = "*"
      destination_port_range     = "443"
      source_address_prefixes    = var.https_source_cidrs
      destination_address_prefix = "*"
    }
  }

  # 選用：只在需要 HTTP→HTTPS 轉址或 ACME HTTP-01 驗證時開放 80（預設不開）。
  dynamic "security_rule" {
    for_each = length(var.http_source_cidrs) > 0 ? [1] : []
    content {
      name                       = "HTTP"
      priority                   = 120
      direction                  = "Inbound"
      access                     = "Allow"
      protocol                   = "Tcp"
      source_port_range          = "*"
      destination_port_range     = "80"
      source_address_prefixes    = var.http_source_cidrs
      destination_address_prefix = "*"
    }
  }
}

resource "azurerm_public_ip" "pip" {
  name                = "${var.project_name}-pip"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_network_interface" "nic" {
  name                = "${var.project_name}-nic"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.subnet.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.pip.id
  }
}

resource "azurerm_network_interface_security_group_association" "nsg_assoc" {
  network_interface_id      = azurerm_network_interface.nic.id
  network_security_group_id = azurerm_network_security_group.nsg.id
}

# -----------------------------------------------------------------------------
# Linux VM（Ubuntu 22.04 LTS）+ cloud-init 裝 Docker
# -----------------------------------------------------------------------------
resource "azurerm_linux_virtual_machine" "vm" {
  name                = "${var.project_name}-vm"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  size                = var.vm_size

  admin_username                  = var.admin_username
  disable_password_authentication = true

  admin_ssh_key {
    username   = var.admin_username
    public_key = file(var.ssh_public_key_path)
  }

  network_interface_ids = [azurerm_network_interface.nic.id]

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
    disk_size_gb         = 64
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts"
    version   = "latest"
  }

  # cloud-init：安裝 Docker + compose plugin（首次開機執行）
  custom_data = base64encode(
    templatefile("${path.module}/cloud-init.yaml.tpl", {
      admin_username = var.admin_username
    })
  )

  tags = {
    project = var.project_name
  }
}
