from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, DateType

def extract_data(spark: SparkSession, file_path: str) -> DataFrame:
    """
    Reads the GlobalLandTemperaturesByCity CSV file.
    """
    schema = StructType([
        StructField("dt", DateType(), True),
        StructField("AverageTemperature", DoubleType(), True),
        StructField("AverageTemperatureUncertainty", DoubleType(), True),
        StructField("City", StringType(), True),
        StructField("Country", StringType(), True),
        StructField("Latitude", StringType(), True),
        StructField("Longitude", StringType(), True)
    ])

    df = spark.read \
        .option("header", "true") \
        .schema(schema) \
        .csv(file_path)

    return df