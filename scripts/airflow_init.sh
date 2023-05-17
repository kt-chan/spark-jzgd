#!/usr/bin/env bash

su airflow -c "airflow connections add 'dbt_postgres_instance_raw_data' --conn-uri $AIRFLOW_CONN_DBT_POSTGRESQL_CONN"

su airflow -c "airflow connections add 'spark_thrift_default' --conn-uri $AIRFLOW_CONN_SPARK_CONN"

su airflow -c "airflow connections add 'dbt_ssh_conn' --conn-uri '$AIRFLOW_CONN_DBT_SSH_CONN'"
