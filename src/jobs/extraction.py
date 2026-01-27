from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.types import StructType

def extract_data(spark: SparkSession, file_path: str, schema: StructType = None) -> DataFrame:
    """
    Reads CSV data.
    If a schema is provided, key-value pairs are enforced.
    Otherwise, inferSchema is used (slower but adapts to new data).
    """

    reader = spark.read \
        .option("header", "true")

    if schema:
        reader = reader.schema(schema)
    else:
        # Default behavior: infer schema to adapt to new datasets
        reader = reader.option("inferSchema", "true")

    df = reader.csv(file_path)

    return df