provider "azurerm" {
  features {}

  subscription_id = var.subscription_id
  client_id       = var.client_id
  client_secret   = var.client_secret
  tenant_id       = var.tenant_id
}

resource "azurerm_resource_group" "osv_data_rg" {
  name     = "osv_data-resources"
  location = "East US"
}

resource "azurerm_virtual_network" "osv_data_vnet" {
  name                = "osv_data-network"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.osv_data_rg.location
  resource_group_name = azurerm_resource_group.osv_data_rg.name
}

resource "azurerm_subnet" "osv_data_subnet" {
  name                 = "osv_data-subnet"
  resource_group_name  = azurerm_resource_group.osv_data_rg.name
  virtual_network_name = azurerm_virtual_network.osv_data_vnet.name
  address_prefixes     = ["10.0.2.0/24"]
}

resource "azurerm_public_ip" "osv_data_public_ip" {
  name                = "osv_data-public-ip"
  location            = azurerm_resource_group.osv_data_rg.location
  resource_group_name = azurerm_resource_group.osv_data_rg.name
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_network_security_group" "osv_data_nsg" {
  name                = "osv_data_nsg"
  location            = azurerm_resource_group.osv_data_rg.location
  resource_group_name = azurerm_resource_group.osv_data_rg.name

  security_rule {
    name                       = "SSH"
    priority                   = 1001
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

resource "azurerm_network_interface" "osv_data_nic" {
  name                = "osv_data-nic"
  location            = azurerm_resource_group.osv_data_rg.location
  resource_group_name = azurerm_resource_group.osv_data_rg.name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.osv_data_subnet.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.osv_data_public_ip.id
  }
}

resource "azurerm_network_interface_security_group_association" "osv_data_nic_nsg" {
  network_interface_id      = azurerm_network_interface.osv_data_nic.id
  network_security_group_id = azurerm_network_security_group.osv_data_nsg.id
}

resource "azurerm_virtual_machine" "osv_data_vm" {
  name                  = "osvdatamachine"
  location              = azurerm_resource_group.osv_data_rg.location
  resource_group_name   = azurerm_resource_group.osv_data_rg.name
  network_interface_ids = [azurerm_network_interface.osv_data_nic.id]
  vm_size               = "Standard_DS1_v2"

  storage_os_disk {
    name              = "osvdataosdisk"
    caching           = "ReadWrite"
    create_option     = "FromImage"
    managed_disk_type = "Standard_LRS"
  }

  storage_image_reference {
    publisher = "Canonical"
    offer     = "UbuntuServer"
    sku       = "18.04-LTS"
    version   = "latest"
  }

  os_profile {
    computer_name  = "osvdatamachine"
    admin_username = "adminuser"
  }

  os_profile_linux_config {
    disable_password_authentication = false

    ssh_keys {
      path     = "/home/adminuser/.ssh/authorized_keys"
      key_data = file("~/.ssh/id_rsa.pub")
    }
  }

  provisioner "remote-exec" {
    inline = [
      "sudo apt-get update",
      "sudo apt-get install -y git",
      "git clone https://github.com/10809458/osv-data-store /home/adminuser/osv-data-store",
      "cd /home/adminuser/osv-data-store",
      "python3 -m venv venv",
      "source venv/bin/activate",
      "pip install -r requirements.txt"
    ]

    connection {
      type        = "ssh"
      user        = "adminuser"
      private_key = file("~/.ssh/id_rsa")
      host        = azurerm_public_ip.osv_data_public_ip.ip_address
    }
  }
}

output "public_ip" {
  value = azurerm_public_ip.osv_data_public_ip.ip_address
}