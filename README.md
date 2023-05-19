# Apache Spark SQL Stress Test for Log Processing

## Requirements 
* Centos 7 or Ubuntu 18.04 above, with 8 Vcores and 16GB RAM, 100GB Disk space
* Install [Docker](https://www.docker.com/products/docker-desktop)
* Install [Docker Compose](https://github.com/docker/compose/releases v2.6) 
* Internet Connection
* Download following packages, and put those under "tars" directory.
	- apache-hive-3.1.3-bin.tar.gz     
	- hadoop-aws-3.3.1.jar               
	- aws-java-sdk-bundle-1.12.383.jar 
	- Python-3.6.3.tgz
	- hadoop-3.2.3.tar.gz              
	- spark-3.3.1-bin-hadoop3.tgz

## Setup 
* Clone the repository
* Run chmod +x *.sh* 
* Run ./build.sh
* Run ./start-spark.sh

## Objective and Dataset
The dataset is reversed generated according to data schema provided by log processing agency. It is required to measure the sql processing duration to generate the following output on hours batch ETL

First, the SQL1-PySpark-DataGen.py Python script would generate all required dataset, with default 7 days logs, and then it would process the Batch workload at once for the first 6 days, and put the summary records into target tables.

Seconds, you should run SQL1-PySpark-RunQuery.py, and it would execute batch ETL workload for the last day on hours basis (total 24 rounds), and then append the output into target tables. 

The objective is use data turbo with SQL semantic cache service to accelerate this 24 iterations of batch ETL processes.


## Connections
* Jupyter notebook: `http://[hostname]:8888/lab?token=welcome `
* HDFS homepage: http://[hostname]:9870/
* Spark Master: `http://[hostname]:8082/ `

## Instruction
1. cd project directoy, if you run spark on current docker platform, please run following commands to stars necessary service. 
* sudo ./start-spark.sh

2. Edit ./juptyer/conf/default.conf , and change SystemInfo and ScaleInfo Parameters. You have at least change spark cluster connection information if you are not running this docker environment.
	- change SystemInfo for spark cluster setup, default is the local spark cluster values. 
	- change ScaleInfo for dataset size setup, default is the minimun values. 

3. Generate the data set with the following command
* python ./bin/SQL1-PySpark-DataGen.py -f ./conf/default.conf 

4. Execute daily batch ETL job
* python ./bin/SQL1-PySpark-RunQuery.py -f ./conf/default.conf 
 
5. Measure the output time for the log output line with prefix "Finished tb_test_qf_stat Insert Query ..."



## Docker Compose Commands
* Run the services: `./start-spark.sh` for all service
* Disable the services: `./clean.sh` & `./prune.sh`

If you need to check the log of the running containers, use `docker-compose logs [service-name] -f ` to view the running services log.
If you need to connect to the running containers, use `docker-compose exec -it [service-name] bash ` to login the running services.

