# Apache Spark SQL Stress Test for Log Processing

## Requirements 
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

## Dataset
The dataset is reversed generated according to data schema provided by log processing agency
It is required to measure the sql processing duration to generate the following output on hours batch ETL
	+---+-----------+--------------------+---+-------------+---+---+
	|f22|f02        |f16                 |cnt|bd           |f06|f07|
	+---+-----------+--------------------+---+-------------+---+---+
	|3  |19218983880|Great you found me !|16 |2023-05-17-08|0  |7  |
	|3  |19218983881|Great you found me !|13 |2023-05-17-09|0  |7  |
	|3  |19218983882|Great you found me !|13 |2023-05-17-10|0  |7  |
	|3  |19218983883|Great you found me !|15 |2023-05-17-11|0  |7  |
	|3  |19218983884|Great you found me !|17 |2023-05-17-11|0  |7  |
	|3  |19218983885|Great you found me !|15 |2023-05-17-11|0  |7  |
	|3  |19218983886|Great you found me !|12 |2023-05-17-11|0  |7  |
	|3  |19218983887|Great you found me !|11 |2023-05-17-10|0  |7  |
	|3  |19218983888|Great you found me !|16 |2023-05-17-11|0  |7  |
	|3  |19218983889|Great you found me !|13 |2023-05-17-11|0  |7  |
	+---+-----------+--------------------+---+-------------+---+---+

## Connections
* Jupyter notebook: `http://[hostname]:8888/lab?token=welcome `
* HDFS homepage: http://[hostname]:9870/
* Spark Master: `http://[hostname]:8082/ `

## Instruction
1. Edit ./conf/default.conf , and change SystemConfig and ScaleConfig Parameters. You have at least change spark cluster connection information if you are not running this docker environment.

2. Generate the data set with the following command
* python ./bin/SQL1-PySpark-DataGen.py -f ./conf/default.conf 

3. Execute daily batch ETL job
* python ./bin/SQL1-PySpark-RunQuery.py -f ./conf/default.conf 
 
4. Measure the output time for the log output line with prefix "Finished tb_test_qf_stat Insert Query ..."
* python ./bin/SQL1-PySpark-DataGen.py -f ./conf/default.conf 


## Docker Compose Commands
* Run the services: `./start-spark.sh` for all service
* Disable the services: `./clean.sh` & `./prune.sh`

If you need to check the log of the running containers, use `docker-compose logs [service-name] -f ` to view the running services log.
If you need to connect to the running containers, use `docker-compose exec -it [service-name] bash ` to login the running services.

