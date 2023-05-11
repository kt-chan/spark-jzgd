#!/usr/bin/env bash

export HIVE_OPTS="${HIVE_OPTS} --hiveconf metastore.root.logger=${HIVE_LOGLEVEL},console "
export PATH=$HIVE_HOME/bin:$HADOOP_HOME/bin:$PATH

source $HADOOP_HOME/etc/hadoop/hadoop-env.sh

set +e
if schematool -dbType postgres -info -verbose; then
    echo "Hive metastore schema verified."
else
    if schematool -dbType postgres -initSchema -verbose; then
        echo "Hive metastore schema created."
    else
        echo "Error creating hive metastore: $?"
    fi
fi
set -e

nohup hive --service metastore &
## nohup hive --service hiveserver2 &

tail -f /tmp/hive/hive.log