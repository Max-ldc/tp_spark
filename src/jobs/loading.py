from pyspark.sql import DataFrame

def load_data(df: DataFrame, output_path: str):
    """
    Saves the transformed DataFrame to the specified path in Parquet format.
    The data is partitioned by 'event_date'.
    """
    df.write \
        .mode("overwrite") \
        .partitionBy("event_date") \
        .parquet(output_path)