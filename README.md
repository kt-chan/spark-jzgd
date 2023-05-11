# Apache Airflow and DBT on Apache Spark with Hudi support, using Docker Compose
Stand-alone project that utilises public eCommerce data from Instacart to demonstrate how to schedule dbt models through Airflow.

For more Data & Analytics related reading, check https://analyticsmayhem.com

## Requirements 
* Install [Docker](https://www.docker.com/products/docker-desktop)
* Install [Docker Compose](https://github.com/docker/compose/releases v2.6) 
* Download the [Kaggle Instacart eCommerce dataset](https://www.kaggle.com/c/instacart-market-basket-analysis/data) 

## Dataset

The dataset for this competition is a relational set of files describing customers' orders over time. The goal of the competition is to predict which products will be in a user's next order. The dataset is anonymized and contains a sample of over 3 million grocery orders from more than 200,000 Instacart users. For each user, we provide between 4 and 100 of their orders, with the sequence of products purchased in each order. We also provide the week and hour of day the order was placed, and a relative measure of time between orders. For more information, see the blog post [https://tech.instacart.com/3-million-instacart-orders-open-sourced-d40d29ead6f2] accompanying its public release.

The user story for analytic example is available here:
1. https://rpubs.com/MohabDiab/482437
2. https://github.com/archd3sai/Instacart-Market-Basket-Analysis
3. https://asagar60.medium.com/instacart-market-basket-analysis-part-1-introduction-eda-b08fd8250502

## DBT with Spark and Hudi
https://github.com/apache/hudi/tree/master/hudi-examples/hudi-examples-dbt

## Setup 
* Clone the repository
* Run ./build.sh force
* Extract the "Kaggle Instacart eCommerce dataset" files to the new ./sample_data directory (files are needed as seed data)
* Run chmod +x *.sh
* Run start.sh

## Connections
* Airflow homepage: `http://[hostname]:8080/home `
* Jupyter notebook: `http://[hostname]:8888/lab?token=welcome `
* DBT homepage: `http://[hostname]:8081/#!/overview `
* Spark Master: `http://[hostname]:8082/ `
* Spark Thrift: `http://[hostname]:4040/jobs/ `

## Docker Compose Commands
* Run the services: `./start.sh` for all service or `./start-spark.sh` for spark with jupyter notebook only
* Disable the services: `./clean.sh` & `./prune.sh`

If you need to check the log of the running containers, use `docker-compose logs [service-name] -f ` to view the running services log.
If you need to connect to the running containers, use `docker-compose exec -it [service-name] bash ` to login the running services.


Credit to the very helpful repository: https://github.com/puckel/docker-airflow
