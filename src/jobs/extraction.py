from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, LongType, DoubleType, TimestampType

def extract_data(spark: SparkSession, file_path: str) -> DataFrame:
    """
    Reads CSV data using a predefined schema.
    This avoids the expensive 'inferSchema' pass.
    """

    # Define the schema strictly matching the CSV columns
    schema = StructType([
        StructField("event_time", TimestampType(), True),
        StructField("event_type", StringType(), True),
        StructField("product_id", IntegerType(), True),
        StructField("category_id", LongType(), True),
        StructField("category_code", StringType(), True),
        StructField("brand", StringType(), True),
        StructField("price", DoubleType(), True),
        StructField("user_id", IntegerType(), True),
        StructField("user_session", StringType(), True)
    ])

    df = spark.read \
        .option("header", "true") \
        .schema(schema) \
        .csv(file_path)

    return df