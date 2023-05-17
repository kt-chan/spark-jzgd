#!/usr/bin/env python
# coding: utf-8

# !pip install --upgrade pip
# !pip3 install --upgrade pandas

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


import threading
from time import sleep

df = pd.DataFrame()   
taskdone = False
alphabet = list('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
LENGTH = 10

def getNumberOfExecutor():
    number_of_workers = len(spark.sparkContext._jsc.sc().statusTracker().getExecutorInfos()) - 1
    return number_of_workers

def progressbar():
    logging.info('Start')
    while not (taskdone):
        sleep(5)
        logging.info('.')

def inittask(droptable = False):
    sqlContext.sql("create database if not exists sample;")
    sqlContext.sql("use sample;")
    
    if(droptable):
        logging.info('dropping sample.* tables')
        sqlContext.sql("drop table if exists sample.tb_test;")
        sqlContext.sql("drop table if exists sample.tb_sev_u;")
        sqlContext.sql("drop table if exists sample.tb_test_qf_stat;")
    

def gendata_tbsevu(scale = 1, batch_size = 100000):
    logging.info("generating data for tb_sev_u ...")
    
    sqlContext.sql("""
        create table sample.tb_sev_u 
        as
        select distinct f02 as id, f03 as name
        from sample.tb_test 
        where f02 < 19218983880 or f02 > 19218983890
        ORDER BY RAND () 
        limit {batch}
    ;""".format(batch=batch_size) )

    logging.info("finished loading data for tb_sev_u with " + str(batch_size) + " rows.")    
    
    
def gendata_tbtest_noise(scale_rounds = 1, batch_size = 100000, timespan_days = 31):
    
    logging.info("generating noise data for tb_test ...")
    ## for 100,000 rows of data with 25MB Storage Data Without Replication
    global df
    target_ts_int=None
    partitions = timespan_days * 24
    
    for i in range(scale_rounds):

        if 'df' in globals():
            del df
        
        df = pd.DataFrame()    
        
        logging.info("running round: " + str(i+1) + " of total " + str(scale_rounds)  +" rounds, with batchsize = " + str(batch_size) + ".")

        df = pd.DataFrame()

        cols=["f01", "f02","f03", "f04", "f05", "f06", "f07", "f08", "f09", "f10","f11","f12","f13","f14","f15","f16","f17","f18","f19","f20","f21","f22","f23","f24","f25","f26","f27","f28","f29","f30","f31" ]
        random_txtcols=["f03","f05","f08","f09","f11","f12","f13","f16","f17","f18","f20","f21","f23","f24","f25","f26","f27","f28","f29"]

        current_ts = pd.Timestamp.now()
        current_ts_int = int(pd.to_datetime(current_ts).value/10**9)
        if target_ts_int is None:
            initial_ts = pd.to_datetime(current_ts - pd.Timedelta(days=timespan_days))
        else:
            initial_ts = target_ts;
        
        target_ts =  pd.to_datetime(initial_ts + pd.Timedelta(hours=math.ceil(partitions / scale_rounds)))
        initial_ts_int =  int(initial_ts.value/10**9)
        target_ts_int =  int(target_ts.value/10**9)
        
        df1 = pd.DataFrame(np.random.randint(initial_ts_int, target_ts_int, size=(batch_size,1)),  columns=list(["f01"]))
        df2 = pd.DataFrame(np.random.randint(19200000000,19200000000+20000000,size=(batch_size,2)), columns=list(["f02", "f04"])) 
        df6 = pd.DataFrame(np.random.randint(0, 10, size=(batch_size,5)),  columns=list(["f06", "f07", "f10", "f15", "f19"]))
        df14 = pd.DataFrame(np.random.randint(48, 51, size=(batch_size,1)),  columns=list(["f14"]))
        df22 = pd.DataFrame(np.random.randint(1, 10, size=(batch_size,1)),  columns=list(["f22"]))
        df30 = pd.DataFrame(initial_ts_int, index=range(batch_size),  columns=list(["f30"]))
        df31 = pd.DataFrame(target_ts_int, index=range(batch_size),  columns=list(["f31"]))

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
        sparkDF = sparkDF.withColumn("cp", from_unixtime(sparkDF["f01"], "yyyyMMddHH"))
        sparkDF = sparkDF.withColumn("ld", from_unixtime(sparkDF["f01"], "yyyyMMddHH"))
        sparkDF = sparkDF.withColumn("f30", from_unixtime(sparkDF["f30"], "yyyyMMddHH"))
        sparkDF = sparkDF.withColumn("f31", from_unixtime(sparkDF["f31"], "yyyyMMddHH"))
        #sparkDF.coalesce(getNumberOfExecutor()).write.mode("append").partitionBy( ["cp","ld"]).bucketBy(32, "f02").sortBy("f01").format("orc").saveAsTable("tb_test")
        logging.info("writing to hive table sample.tb_test ...")
        sparkDF.coalesce(getNumberOfExecutor()).write.mode("append").partitionBy( ["cp","ld"]).format("orc").saveAsTable("tb_test")

        finish_ts = pd.Timestamp.now()
        spark.catalog.clearCache()
        logging.info("finished round: "+ str(i+1) + " for " + str(batch_size) + " rows with " + str( (finish_ts - current_ts).seconds)  + " seconds")

def gendata_tbtest_target(scale_rounds = 1, batch_size = 100000, timespan_days = 31):
    
    logging.info("generating target data for tb_test ...")
    ## for 100,000 rows of data with 25MB Storage Data Without Replication
    global df
    target_ts_int=None
    partitions = timespan_days * 24
    
    for i in range(scale_rounds):
        if 'df' in globals():
            del df

        df = pd.DataFrame()   

        cols=["f01", "f02","f03", "f04", "f05", "f06", "f07", "f08", "f09", "f10","f11","f12","f13","f14","f15","f16","f17","f18","f19","f20","f21","f22","f23","f24","f25","f26","f27","f28","f29","f30","f31" ]
        random_txtcols=["f03","f05","f08","f09","f11","f12","f13","f16","f17","f18","f20","f21","f23","f24","f25","f26","f27","f28","f29"]

        current_ts = pd.Timestamp.now()
        current_ts_int = int(pd.to_datetime(current_ts).value/10**9)
        if target_ts_int is None:
            initial_ts = pd.to_datetime(current_ts - pd.Timedelta(days=timespan_days))
        else:
            initial_ts = target_ts;

        target_ts =  pd.to_datetime(initial_ts + pd.Timedelta(hours=math.ceil(partitions / scale_rounds)))
        initial_ts_int =  int(initial_ts.value/10**9)
        target_ts_int =  int(target_ts.value/10**9)

        ## /*
        ##
        ## +---+-----------+------------------+---+---+---+----------+----------+
        ## |f22|f02        |f16               |cnt|f06|f07|bd        |ad        |
        ## +---+-----------+------------------+---+---+---+----------+----------+
        ## |3  |19218983709|xfhtE3h5CYgGOWhOKk|1  |0  |7  |2023-03-19|2023031415|
        ## |5  |19219966684|ygeEVbANtFFi8Y1hVk|1  |4  |4  |2023-03-19|2023031415|
        ## |3  |19218120415|rUpWrl5GvPKANvoVQA|1  |6  |2  |2023-03-19|2023031415|
        ## |8  |19204926044|giFVrAhopgs0xLBbqC|1  |9  |4  |2023-03-19|2023031415|
        ## |3  |19200131747|WXCnls2FOur2a2eDrx|1  |4  |7  |2023-03-19|2023031415|
        ## |9  |19213837980|Uvsg7bYQhZAddPp4fb|1  |0  |7  |2023-03-19|2023031415|
        ## |8  |19206179720|7KZIluL2WBkkQHI6M4|1  |5  |0  |2023-03-19|2023031415|
        ## |8  |19204624908|MNwN3ensBpDhy08k18|1  |1  |3  |2023-03-19|2023031415|
        ## |1  |19219995818|GVkuR9l4m3ZQQO9duG|1  |5  |4  |2023-03-19|2023031415|
        ## |4  |19219858050|1U2HdpMfVarddjhWNl|1  |0  |6  |2023-03-19|2023031415|
        ## +---+-----------+------------------+---+---+---+----------+----------+
        ## 
        ## */

        df1 = pd.DataFrame(np.random.randint(initial_ts_int, target_ts_int, size=(batch_size,1)),  columns=list(["f01"]))
        df2 = pd.DataFrame(np.random.randint(19218983880,19218983880+10,size=(batch_size,1)), columns=list(["f02"])) 
        df4 = pd.DataFrame(np.random.randint(19200000000,19200000000+20000000,size=(batch_size,1)), columns=list(["f04"])) 
        df6 = pd.DataFrame(0, index=range(batch_size),  columns=list(["f06"]))
        df7 = pd.DataFrame(7, index=range(batch_size),  columns=list(["f07"]))
        df10 = pd.DataFrame(np.random.randint(0, 10, size=(batch_size,3)),  columns=list(["f10", "f15", "f19"]))
        df14 = pd.DataFrame(np.random.randint(48, 51, size=(batch_size,1)),  columns=list(["f14"]))
        df22 = pd.DataFrame(3, index=range(batch_size),  columns=list(["f22"]))
        df30 = pd.DataFrame(np.random.randint(initial_ts_int, target_ts_int, size=(batch_size,2)),  columns=list(["f30", "f31"]))

        for k in random_txtcols: 
            if k == 'f16' :
                np_batchsize =  pd.DataFrame("Great you found me !", index=range(batch_size),  columns=list(["f16"]))
            else :
                np_batchsize = np.random.choice(np.array(alphabet, dtype="|U1"), [batch_size, LENGTH])
                np_batchsize = pd.DataFrame( ["".join(np_batchsize[i]) for i in range(len(np_batchsize))], columns=[k])

            df[k] = np_batchsize

        df = pd.concat([df1,df2, df4, df6, df7, df10,df14, df22, df30, df], axis=1, join='inner')

        df = df[cols]
        
        logging.info("Memory Usage: " + f'{df.memory_usage(deep=True).sum():,}'  + " Bytes")

        logging.info("creating spark data frame for partitioins from " + str(pd.to_datetime(df['f01'].min(), unit='s')) + ' to ' +  str(pd.to_datetime(df['f01'].max(), unit='s')) + '... ')
        sparkDF = spark.createDataFrame(df)
        sparkDF = sparkDF.withColumn("cp", from_unixtime(sparkDF["f01"], "yyyyMMddHH"))
        sparkDF = sparkDF.withColumn("ld", from_unixtime(sparkDF["f01"], "yyyyMMddHH"))
        sparkDF = sparkDF.withColumn("f30", from_unixtime(sparkDF["f30"], "yyyyMMddHH"))
        sparkDF = sparkDF.withColumn("f31", from_unixtime(sparkDF["f31"], "yyyyMMddHH"))
        #sparkDF.coalesce(getNumberOfExecutor()).write.mode("append").partitionBy( ["cp","ld"]).bucketBy(32, "f02").sortBy("f01").format("orc").saveAsTable("tb_test")
        logging.info("writing to hive table sample.tb_test ...")
        sparkDF.coalesce(getNumberOfExecutor()).write.mode("append").partitionBy( ["cp","ld"]).format("orc").saveAsTable("tb_test")

        finish_ts = pd.Timestamp.now()
        spark.catalog.clearCache()
        logging.info("finished " + str(batch_size) + " rows with " + str( (finish_ts - current_ts).seconds)  + " seconds")

    
def gendata_tbtest(scale = 1, batch_size = 100000, timespan_days = 31):
    
    scale_factor = scale*1024
    scale_unit =  math.ceil(batch_size/(100000/25))
    scale_rounds = math.ceil(scale_factor/scale_unit)
    
    
    #Testing
    if debugMode :
        logging.info("Testing with " + str(1) +" batches data instead of " + str(scale_rounds) +" ...., remove this block later.")
        scale_rounds = 1    
            
    gendata_tbtest_noise(scale_rounds, batch_size, timespan_days)
    gendata_tbtest_target(scale_rounds, math.ceil(batch_size/10), timespan_days)
    
    sqlContext.sql("use sample;")
    sqlContext.sql("show tables").show()

def gendata(scale_gb = 1, batch_size_k = 100, timespan_days = 31):
    logging.info("number_of_workers: " + str(getNumberOfExecutor()) + ".")
    gendata_tbtest(scale_gb, batch_size_k * 1000, timespan_days )
    gendata_tbsevu(scale_gb, batch_size_k * 1000)
    
    
def longtask(scale_gb = 1, batch_size_k = 100, timespan_days = 31, droptTable = False):
    inittask(droptTable)
    gendata(scale_gb, batch_size_k, timespan_days)
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


# In[ ]:


logging.info("ANALYZE TABLE sample.tb_test COMPUTE STATISTICS FOR ALL COLUMNS  ;")
sqlContext.sql("ANALYZE TABLE sample.tb_test COMPUTE STATISTICS FOR ALL COLUMNS  ;") 
df = sqlContext.sql("DESCRIBE EXTENDED sample.tb_test;") 
df.show(100,False)


# In[ ]:


logging.info("ANALYZE TABLE sample.tb_sev_u COMPUTE STATISTICS FOR ALL COLUMNS  ;")
sqlContext.sql("ANALYZE TABLE sample.tb_sev_u COMPUTE STATISTICS FOR ALL COLUMNS  ;") 
df = sqlContext.sql("DESCRIBE EXTENDED sample.tb_sev_u;") 
df.show(100,False)


# In[ ]:


spark.sparkContext.stop()


# In[ ]:





# In[ ]:




