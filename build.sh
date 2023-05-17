#!/usr/bin/env bash
# sudo docker build -f ./dockerfile/dockerfile_airflow -t airflow:2.3.0 -t airflow:stable .
# sudo docker build -f ./dockerfile/dockerfile_dbt -t dbt-service:1.1.0 -t dbt-service:stable .
sudo docker build -f ./dockerfile/dockerfile_nginx -t nginx:latest .
sudo docker build -f ./dockerfile/dockerfile_ubuntu_hk_noproxy -t ubuntu:stable .
sudo docker build -f ./dockerfile/dockerfile_hadoop -t hadoop:3.2.3 -t hadoop:stable .
sudo docker build -f ./dockerfile/dockerfile_spark -t spark:3.3.1 -t spark:stable .
sudo docker build -f ./dockerfile/dockerfile_presto -t presto:0.261  -t presto:stable .
sudo docker build -f ./dockerfile/dockerfile_jupyter -t jupyter-spark:3.3.1 -t jupyter-spark:stable .

# download postgres:13 as local images
sudo docker image pull postgres:13 
sudo docker tag postgres:13 postgres:stable
