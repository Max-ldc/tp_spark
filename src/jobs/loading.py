from pyspark.sql import DataFrame
from pyspark.sql import functions as F

def load_data(df: DataFrame, output_path: str):
    """
    Saves the transformed DataFrame to the specified path in Parquet format.
    The data is partitioned by 'Country' for efficient querying.
    Column names are harmonized for consistency with streaming data.
    """
    
    # Harmonize column names for consistency
    harmonized_df = df.select(
        F.col("year"),
        F.col("City"),
        F.col("Country"),
        F.col("latitude_numeric"),
        F.col("longitude_numeric"),
        F.col("avg_yearly_temperature").alias("temperature"),
        F.col("mean_temperature").alias("historical_mean_temperature"),
        F.col("stddev_temperature").alias("historical_stddev_temperature"),
        F.col("temperature_zscore"),
        F.col("is_anomaly"),
        F.col("anomaly_type").alias("anomaly_status"),
        # CSV-specific columns
        F.col("months_count")
    )
    
    harmonized_df.write \
        .mode("overwrite") \
        .partitionBy("Country") \
        .parquet(output_path)