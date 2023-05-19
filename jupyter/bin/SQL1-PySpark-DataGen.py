#!/usr/bin/env python
# coding: utf-8

# !pip install --upgrade pip
# !pip3 install --upgrade pandas

# In[1]:


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
debugMode = scaleinfo.getboolean("debugMode")

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
import gc

from pyspark.sql import SQLContext, SparkSession
from pyspark.sql.functions  import from_unixtime

spark = SparkSession         .builder         .appName(SPARK_APP_NAME)         .master(SPARK_MASTER)         .config("hive.metastore.uris", HIVE_HMS_HOST)         .config("spark.sql.warehouse.dir", SPARK_WAREHOUSE_DIR)         .config("spark_driver_cores", SPARK_DRIVER_CORES)         .config("spark.driver.memory", SPARK_DRIVER_MEMORY)         .config("spark.executor.cores", SPARK_EXECUTOR_CORES)         .config("spark.executor.memory", SPARK_DRIVER_MEMORY)         .enableHiveSupport()         .getOrCreate()

spark.sparkContext.setLogLevel("INFO")
sqlContext = SQLContext(spark.sparkContext, sparkSession=spark)
spark.sparkContext.version
logging.info("Spark Version: " + spark.version)
logging.info("PySpark Version: " + pyspark.__version__)
logging.info("Pandas Version: " + pd.__version__)


# In[3]:


import threading
from time import sleep


taskdone = False
alphabet = list('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
LENGTH = 10

cols=["f01", "f02","f03", "f04", "f05", "f06", "f07", "f08", "f09", "f10","f11","f12","f13","f14","f15","f16","f17","f18","f19","f20","f21","f22","f23","f24","f25","f26","f27","f28","f29","f30","f31" ]
random_txtcols=["f03","f05","f08","f09","f11","f12","f13","f16","f17","f18","f20","f21","f23","f24","f25","f26","f27","f28","f29"]

def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f %s%s" % (num, 'Yi', suffix)

def getNumberOfExecutor():
    global spark
    sc=spark.sparkContext
    number_of_workers = len(sc._jsc.sc().statusTracker().getExecutorInfos()) - 1
    return number_of_workers

def delete_path(host, path):
    global spark
    sc=spark.sparkContext
    URI           = sc._gateway.jvm.java.net.URI
    Path          = sc._gateway.jvm.org.apache.hadoop.fs.Path
    FileSystem    = sc._gateway.jvm.org.apache.hadoop.fs.FileSystem
    Configuration = sc._gateway.jvm.org.apache.hadoop.conf.Configuration
    fs = FileSystem.get(URI(host), Configuration())
    logging.info("deleting hdfs directory: " + host + path)
    if fs.exists(Path(path)) :
        fs.delete(Path(path), True)
        logging.info("deleted " + path)

def progressbar():
    logging.info('Start')
    while not (taskdone):
        sleep(5)
        logging.info('.')

def inittask(droptable = False):
    global SPARK_WAREHOUSE_DIR
    
    if(droptable):
        logging.info('dropping sample.* tables')
        sqlContext.sql("drop table if exists sample.tb_test;")
        sqlContext.sql("drop table if exists sample.tb_sev_u;")
        sqlContext.sql("drop table if exists sample.tb_test_qf_stat;")
        sqlContext.sql("drop table if exists sample.tb_test_num_tmp;")
        sqlContext.sql("drop table if exists sample.tb_test_qf_lastest;")
        # Delete the HDFS directory for failure case
        pos=SPARK_WAREHOUSE_DIR.index("/", len("hdfs://"))
        hdfshost=SPARK_WAREHOUSE_DIR[:pos]
        hdfsdir=SPARK_WAREHOUSE_DIR[pos:]+"/sample.db"
        logging.info('deleting hdfs directory: ' + hdfsdir)
        delete_path(hdfshost, hdfsdir)
    
    sqlContext.sql("create database if not exists sample;")
    sqlContext.sql("use sample;")
    
    return True
    

def gendata_tbsevu(rounds = 1, batch_size = 100000):
    logging.info("generating data for tb_sev_u ...")
    
    sqlContext.sql("""
        create table sample.tb_sev_u 
        as
        select distinct f02 as id, f03 as name
        from sample.tb_test 
        where f02 < 19218983880 or f02 > 19218983890
        ORDER BY RAND () 
        limit {batch}
    ;""".format(batch=int(rounds*batch_size)))

    logging.info("finished loading data for tb_sev_u with " + str(batch_size) + " rows.")    
    
    
def gendata_tbtest_noise(fromTS, toTS, scale_rounds = 1, batch_size = 100000):
    global random_txtcols
    scale_rounds = scale_rounds + 1
    ## for 100,000 rows of data with 25MB Storage Data Without Replication
    df = pd.DataFrame()   
    initial_ts_int =  int(fromTS.value/10**9)
    target_ts_int =  int(toTS.value/10**9)
    
    logging.info("Round " + str(scale_rounds) + ": generating noise data for tb_test with batch size "+ str(batch_size) + " rows, from " + str(initial_ts_int) + " to " +  str(target_ts_int) + ".")
                 
    df1 = pd.DataFrame(np.random.randint(initial_ts_int, target_ts_int, size=(batch_size,1)),  columns=list(["f01"]))
    df2 = pd.DataFrame(np.random.randint(19200000000,19200000000+20000000,size=(batch_size,2)), columns=list(["f02", "f04"])) 
    df6 = pd.DataFrame(np.random.randint(0, 10, size=(batch_size,5)),  columns=list(["f06", "f07", "f10", "f15", "f19"]))
    df14 = pd.DataFrame(np.random.randint(48, 51, size=(batch_size,1)),  columns=list(["f14"]))
    df22 = pd.DataFrame(np.random.randint(1, 10, size=(batch_size,1)),  columns=list(["f22"]))
    df30 = pd.DataFrame(np.random.randint(initial_ts_int,target_ts_int,size=(batch_size,1)),  columns=list(["f30"]))
    df31 = df30
    df31 = df31.rename(columns={"f30": "f31"})
    
    for k in random_txtcols: 
        np_batchsize = None
        if k == 'f16' :
            np_batchsize = np.random.choice(np.array(alphabet, dtype="|U1"), [batch_size, math.ceil(1 + LENGTH * (np.random.randint(1, 30) / 10))])
        else :
            np_batchsize = np.random.choice(np.array(alphabet, dtype="|U1"), [batch_size, LENGTH])

        df0 = pd.DataFrame( ["".join(np_batchsize[i]) for i in range(len(np_batchsize))], columns=[k])
        df[k] = df0[k]

    df = pd.concat([df1,df2, df6, df14, df22, df30, df31, df], axis=1, join='inner')

    df = df[cols]
    logging.info("Memory Usage: " + f'{df.memory_usage(deep=True).sum():,}'  + " Bytes")

    logging.info("creating spark data frame for partitioins from " + str(pd.to_datetime(df['f01'].min(), unit='s')) + ' to ' +  str(pd.to_datetime(df['f01'].max(), unit='s')) + '... ')
    sparkDF = spark.createDataFrame(df)
    sparkDF = sparkDF.withColumn("cp", from_unixtime(sparkDF["f01"], "yyyyMMddHH").cast("BigInt"))
    sparkDF = sparkDF.withColumn("ld", from_unixtime(sparkDF["f01"], "yyyyMMddHH").cast("BigInt"))
    sparkDF = sparkDF.withColumn("f30", from_unixtime(sparkDF["f30"], "yyyyMMddHH").cast("BigInt"))
    sparkDF = sparkDF.withColumn("f31", from_unixtime(sparkDF["f31"], "yyyyMMddHH").cast("BigInt"))
    #sparkDF.coalesce(getNumberOfExecutor()).write.mode("append").partitionBy( ["cp","ld"]).bucketBy(32, "f02").sortBy("f01").format("orc").saveAsTable("tb_test")
    logging.info("writing to hive table sample.tb_test ...")
    
    current_ts = pd.Timestamp.now()
    
    sparkDF.coalesce(getNumberOfExecutor()).write.mode("append").partitionBy( ["cp","ld"]).format("orc").option("compression","ZLIB").saveAsTable("sample.tb_test")
    finish_ts = pd.Timestamp.now()
    
    spark.catalog.clearCache()
    gc.collect()
    logging.info("finished round " + str(scale_rounds) +  " with batch size "+ str(batch_size) + " rows with " + str( (finish_ts - current_ts).seconds)  + " seconds")
        

def gendata_tbtest_target(fromTS, toTS, scale_rounds = 1, batch_size = 100000):
    global random_txtcols
    scale_rounds = scale_rounds + 1
    ## for 100,000 rows of data with 25MB Storage Data Without Replication
    df = pd.DataFrame()   
    initial_ts_int =  int(fromTS.value/10**9)
    target_ts_int =  int(toTS.value/10**9)

    logging.info("Round " + str(scale_rounds) + ": generating target data for tb_test with batch size "+ str(batch_size) + " rows, from " + str(initial_ts_int) + " to " +  str(target_ts_int) + ".")
                 
    df1 = pd.DataFrame(np.random.randint(initial_ts_int, target_ts_int, size=(batch_size,1)),  columns=list(["f01"]))
    df2 = pd.DataFrame(np.random.randint(19218983880,19218983880+10,size=(batch_size,1)), columns=list(["f02"])) 
    df4 = pd.DataFrame(np.random.randint(19200000000,19200000000+20000000,size=(batch_size,1)), columns=list(["f04"])) 
    df6 = pd.DataFrame(0, index=range(batch_size),  columns=list(["f06"]))
    df7 = pd.DataFrame(7, index=range(batch_size),  columns=list(["f07"]))
    df10 = pd.DataFrame(np.random.randint(0, 10, size=(batch_size,3)),  columns=list(["f10", "f15", "f19"]))
    df14 = pd.DataFrame(49, index=range(batch_size),  columns=list(["f14"]))
    df22 = pd.DataFrame(3, index=range(batch_size),  columns=list(["f22"]))
    df30 = pd.DataFrame(np.random.randint(initial_ts_int,target_ts_int,size=(batch_size,1)),  columns=list(["f30"]))
    df31 = df30
    df31 = df31.rename(columns={"f30": "f31"})

    for k in random_txtcols: 
        if k == 'f16' :
            np_batchsize =  pd.DataFrame("Great you found me !", index=range(batch_size),  columns=list(["f16"]))
        else :
            np_batchsize = np.random.choice(np.array(alphabet, dtype="|U1"), [batch_size, LENGTH])
            np_batchsize = pd.DataFrame( ["".join(np_batchsize[i]) for i in range(len(np_batchsize))], columns=[k])

        df[k] = np_batchsize

    df = pd.concat([df1,df2, df4, df6, df7, df10, df14, df22, df30, df31, df], axis=1, join='inner')

    df = df[cols]

    logging.info("Memory Usage: " + f'{df.memory_usage(deep=True).sum():,}'  + " Bytes")

    logging.info("creating spark data frame for partitioins from " + str(pd.to_datetime(df['f01'].min(), unit='s')) + ' to ' +  str(pd.to_datetime(df['f01'].max(), unit='s')) + '... ')
    sparkDF = spark.createDataFrame(df)
    sparkDF = sparkDF.withColumn("cp", from_unixtime(sparkDF["f01"], "yyyyMMddHH").cast("BigInt"))
    sparkDF = sparkDF.withColumn("ld", from_unixtime(sparkDF["f01"], "yyyyMMddHH").cast("BigInt"))
    sparkDF = sparkDF.withColumn("f30", from_unixtime(sparkDF["f30"], "yyyyMMddHH").cast("BigInt"))
    sparkDF = sparkDF.withColumn("f31", from_unixtime(sparkDF["f31"], "yyyyMMddHH").cast("BigInt"))
    #sparkDF.coalesce(getNumberOfExecutor()).write.mode("append").partitionBy( ["cp","ld"]).bucketBy(32, "f02").sortBy("f01").format("orc").saveAsTable("tb_test")
    
    logging.info("writing to hive table sample.tb_test ...")
    current_ts = pd.Timestamp.now()
    sparkDF.coalesce(getNumberOfExecutor()).write.mode("append").partitionBy( ["cp","ld"]).format("orc").option("compression","ZLIB").saveAsTable("sample.tb_test")
    finish_ts = pd.Timestamp.now()
    
    spark.catalog.clearCache()
    gc.collect()
    logging.info("finished round " + str(scale_rounds) +  " with batch size "+ str(batch_size) + " rows with " + str( (finish_ts - current_ts).seconds)  + " seconds")

    
def gendata_tbtest(scale = 1, batch_size = 100000, timespan_days = 31):
    
    scale_factor = scale*1024
    scale_unit =  math.ceil(batch_size/(100000/25))
    scale_rounds = math.ceil(scale_factor/scale_unit)
    
    #Testing
    if debugMode :
        logging.warning("Testing with " + str(2) +" rounds data instead of " + str(scale_rounds) +" rounds, remove this by settign debugMode = False in config file.")
        scale_rounds = 2
        
    target_ts=None
    partitions = timespan_days * 24
    current_ts = pd.Timestamp.now()
    
    for i in range(scale_rounds):
        
        if debugMode :            
            for name, size in sorted(((name, sys.getsizeof(value)) for name, value in list(globals().items())), key= lambda x: -x[1])[:10]:
                logging.info("{:>30}: {:>8}".format(name, sizeof_fmt(size)))
            for name, size in sorted(((name, sys.getsizeof(value)) for name, value in list(locals().items())), key= lambda x: -x[1])[:10]:
                logging.info("{:>30}: {:>8}".format(name, sizeof_fmt(size)))
        
        if target_ts is None:
            initial_ts = pd.to_datetime(current_ts - pd.Timedelta(days=timespan_days))
        else:
            initial_ts = target_ts;

        target_ts =  pd.to_datetime(initial_ts + pd.Timedelta(hours=math.ceil(partitions / scale_rounds)))

        gendata_tbtest_noise(initial_ts, target_ts, i, batch_size)
        gendata_tbtest_target(initial_ts, target_ts, i, math.ceil(batch_size/10))

    # Finish data generation for tb_test
    # Then we load the data into tb_serv_u
    logging.info("generating data for tb_servu")
    gendata_tbsevu(scale_rounds, batch_size)
    
    sqlContext.sql("use sample;")
    sqlContext.sql("show tables").show()

def gendata(scale_gb = 1, batch_size = 100, timespan_days = 31):
    logging.info("number_of_workers: " + str(getNumberOfExecutor()) + ".")
    gendata_tbtest(scale_gb, batch_size * 1000, timespan_days )
    
    
def longtask(scale_gb = 1, batch_size = 100, timespan_days = 31, droptTable = False):
    inittask(droptTable)
    gendata(scale_gb, batch_size, timespan_days)
    global taskdone
    taskdone = True

# start the thread pool
t1 = threading.Thread(target=progressbar)
t2 = threading.Thread(target=longtask,  args=(scale, batch, timespan_days, droptable))

# wait for all tasks to complete
# start threads
t1.start()
t2.start()

# wait until threads finish their job
t1.join()
t2.join()

logging.info('Done!')


# In[4]:


logging.info("ANALYZE TABLE sample.tb_test COMPUTE STATISTICS FOR ALL COLUMNS  ;")
sqlContext.sql("ANALYZE TABLE sample.tb_test COMPUTE STATISTICS FOR ALL COLUMNS  ;") 
df = sqlContext.sql("DESCRIBE EXTENDED sample.tb_test;") 
df.show(100,False)


# In[5]:


logging.info("ANALYZE TABLE sample.tb_sev_u COMPUTE STATISTICS FOR ALL COLUMNS  ;")
sqlContext.sql("ANALYZE TABLE sample.tb_sev_u COMPUTE STATISTICS FOR ALL COLUMNS  ;") 
df = sqlContext.sql("DESCRIBE EXTENDED sample.tb_sev_u;") 
df.show(100,False)


# In[6]:


logging.info("create table if not exists sample.tb_test_qf_stat ...")
    
sqlContext.sql("use sample;") 
sqlContext.sql("drop table if exists sample.tb_test_qf_stat");

stmt = """
        create table if not exists sample.tb_test_qf_stat(
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
logging.info("Table sample.tb_test_qf_stat created.")


logging.info("create table if not exists sample.tb_test_qf_stat_log ...")
    
sqlContext.sql("use sample;") 
sqlContext.sql("drop table if exists sample.tb_test_qf_stat_log");

stmt = """
        create table if not exists sample.tb_test_qf_stat_log(
        batchId    string
        )
        ;
       """
logging.info("Executing query: \n" + stmt)
sqlContext.sql(stmt)
logging.info("Table sample.tb_test_qf_stat_log created.")


# In[7]:


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

    
from datetime import datetime
from dateutil.relativedelta import relativedelta
    
today = datetime.now()
date1  = today - relativedelta(days=7)
date2  = today - relativedelta(days=2)
batchId = date2.strftime("%Y%m%d%H")
dateFrom = date1.strftime("%Y%m%d%H")
dateTo = date2.strftime("%Y%m%d%H")

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
;
"""
logging.info("\nExecuting query: \n" + query)
runstarttime = datetime.now()
sqlContext.sql(query) 
runfinishtime = datetime.now()

sqlContext.sql("set hive.exec.dynamic.partition.mode=strict")
logging.info("Finished tb_test_qf_stat Insert Query with " + str( (runfinishtime - runstarttime).seconds)  + " seconds")

query = """
 insert into sample.tb_test_qf_stat_log
 select {batchId}
 from tb_test_qf_tmp1
;
""".format(batchId=str(batchId))

logging.info("\nExecuting query: \n" + query)
sqlContext.sql(query) 
logging.info("\nFinished query: \n" + query)


# df = sqlContext.sql("select * from tb_test_qf_tmp1 ");
# df.show(100, False)

# In[8]:


sqlContext.sql("use sample;") 
query = "drop table if exists sample.tb_test_qf_lastest;"
logging.info("\nExecuting query: \n" + query)
sqlContext.sql(query) 
logging.info("\nFinished query: \n" + query)

query = """
create table  if not exists tb_test_qf_lastest as
select f22,f02,f16,cnt,bd,f06,f07 from
( select *, row_number() over(partition by f02 order by bd desc) rn from sample.tb_test_qf_stat) t
where t.rn =1;
"""

logging.info("\nExecuting query: \n" + query)
runstarttime = datetime.now()
sqlContext.sql(query) 
runfinishtime = datetime.now()
logging.info("Finished Query with " + str( (runfinishtime - runstarttime).seconds)  + " seconds")

query = """select * from tb_test_qf_lastest;""";
logging.info("\nExecuting query: \n" + query)
runstarttime = datetime.now()
df = sqlContext.sql(query) 
df.show(100, False)
runfinishtime = datetime.now()
logging.info("Finished Query with " + str( (runfinishtime - runstarttime).seconds)  + " seconds")


# In[9]:


sqlContext.sql("use sample;") 
df = sqlContext.sql("show tables;") 
df.show(100,False)

query = "drop table if exists sample.tb_test_num_tmp;"
logging.info("\nExecuting query: \n" + query)
sqlContext.sql(query) 

query = """
    create table  if not exists sample.tb_test_num_tmp as
    select f22, f02, min(bd) as f_date, max(bd) as l_date,f06,f07
    from tb_test_qf_tmp1 
    group by f22, f02,f06,f07;
"""


logging.info("\nExecuting query: \n" + query)
runstarttime = datetime.now()
sqlContext.sql(query) 
runfinishtime = datetime.now()
logging.info("Finished Query with " + str( (runfinishtime - runstarttime).seconds)  + " seconds")

query = "drop table if exists sample.tb_test_num_tmp1;"

logging.info("\nExecuting query: \n" + query)
runstarttime = datetime.now()
sqlContext.sql(query) 
runfinishtime = datetime.now()
logging.info("Finished Query with " + str( (runfinishtime - runstarttime).seconds)  + " seconds")

query = """
    create table if not exists sample.tb_test_num
    as
    select t.f22, f02, min(f_date) as f_date, max(l_date) as l_date,f06,f07
    from sample.tb_test_num_tmp as t
    group by t.f22,f02,f06,f07
    limit 1;
"""

logging.info("\nExecuting query: \n" + query)
runstarttime = datetime.now()
sqlContext.sql(query) 
runfinishtime = datetime.now()
logging.info("Finished Query with " + str( (runfinishtime - runstarttime).seconds)  + " seconds")

query = "Truncate table sample.tb_test_num;"
logging.info("\nExecuting query: \n" + query)
runstarttime = datetime.now()
sqlContext.sql(query) 
runfinishtime = datetime.now()
logging.info("Finished Query with " + str( (runfinishtime - runstarttime).seconds)  + " seconds")


query = """
    create table  if not exists sample.tb_test_num_tmp1 as
    select t.f22, f02, min(f_date) as f_date, max(l_date) as l_date,f06,f07
     from
    ( select * from tb_test_num_tmp
    union all
    select * from tb_test_num ) t
    group by t.f22,f02,f06,f07
;"""

logging.info("\nExecuting query: \n" + query)
runstarttime = datetime.now()
sqlContext.sql(query) 
runfinishtime = datetime.now()
logging.info("Finished Query with " + str( (runfinishtime - runstarttime).seconds)  + " seconds")

query = "drop table if exists sample.tb_test_num;"
logging.info("\nExecuting query: \n" + query)
runstarttime = datetime.now()
sqlContext.sql(query) 
runfinishtime = datetime.now()
logging.info("Finished Query with " + str( (runfinishtime - runstarttime).seconds)  + " seconds")

query = " alter table sample.tb_test_num_tmp1 rename to sample.tb_test_num; "
logging.info("\nExecuting query: \n" + query)
runstarttime = datetime.now()
sqlContext.sql(query) 
runfinishtime = datetime.now()
logging.info("Finished Query with " + str( (runfinishtime - runstarttime).seconds)  + " seconds")

query = " select * from sample.tb_test_num; "
logging.info("\nExecuting query: \n" + query)
runstarttime = datetime.now()
df = sqlContext.sql(query) 
df.show(100, False)
runfinishtime = datetime.now()
logging.info("Finished Query with " + str( (runfinishtime - runstarttime).seconds)  + " seconds")


# In[10]:


spark.sparkContext.stop()


# In[ ]:





# In[ ]:





# In[ ]:




