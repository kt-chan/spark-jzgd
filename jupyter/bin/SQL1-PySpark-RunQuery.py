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


# In[ ]:


import math
import pyspark
import pandas as pd
import numpy as np

from pyspark.sql import SQLContext, SparkSession
from pyspark.sql.functions  import from_unixtime

spark = SparkSession         .builder         .appName(SPARK_APP_NAME)         .master(SPARK_MASTER)         .config("hive.metastore.uris", HIVE_HMS_HOST)         .config("spark.sql.warehouse.dir", SPARK_WAREHOUSE_DIR)         .config("spark_driver_cores", SPARK_DRIVER_CORES)         .config("spark.driver.memory", SPARK_DRIVER_MEMORY)         .config("spark.executor.cores", SPARK_EXECUTOR_CORES)         .config("spark.executor.memory", SPARK_DRIVER_MEMORY)         .enableHiveSupport()         .getOrCreate()

spark.sparkContext.setLogLevel("INFO")
sqlContext = SQLContext(spark.sparkContext, sparkSession=spark)
spark.sparkContext.version
logging.info("Spark Version: " + spark.version)
logging.info("PySpark Version: " + pyspark.__version__)
logging.info("Pandas Version: " + pd.__version__)


# In[ ]:


def create_tb_test_qf_stat():
    
    sqlContext.sql("use sample;") 
    logging.info("Executing query: drop table if exists tb_test_qf_stat ..." )
    sqlContext.sql("drop table if exists tb_test_qf_stat;") 
        
    stmt = """
            create table if not exists tb_test_qf_stat(
            f22 string,
            f02 string,
            f16 string,
            cnt bigint,
            f06    string,
            f07    string
            )partitioned by (bd string, ad bigint)
            ;
           """
    
    logging.info("Executing query: \n" + stmt)
    sqlContext.sql(stmt)
    


# In[ ]:


from datetime import datetime
from dateutil.relativedelta import relativedelta

today = datetime.now()
target  = today - relativedelta(days=7)

batchId = target.strftime("%Y%m%d%H")
date1 = target.strftime("%Y%m%d%H")
date2 = today.strftime("%Y%m%d%H")

query = """
with tb_test_qf_tmp as (
    select trim(f02) as f02, trim(f04) as f04,trim(f22) as f22,
    regexp_replace(regexp_replace(regexp_replace(trim(f16),'\\\?+','\?') ,'0+','0'),'[ \t]+',' ') as f16,
    from_unixtime(unix_timestamp(cast(f30 as string),'yyyyMMddHH'), 'yyyy-MM-dd')  as bd,
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
insert into tb_test_qf_stat partition(bd, ad)
select f22,f02,f16,cnt,f06,f07,bd,ad
from tb_test_qf_tmp1
-- order by ad, bd, f22, f02
-- select * from tb_test_qf_tmp
;
""".format(batchId=batchId, date1=date1, date2=date2)

sqlContext.sql("use sample;") 
sqlContext.sql("set hive.exec.dynamic.partition.mode=nonstrict")
create_tb_test_qf_stat()
df = sqlContext.sql("show tables") 
df.show()

from time import sleep
sleep(5)

logging.info("\nExecuting query: \n" + query)
runstarttime = datetime.now()
sqlContext.sql(query) 
runfinishtime = datetime.now()
logging.info("Finished Query with " + str( (runfinishtime - runstarttime).seconds)  + " seconds")

df = sqlContext.sql("select * from tb_test_qf_stat limit 10")
df.show(10, False)


# In[ ]:


spark.sparkContext.stop()


# In[ ]:




