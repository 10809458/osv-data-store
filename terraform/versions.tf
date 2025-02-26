provider "azurerm" {
  features {}
}

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">=3.0"
    }
  }
  required_version = ">= 1.0"
}

module "networking" {
  source  = "./modules/networking"
  vnet_name = "osv-vnet"
  resource_group_name = "osv-resource-group"
  location = "eastus"
}

module "storage" {
  source  = "./modules/storage"
  storage_account_name = "osvdatastore"
  resource_group_name = module.networking.resource_group_name
  location = module.networking.location
}

module "databricks" {
  source  = "./modules/databricks"
  resource_group_name = module.networking.resource_group_name
  location = module.networking.location
  vnet_id  = module.networking.vnet_id
}

module "synapse" {
  source  = "./modules/synapse"
  resource_group_name = module.networking.resource_group_name
  location = module.networking.location
}

module "airflow" {
  source  = "./modules/airflow"
  resource_group_name = module.networking.resource_group_name
  location = module.networking.location
  vnet_id  = module.networking.vnet_id
}

module "permissions" {
  source  = "./modules/permissions"
  storage_account_id = module.storage.storage_account_id
  databricks_workspace_id = module.databricks.workspace_id
  synapse_workspace_id = module.synapse.workspace_id
}
