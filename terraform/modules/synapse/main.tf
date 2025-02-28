provider "azurerm" {
  features {}

  subscription_id = var.subscription_id
  client_id       = var.client_id
  client_secret   = var.client_secret
  tenant_id       = var.tenant_id
  resource_provider_registrations  = "none"
}

# Resource Group
resource "azurerm_resource_group" "synapse_rg" {
  name     = "synapse-resource-group"
  location = "West US"
}

# Storage Account
resource "azurerm_storage_account" "synapse_storage" {
  name                     = "synapsestorageacct${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.synapse_rg.name
  location                 = azurerm_resource_group.synapse_rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  is_hns_enabled           = true  # Enable hierarchical namespace for Data Lake Storage Gen2
}

resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

# Data Lake Storage Gen2 Filesystem
resource "azurerm_storage_data_lake_gen2_filesystem" "synapse_filesystem" {
  name               = "filesystem"
  storage_account_id = azurerm_storage_account.synapse_storage.id
  depends_on         = [azurerm_storage_account.synapse_storage]
}

# Synapse Workspace
resource "azurerm_synapse_workspace" "synapse_workspace" {
  name                                 = "synapseworkspace${random_string.suffix.result}"
  resource_group_name                  = azurerm_resource_group.synapse_rg.name
  location                             = azurerm_resource_group.synapse_rg.location
  storage_data_lake_gen2_filesystem_id = azurerm_storage_data_lake_gen2_filesystem.synapse_filesystem.id
  sql_administrator_login              = "sqladmin"
  sql_administrator_login_password     = "P@ssw0rd1234!"
  identity {
    type = "SystemAssigned"
  }
}

# Synapse SQL Pool
resource "azurerm_synapse_sql_pool" "synapse_sql_pool" {
  name                 = "synapsesqlpool"
  synapse_workspace_id = azurerm_synapse_workspace.synapse_workspace.id
  sku_name             = "DW100c"
  storage_account_type = "GRS"
  depends_on           = [azurerm_synapse_workspace.synapse_workspace]
}

# Synapse Firewall Rule
resource "azurerm_synapse_firewall_rule" "synapse_firewall_rule" {
  name                 = "allow_all_azure_ips"
  synapse_workspace_id = azurerm_synapse_workspace.synapse_workspace.id
  start_ip_address     = "0.0.0.0"
  end_ip_address       = "255.255.255.255"
  depends_on           = [azurerm_synapse_workspace.synapse_workspace]
}