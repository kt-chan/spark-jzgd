#!/usr/bin/env bash

# Enable ssh server
/etc/init.d/ssh restart


cd /dbt 

# dbt compile
# dbt docs generate 
dbt deps
nohup dbt docs serve --port 8081  >  ${DBT_HOME}/logs/dbt.log 2>&1 &

## # Wait for any process to exit
## wait -n
##   
## # Exit with status of process that exited first
## exit $?

## testing for log output
tail -f ${DBT_HOME}/logs/dbt.log
