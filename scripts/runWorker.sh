#!/usr/bin/env bash

cd ${SPARK_HOME}
./sbin/start-worker.sh --host $HOSTNAME spark://${SPARK_MASTER_HOST}:${SPARK_MASTER_PORT}

sleep 10

tail -f ${SPARK_HOME}/logs/spark--org.apache.spark.deploy.worker.*