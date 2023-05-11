export PATH=$PRESTO_HOME/presto-server/bin:$PATH

cd $PRESTO_HOME/presto-server

nohup ./bin/launcher run -v &

tail -f /dev/null