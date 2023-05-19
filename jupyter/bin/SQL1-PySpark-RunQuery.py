#!/usr/bin/env python
# coding: utf-8

# !pip install --upgrade pip
# !pip install SQLAlchemy==1.3
# !pip install pyhive[hive]
# !pip install thrift
# !pip install sasl
# !pip install thrift-sasl 
# !pip install psycopg2

# /**
# 注意：
# @date1表示开始时间，@date2表示结束时间，一般两者相差一天，即取一天的数据。
# bd/ad/ld/cp格式都是yyyymmddhh24，比如2023032301
# @batchId表示批次的变量，yyyymmddhh24格式，比如2023032301
# udf_is_null 自定义函数，用于判断字段是否为空，如果字段为空/null或者空字符串，都返回0，否则返回1
# --主表建表语句 TABLE tb_test --每天1T数据，f02本端号码（去重后2千万），f04对端号码（去重后2千万），f16中文内容
# */

# In[ ]:


import sys,os,logging
import argparse


date_strftime_format = "%d-%b-%y %H:%M:%S"
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='[%(asctime)s] %(name)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',)

parser = argparse.ArgumentParser()
parser.add_argument("--f", "--filepath", type=str, default="./conf/default.conf", help='provide configuration filepath')
args = parser.parse_args(args=['--filepath', './conf/default.conf'])
configFilePath = args.f

from configparser import ConfigParser
config_object = ConfigParser()
config_object.read(configFilePath)
scaleinfo = config_object["SCALEINFO"]
scale = scaleinfo.getint("scale_gb")
batch = scaleinfo.getint("batch_k")
timespan_days = scaleinfo.getint("timespan_days")
droptable = scaleinfo.getboolean("droptable")

logging.info("Using following scale configuration: ")
for (each_key, each_val) in config_object.items(config_object["SCALEINFO"].name):
    logging.info( each_key + ":" + each_val)

    
systeminfo = config_object["SYSTEMINFO"]
SPARK_APP_NAME = str(systeminfo.get("spark.app.name")).strip('\"')
SPARK_MASTER = str(systeminfo.get("spark.master.hostpath")).strip('\"')
HIVE_HMS_HOST= str(systeminfo.get("hive.metastore.uris")).strip('\"')
SPARK_WAREHOUSE_DIR = str(systeminfo.get("spark.sql.warehouse.dir")).strip('\"')
SPARK_DRIVER_CORES = systeminfo.getint("spark_driver_cores")
SPARK_DRIVER_MEMORY = str(systeminfo.get("spark.driver.memory")).strip('\"')
SPARK_EXECUTOR_CORES = systeminfo.getint("spark.executor.cores")
SPARK_DRIVER_MEMORY = str(systeminfo.get("spark.executor.memory")).strip('\"')

logging.info("Using following system configuration: ")
for (each_key, each_val) in config_object.items(config_object["SYSTEMINFO"].name):
    logging.info( each_key + ":" + each_val)


# In[2]:


import math
import pyspark
import pandas as pd
import numpy as np

from pyspark.sql import SQLContext, SparkSession
from pyspark.sql.functions  import from_unixtime
from time import sleep

spark = SparkSession         .builder         .appName(SPARK_APP_NAME)         .master(SPARK_MASTER)         .config("hive.metastore.uris", HIVE_HMS_HOST)         .config("spark.sql.warehouse.dir", SPARK_WAREHOUSE_DIR)         .config("spark_driver_cores", SPARK_DRIVER_CORES)         .config("spark.driver.memory", SPARK_DRIVER_MEMORY)         .config("spark.executor.cores", SPARK_EXECUTOR_CORES)         .config("spark.executor.memory", SPARK_DRIVER_MEMORY)         .enableHiveSupport()         .getOrCreate()

spark.sparkContext.setLogLevel("INFO")
sqlContext = SQLContext(spark.sparkContext, sparkSession=spark)
spark.sparkContext.version
logging.info("Spark Version: " + spark.version)
logging.info("PySpark Version: " + pyspark.__version__)
logging.info("Pandas Version: " + pd.__version__)


# In[ ]:


def create_view_tb_test_qf_tmp1(batchId, dateFrom, dateTo):
    
    logging.info("CREATE OR REPLACE TEMPORARY VIEW tb_test_qf_tmp1  ...")

    sqlContext.sql("use sample;") 
    query = """
        CREATE OR REPLACE TEMPORARY VIEW tb_test_qf_tmp1 
        as
        with tb_test_qf_tmp as (
            select trim(f02) as f02, trim(f04) as f04,trim(f22) as f22,
            regexp_replace(regexp_replace(regexp_replace(trim(f16),'\\\?+','\?') ,'0+','0'),'[ \t]+',' ') as f16,
            from_unixtime(unix_timestamp(cast(f30 as string),'yyyyMMddHH'), 'yyyy-MM-dd-HH')  as bd,
            {batchId} as ad,
            trim(f06) as f06,trim(f07) as f07
            from tb_test t
            where f31 >= {date1} and f31 < {date2} and f14 = '49'
        ),
        tb_test_qf_tmp1 as (
        select a.f22,a.f02,a.f16, count(distinct a.f04) as cnt,a.bd ,a.ad,
        a.f06,a.f07
        from tb_test_qf_tmp a
        left join tb_sev_u b on a.f02 = b.id
        where a.f02 is not null and b.id is null
        and length(a.f16) > 10
        group by a.f22,a.f02,a.f16,a.bd,a.ad,a.f06,a.f07 
        having cnt > 10
        )
        select * from tb_test_qf_tmp1
        ;
    """.format(batchId=batchId, date1=dateFrom, date2=dateTo)

    logging.info("\nExecuting query: \n" + query)
    sqlContext.sql(query) 
    logging.info("View tb_test_qf_tmp1 created.")

    
def getLastBatchDate():
    sqlContext.sql("use sample");
    query="select max(batchId) as lastdate from sample.tb_test_qf_stat_log"
    logging.info("Executing query: " + query)
    lastBatch =(int(sqlContext.sql(query).collect()[0]["lastdate"]))
    logging.info("Completed query: " + query + " with latchBatch = " + str(lastBatch) + ".")
    return lastBatch

def reinitTable(batchId):
    sqlContext.sql("use sample");
    query = "alter table tb_test_qf_stat drop if exists partition (ad = {batchId})".format(batchId=batchId)
    logging.info("Executing query: " + query)
    sqlContext.sql(query);
    logging.info("Completed query: " + query + " with latchBatch = " + str(batchId) + ".")
    return True


import gc
from datetime import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta

lastBatch = getLastBatchDate()
lastBatchDate = datetime.strptime(str(lastBatch), "%Y%m%d%H")
dayrange = 1
date1  = lastBatchDate
date2  = lastBatchDate + relativedelta(days=dayrange)

dateFrom = date1.strftime("%Y%m%d%H")
dateTo = date2.strftime("%Y%m%d%H")
rounds = math.ceil(timedelta(days=dayrange)  / timedelta(hours=1))

logging.info("Running total " + str(rounds) + " rounds from " + dateFrom + " to " + dateTo)

for i in range(rounds):
    if i > 0 :
        date1 = (date1 + relativedelta(hours=1))
    
    date2 = (date1 + relativedelta(hours=1))
    batchId = date2.strftime("%Y%m%d%H")
    reinitTable(batchId)

date1  = lastBatchDate
date2  = lastBatchDate + relativedelta(days=dayrange)
runstarttime = datetime.now()
for i in range(rounds):
    if i > 0 :
        date1 = (date1 + relativedelta(hours=1))
    
    date2 = (date1 + relativedelta(hours=1))
    batchId = date2.strftime("%Y%m%d%H")
    dateFrom = date1.strftime("%Y%m%d%H")
    dateTo = date2.strftime("%Y%m%d%H")
    
    logging.info("Running rounds " + str(i+1) + " for batchId =" + str(batchId) + ".")
    create_view_tb_test_qf_tmp1(batchId, dateFrom, dateTo)
    
    query = "alter table tb_test_qf_stat drop if exists partition (ad = {batchId})".format(batchId=batchId)
    logging.info("Executing query: " + query)
    sqlContext.sql(query);
    logging.info("table sample.tb_test_qf_stat partition " + str(batchId) + " dropped.")
    
    sqlContext.sql("set hive.exec.dynamic.partition.mode=nonstrict")
    query = """
     insert into sample.tb_test_qf_stat partition(bd, ad)
     select f22,f02,f16,cnt,f06,f07,bd,ad
     from tb_test_qf_tmp1
    ;"""
    logging.info("\nExecuting query: \n" + query)
    runstarttime = datetime.now()
    sqlContext.sql(query) 
    runfinishtime = datetime.now()
    logging.info("finished round " + str(i+1) + " with " + str( (runfinishtime - runstarttime).seconds)  + " seconds")
    
    query="""
        select f22,f02,f16,cnt,bd,f06,f07 from
        ( select *, row_number() over(partition by f02 order by bd desc ) rn from tb_test_qf_stat) t
        where t.rn =1;
    """
    df=sqlContext.sql(query) 
    df.show(100,False)
    
    spark.catalog.clearCache()
    gc.collect()

runfinishtime = datetime.now()
sqlContext.sql("set hive.exec.dynamic.partition.mode=strict")
logging.info("Finished tb_test_qf_stat Insert Query with " + str( (runfinishtime - runstarttime).seconds)  + " seconds")


# df = sqlContext.sql("select * from sample.tb_test_qf_stat")
# df.show(10,False)

# In[ ]:


spark.sparkContext.stop()


# In[ ]:




