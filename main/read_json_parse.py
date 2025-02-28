from pyspark.sql import SparkSession
from azure.storage.blob import BlobServiceClient
import json
import time
from datetime import datetime, timedelta

# Generate container names based on the current date
# src_container_name = datetime.now().strftime("%Y%m%d").lower()
# tgt_container_name = datetime.now().strftime("%Y%m%d").lower()
src_container_name = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d").lower()
tgt_container_name = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d").lower()

# Azure Storage account details
src_storage_account_name = "osvdatastorageacct"
tgt_storage_account_name = "osvdatastorageaccttgt"
src_storage_account_key = "update you project related"  # Replace with your actual storage account key from Terraform output
tgt_storage_account_key = "update you project related"  # Replace with your actual storage account key from Terraform output

# Connection strings for source and target storage accounts
src_connection_string = f"DefaultEndpointsProtocol=https;AccountName={src_storage_account_name};AccountKey={src_storage_account_key};EndpointSuffix=core.windows.net"
tgt_connection_string = f"DefaultEndpointsProtocol=https;AccountName={tgt_storage_account_name};AccountKey={tgt_storage_account_key};EndpointSuffix=core.windows.net"

# Initialize Spark session
spark = SparkSession.builder \
    .appName("Read JSON Files from Azure Storage and Write to Parquet") \
    .config("spark.jars.packages", "org.apache.hadoop:hadoop-azure:3.2.0,org.apache.hadoop:hadoop-azure-datalake:3.2.0,com.microsoft.azure:azure-storage:8.6.6") \
    .config("spark.sql.catalogImplementation", "hive") \
    .config("fs.azure", "org.apache.hadoop.fs.azure.NativeAzureFileSystem") \
    .config(f"fs.azure.account.key.{src_storage_account_name}.blob.core.windows.net", src_storage_account_key) \
    .config(f"fs.azure.account.key.{tgt_storage_account_name}.blob.core.windows.net", tgt_storage_account_key) \
    .config("fs.azure.createRemoteFileSystemDuringInitialization", "true") \
    .config("fs.azure.remoteFileSystemThreadCount", "8") \
    .enableHiveSupport() \
    .getOrCreate()

# Print Spark version for debugging
print(f"Using Spark version: {spark.version}")

# Initialize BlobServiceClient for source and target storage accounts
src_blob_service_client = BlobServiceClient.from_connection_string(src_connection_string)
tgt_blob_service_client = BlobServiceClient.from_connection_string(tgt_connection_string)

# Initialize container clients for source and target containers
src_container_client = src_blob_service_client.get_container_client(src_container_name)
tgt_container_client = tgt_blob_service_client.get_container_client(tgt_container_name)

# Create the target container if it does not exist
if not tgt_container_client.exists():
    tgt_container_client.create_container()

print("I AM HERE step 1")

# List blobs in the source container
blob_list = src_container_client.list_blobs()
print("I AM HERE step 2")

# Define the required fields
columns = ["id", "summary", "details", "aliases", "modified", "published"]
print("I AM HERE step 3")

# Create an empty DataFrame with the required schema
schema = "id STRING, summary STRING, details STRING, aliases STRING, modified STRING, published STRING"
df = spark.createDataFrame([], schema)
print("I AM HERE step 4")
df.show()

# Loop through each blob in the source container
for blob in blob_list:
    try:
        # Read JSON file from Azure Storage
        blob_client = src_container_client.get_blob_client(blob.name)
        json_data = blob_client.download_blob().readall()

        # Parse JSON data
        data = json.loads(json_data)
        print("I AM HERE step 5")
        
        # Extract relevant fields from "vulnerability"
        vulnerability = data.get("vulnerability", {})

        # Prepare the extracted data
        extracted_data = {
            "id": vulnerability.get("id", ""),
            "summary": vulnerability.get("summary", ""),
            "details": vulnerability.get("details", ""),
            "aliases": ", ".join(vulnerability.get("aliases", [])),  # Convert list to string
            "modified": vulnerability.get("modified", ""),
            "published": vulnerability.get("published", "")
        }
        print("I AM HERE step 6")
        
        # Create a DataFrame from the extracted data
        extracted_df = spark.createDataFrame([extracted_data])

        # Append the extracted DataFrame to the main DataFrame
        df = df.union(extracted_df)
    except json.JSONDecodeError as e:
        print(f"Failed to decode JSON for blob {blob.name}: {e}")
    except Exception as e:
        print(f"Failed to process blob {blob.name}: {e}")

# Define the Parquet file path in the target container
parquet_file_path = f"wasbs://{tgt_container_name}@{tgt_storage_account_name}.blob.core.windows.net/vulnerability_data.parquet"

# Write the DataFrame to Parquet file in the target container
try:
    df.write \
        .mode("overwrite") \
        .parquet(parquet_file_path)
    print("Data successfully written to Parquet file")
except Exception as e:
    print(f"Failed to write data to Parquet file: {e}")

# Stop the Spark session
spark.stop()