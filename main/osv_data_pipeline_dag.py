from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from datetime import datetime, timedelta

# Define default arguments
default_args = {
    'owner': 'adminuser',
    'depends_on_past': False,
    'start_date': datetime(2025, 3, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Define the DAG
dag = DAG(
    'osv_data_pipeline',
    default_args=default_args,
    description='OSV Data Pipeline DAG',
    schedule_interval='0 9 * * *',  # Run at 9 AM ET
    catchup=False,
)

# Define tasks
read_json_parse = BashOperator(
    task_id='read_json_parse',
    bash_command='python /home/adminuser/osv-data-store/read_json_parse.py',
    dag=dag,
)

read_api_store_ecosystems_data = BashOperator(
    task_id='read_api_store_ecosystems_data',
    bash_command='python /home/adminuser/osv-data-store/read_api_store_ecosystems_data.py',
    dag=dag,
)

deltalake_store_and_load_db = BashOperator(
    task_id='deltalake_store_and_load_db',
    bash_command='python /home/adminuser/osv-data-store/deltalake_store_and_load_db.py',
    dag=dag,
)

# Set up dependencies
read_json_parse >> read_api_store_ecosystems_data >> deltalake_store_and_load_db