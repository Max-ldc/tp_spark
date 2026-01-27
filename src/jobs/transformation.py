from pyspark.sql import DataFrame
from pyspark.sql import functions as F

def transform_global_temperature_by_year(df_global: DataFrame) -> DataFrame:
    """
    Calculates average temperature by year globally.
    Filters out years with less than 6 months of data.
    Input: DataFrame from GlobalTemperatures.csv (must include 'dt' and 'LandAverageTemperature')
    """
    return df_global \
        .filter(F.col("LandAverageTemperature").isNotNull()) \
        .withColumn("year", F.year(F.col("dt"))) \
        .groupBy("year") \
        .agg(
            F.avg("LandAverageTemperature").alias("avg_temperature"),
            F.count("dt").alias("months_count")
        ) \
        .filter(F.col("months_count") >= 6) \
        .drop("months_count") \
        .orderBy("year")

def detect_exceptional_years(df_global_yearly: DataFrame) -> DataFrame:
    """
    Identifies exceptional years (hottest and coldest) based on global average.
    Calculates the overall average and difference from mean.
    """
    # Calculate global mean of the yearly averages
    stats = df_global_yearly.select(F.avg("avg_temperature").alias("global_mean"), F.stddev("avg_temperature").alias("global_std")).collect()[0]
    global_mean = stats["global_mean"]
    global_std = stats["global_std"]

    # Add deviation metrics
    return df_global_yearly \
        .withColumn("global_mean", F.lit(global_mean)) \
        .withColumn("anomaly", F.col("avg_temperature") - F.col("global_mean")) \
        .withColumn("z_score", (F.col("avg_temperature") - global_mean) / global_std) \
        .orderBy(F.abs(F.col("anomaly")).desc())

def transform_temperature_by_latitude_and_year(df_city: DataFrame) -> DataFrame:
    """
    Calculates average temperature partitioned by latitude and year.
    Input: DataFrame from GlobalLandTemperaturesByCity.csv
    """
    return df_city \
        .filter(F.col("AverageTemperature").isNotNull()) \
        .withColumn("year", F.year(F.col("dt"))) \
        .groupBy("year", "Latitude") \
        .agg(F.avg("AverageTemperature").alias("avg_temperature")) \
        .orderBy("year", "Latitude")

def transform_hemisphere_comparison(df_city: DataFrame) -> DataFrame:
    """
    Compares average temperature between Northern and Southern Hemispheres over time.
    Derives hemisphere from Latitude string (e.g. '57.05N' -> North).
    """
    return df_city \
        .filter(F.col("AverageTemperature").isNotNull()) \
        .withColumn("year", F.year(F.col("dt"))) \
        .withColumn("hemisphere", 
            F.when(F.col("Latitude").endswith("N"), "North")
             .when(F.col("Latitude").endswith("S"), "South")
             .otherwise("Unknown")
        ) \
        .groupBy("year", "hemisphere") \
        .agg(F.avg("AverageTemperature").alias("avg_temperature")) \
        .orderBy("year", "hemisphere")
