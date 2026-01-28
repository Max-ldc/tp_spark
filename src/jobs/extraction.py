from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.types import StructType, StructField, StringType

def extract_data(spark: SparkSession, file_path: str) -> DataFrame:
    """
    Reads CSV data by dynamically creating schema from CSV headers.
    All columns are read as StringType.
    """

    # Read the first line to get headers
    with open(file_path, 'r') as f:
        headers = f.readline().strip().split(',')
    
    # Create schema dynamically from headers
    schema = StructType([
        StructField(header, StringType(), True) for header in headers
    ])

    df = spark.read \
        .option("header", "true") \
        .schema(schema) \
        .csv(file_path)

    return df