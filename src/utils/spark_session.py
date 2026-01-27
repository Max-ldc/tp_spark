from pyspark.sql import SparkSession

def get_spark_session(app_name: str) -> SparkSession:
    """
    Creates or gets a Spark Session.
    """
    spark = SparkSession.builder \
        .appName(app_name) \
        .config("spark.driver.memory", "4g") \
        .config("spark.sql.shuffle.partitions", "8") \
        .getOrCreate()
    
    # Set log level to WARN to reduce clutter in the console
    spark.sparkContext.setLogLevel("WARN")
    
    return spark