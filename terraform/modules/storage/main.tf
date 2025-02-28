provider "azurerm" {
  features {}

  subscription_id = var.subscription_id
  client_id       = var.client_id
  client_secret   = var.client_secret
  tenant_id       = var.tenant_id
  resource_provider_registrations  = "none"
}

resource "azurerm_resource_group" "osv_data_rg" {
  name     = "osv-data-resources"
  location = "East US"
}

resource "azurerm_storage_account" "osv_data_sa" {
  name                     = "osvdatastorageacct"
  resource_group_name      = azurerm_resource_group.osv_data_rg.name
  location                 = azurerm_resource_group.osv_data_rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_storage_account" "osv_data_sa_tgt" {
  name                     = "osvdatastorageaccttgt"
  resource_group_name      = azurerm_resource_group.osv_data_rg.name
  location                 = azurerm_resource_group.osv_data_rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_storage_container" "osv_data_container" {
  name                  = "vulnerability-data"
  storage_account_name  = azurerm_storage_account.osv_data_sa.name
  container_access_type = "private"
}

output "storage_account_name" {
  value = azurerm_storage_account.osv_data_sa.name
}

output "storage_account_key" {
  value     = azurerm_storage_account.osv_data_sa.primary_access_key
  sensitive = true
}