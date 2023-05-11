#!/usr/bin/env bash

sudo service ssh start
export PATH=$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$PATH

source $HADOOP_HOME/etc/hadoop/hadoop-env.sh


cd $HADOOP_HOME
DIR=/tmp/hadoop-hdfs/dfs
if [ ! -d "$DIR" ];
then
    sudo rm -rf /tmp/hadoop-hdfs/dfs/*
	hdfs namenode -format -force
fi

start-dfs.sh

sleep 10

hdfs dfs -mkdir -p /tmp/hive
hdfs dfs -chmod -R 777 /tmp

hdfs dfs -mkdir -p /data
hdfs dfs -mkdir -p /user/hive/warehouse

tail -f /dev/null