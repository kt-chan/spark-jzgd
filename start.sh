#!/usr/bin/env bash
sudo docker-compose build
sudo docker-compose up jupyter-notebook -d
sudo docker-compose up dbt-service -d
sudo docker-compose up airflow-init -d
sudo docker-compose up -d

