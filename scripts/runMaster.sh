#!/usr/bin/env bash

sudo service ssh start

cd ${SPARK_HOME}
./sbin/start-master.sh --host $HOSTNAME

tail -f ${SPARK_HOME}/logs/spark--org.apache.spark.deploy.master.Master-1-spark-master.local.out