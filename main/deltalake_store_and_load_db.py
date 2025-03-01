from pyspark.sql import SparkSession
from delta import DeltaTable
from pyspark.sql.functions import col, substring
import os
import time
from datetime import datetime, timedelta



# Generate container names based on the current date
delta_container_name = datetime.now().strftime("%Y%m%d").lower()
tgt_container_name = datetime.now().strftime("%Y%m%d").lower()

# Azure Storage account details
delta_storage_account_name = "osvdatastorageacctdelta"
tgt_storage_account_name = "osvdatastorageaccttgt"
delta_storage_account_key = "update you project related"  # Replace with your actual storage account key from Terraform output
tgt_storage_account_key = "update you project related"  # Replace with your actual storage account key from Terraform output

# Define Storage Paths
source_parquet_path = f"wasbs://{tgt_container_name}@{tgt_storage_account_name}.blob.core.windows.net/vulnerability_data.parquet"  # Path where daily Parquet files are stored
delta_path = f"wasbs://{delta_container_name}@{delta_storage_account_name}.blob.core.windows.net/delta/vulnerabilities"  # Path for Delta Lake storage

# Initialize Spark Session with Delta Support
spark = SparkSession.builder \
    .appName("OSV-DeltaLake-DailyPartition") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()

# Step 1: Read All Parquet Files from Source (Handles Multiple Daily Files)
df = spark.read.parquet(source_parquet_path)

# Step 2: Extract Year & Day from Published Date
df = df.withColumn("year", substring(col("published"), 1, 4))  # Extract YYYY
df = df.withColumn("day", substring(col("published"), 1, 10))  # Extract YYYY-MM-DD

# Step 3: Write Data to Delta Table (Partitioned by Year & Day)
df.write.format("delta") \
    .mode("append") \
    .partitionBy("year", "day") \
    .save(delta_path)

print("New daily data appended to Delta Lake")

# Step 4: Read the Latest Data from Delta Table
df_delta = spark.read.format("delta").load(delta_path)
df_delta.show()

# Step 5: Enable Time Travel - Read Previous Versions
df_version_0 = spark.read.format("delta").option("versionAsOf", 0).load(delta_path)
df_version_0.show()

# Step 6: Optimize and Vacuum for Performance
delta_table = DeltaTable.forPath(spark, delta_path)

# Optimize for faster queries
delta_table.optimize().execute()

# Vacuum to remove old versions (retains last 7 days)
delta_table.vacuum(retentionHours=168)

print("Delta table optimized and vacuumed")

# Step 7: Write Data to Azure Synapse Analytics
# Define Synapse Connection Properties
synapse_jdbc_url = "jdbc:sqlserver://<synapse_server_name>.database.windows.net:1433;database=<synapse_database_name>"
synapse_table = "vulnerability_data"
synapse_properties = {
    "user": "<synapse_username>",
    "password": "<synapse_password>",
    "driver": "com.microsoft.sqlserver.jdbc.SQLServerDriver"
}

# Write Data to Synapse Table
df_delta.write \
    .format("jdbc") \
    .mode("overwrite") \
    .option("url", synapse_jdbc_url) \
    .option("dbtable", synapse_table) \
    .option("user", synapse_properties["user"]) \
    .option("password", synapse_properties["password"]) \
    .option("driver", synapse_properties["driver"]) \
    .save()

print("Data written to Azure Synapse Analytics")