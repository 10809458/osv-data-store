import requests
import json
import os
import time
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.core.exceptions import ResourceExistsError, HttpResponseError

# Load configuration from the JSON file
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

# Extract the list of packages and vulnerability filters from the configuration
packages = config.get("packages", [])
vulnerability_filters = config.get("vulnerability_filter", [])

# Generate container name based on current date
src_container_name = datetime.now().strftime("%Y%m%d").lower()
# src_container_name = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d").lower()

# Azure Storage configuration
azure_storage_account_name = "osvdatastorageacct"  # Replace with your actual storage account name from Terraform output
azure_storage_account_key = "update you project related"  # Replace with your actual storage account key from Terraform output
azure_storage_connection_string = f"DefaultEndpointsProtocol=https;AccountName={azure_storage_account_name};AccountKey={azure_storage_account_key};EndpointSuffix=core.windows.net"

# Initialize BlobServiceClient
blob_service_client = BlobServiceClient.from_connection_string(azure_storage_connection_string)
container_client = blob_service_client.get_container_client(src_container_name)

# Retry mechanism for container creation
max_retries = 5
retry_delay = 10  # seconds

for attempt in range(max_retries):
    try:
        # Create the container if it doesn't exist
        if not container_client.exists():
            container_client.create_container()
        break
    except ResourceExistsError as e:
        if "ContainerBeingDeleted" in str(e):
            print(f"Container is being deleted. Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
        else:
            raise e
    except HttpResponseError as e:
        print(f"Error creating container: {e}")
        break

# OSV API URL
url = "https://api.osv.dev/v1/query"

headers = {"Content-Type": "application/json"}


# Iterate over the packages
for package in packages:
    # Create payload for each package
    payload = {
        "package": package
    }

    try:
        # Send POST request for each package
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()

        # Parse JSON response
        data = response.json()

        # Check if there are any vulnerabilities in the response
        if "vulns" in data and data["vulns"]:
            # Iterate over each vulnerability in the response
            for vuln in data["vulns"]:
                # Extract the vuln ID
                vuln_id = vuln.get("id")

                # Check if any filter matches the full vuln_id string (not character by character)
                for filter in vulnerability_filters:
                    if filter in vuln_id:  # Check if the entire filter string is in the vuln_id
                        # Increment the count for the corresponding filter
                        # vulnerability_count[filter] += 1

                        # Prepare the data to be saved (package info + vulnerability details)
                        vuln_data = {
                            "package": package,
                            "vulnerability": vuln
                        }

                        # Create the filename using the vuln_id
                        filename = f"{vuln_id}.json"

                        # Save the extracted data to a JSON file
                        file_content = json.dumps(vuln_data, indent=4)
                        blob_client = container_client.get_blob_client(filename)
                        blob_client.upload_blob(file_content, overwrite=True)

                        # print(f"Found vulnerability {vuln_id} for package '{package['name']}'. Stored in Azure Blob '{filename}'.")

        else:
            print(f"No vulnerabilities found for package '{package['name']}'.")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching vulnerabilities for package '{package['name']}': {e}")

# # After processing all packages, save the summary count to a JSON file
# summary_filename = "vulnerability_summary.json"
# summary_content = json.dumps(vulnerability_count, indent=4)
# summary_blob_client = container_client.get_blob_client(summary_filename)
# summary_blob_client.upload_blob(summary_content, overwrite=True)

# print(f"Vulnerability counts by filter stored in Azure Blob '{summary_filename}'")