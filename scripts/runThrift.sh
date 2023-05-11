#!/usr/bin/env bash

cd ${SPARK_HOME}

## ## # Spark 3.2 standard 
## ./bin/spark-submit --master spark://$SPARK_MASTER_HOST:$SPARK_MASTER_PORT \
## --class org.apache.spark.sql.hive.thriftserver.HiveThriftServer2 \
## >> /tmp/logs/start-thriftserver.out & 


## ##Spark 3.2 with hudi table [this does not work for spark thrift sql]
##  ./bin/spark-submit --master spark://$SPARK_MASTER_HOST:$SPARK_MASTER_PORT \
##  --class org.apache.spark.sql.hive.thriftserver.HiveThriftServer2 \
##  >> /tmp/logs/start-thriftserver.out & 
## 

## test for local mode
nohup ./bin/spark-submit --class org.apache.spark.sql.hive.thriftserver.HiveThriftServer2 \
--conf "spark.cores.max=4" --conf "spark.executor.cores=2" --conf "spark.executor.memory=1G" \
>  ${SPARK_HOME}/logs/Spark.log 2>&1 &

sleep 10

tail -f ${SPARK_HOME}/logs/Spark.log