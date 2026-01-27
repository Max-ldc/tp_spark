from pyspark.sql import DataFrame

def load_data(df: DataFrame, output_path: str):
    """
    Saves the transformed DataFrame to the specified path in Parquet format.
    The data is partitioned by 'Country' for efficient querying.
    """
    df.write \
        .mode("overwrite") \
        .partitionBy("Country") \
        .parquet(output_path)