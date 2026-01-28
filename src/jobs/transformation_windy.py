from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window

def transform_windy_data(df_windy: DataFrame, df_historical_stats: DataFrame) -> DataFrame:
    """
    Transforms Windy CURRENT data by comparing it with HISTORICAL statistics from CSV.
    
    KEY CONCEPT:
    - Windy data = Current/real-time weather (today's temperature)
    - Historical stats = Long-term averages from CSV (mean temperature 1743-2013)
    - Comparison = Is today's weather exceptional compared to historical patterns?
    
    This function detects if current temperatures are anomalies compared to historical averages.
    Example: If Paris historically averages 12°C in January with stddev 2°C, and Windy 
    shows 20°C today, this is flagged as "Exceptionally Hot" (z-score > 2).
    
    Args:
        df_windy: CURRENT weather data from Windy API (real-time)
        df_historical_stats: HISTORICAL statistics (mean, stddev) per location from CSV (1743-2013)
    
    Returns:
        Enriched Windy data with anomaly detection (comparing current vs historical)
    """
    
    # Convert Windy temperature from Kelvin to Celsius
    # Windy API returns temperature in Kelvin
    df_windy_celsius = df_windy.withColumn(
        "temperature_celsius",
        F.col("temperature") - 273.15
    )
    
    # Join with historical stats (using nearest location match)
    # For simplicity, we'll use a cross join with distance calculation
    # In production, you'd want a more efficient spatial join
    
    df_enriched = df_windy_celsius.crossJoin(
        df_historical_stats.select(
            F.col("City").alias("historical_city"),
            F.col("Country").alias("historical_country"),
            F.col("latitude_numeric").alias("historical_lat"),
            F.col("mean_temperature"),
            F.col("stddev_temperature")
        )
    ).withColumn(
        "distance",
        F.sqrt(
            F.pow(F.col("latitude") - F.col("historical_lat"), 2)
        )
    ).withColumn(
        "row_number",
        F.row_number().over(
            Window.partitionBy("location_name").orderBy("distance")
        )
    ).filter(F.col("row_number") == 1)  # Keep closest match
    
    # Calculate if current temperature is anomaly
    df_with_anomaly = df_enriched.withColumn(
        "temperature_zscore",
        (F.col("temperature_celsius") - F.col("mean_temperature")) / F.col("stddev_temperature")
    ).withColumn(
        "is_current_anomaly",
        F.abs(F.col("temperature_zscore")) > 2
    ).withColumn(
        "anomaly_status",
        F.when(F.col("temperature_zscore") > 2, "Currently Exceptionally Hot")
        .when(F.col("temperature_zscore") < -2, "Currently Exceptionally Cold")
        .otherwise("Normal")
    )
    
    return df_with_anomaly


def analyze_windy_by_hemisphere(df: DataFrame) -> DataFrame:
    """
    Analyzes current Windy data by hemisphere.
    """
    df_with_hemisphere = df.withColumn(
        "hemisphere",
        F.when(F.col("latitude") > 0, "Northern")
        .when(F.col("latitude") < 0, "Southern")
        .otherwise("Equatorial")
    )
    
    hemisphere_stats = df_with_hemisphere.groupBy("hemisphere").agg(
        F.avg("temperature_celsius").alias("avg_current_temp"),
        F.avg("wind_speed").alias("avg_wind_speed"),
        F.avg("pressure").alias("avg_pressure"),
        F.count("*").alias("num_locations"),
        F.sum(F.when(F.col("is_current_anomaly") == True, 1).otherwise(0)).alias("num_anomalies")
    )
    
    return hemisphere_stats


def analyze_windy_by_latitude(df: DataFrame) -> DataFrame:
    """
    Analyzes current Windy data by latitude bands.
    """
    df_with_band = df.withColumn(
        "latitude_band",
        F.when(F.col("latitude") >= 60, "Arctic (60°+)")
        .when(F.col("latitude") >= 30, "Northern Temperate (30-60°)")
        .when(F.col("latitude") >= 0, "Tropical North (0-30°)")
        .when(F.col("latitude") >= -30, "Tropical South (0-30°)")
        .when(F.col("latitude") >= -60, "Southern Temperate (30-60°)")
        .otherwise("Antarctic (60°-)")
    )
    
    latitude_stats = df_with_band.groupBy("latitude_band").agg(
        F.avg("temperature_celsius").alias("avg_current_temp"),
        F.avg("wind_speed").alias("avg_wind_speed"),
        F.count("*").alias("num_locations"),
        F.sum(F.when(F.col("is_current_anomaly") == True, 1).otherwise(0)).alias("num_anomalies")
    )
    
    return latitude_stats
