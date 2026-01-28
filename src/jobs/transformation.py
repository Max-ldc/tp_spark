from pyspark.sql import DataFrame
from pyspark.sql import functions as F

def transform_data(df: DataFrame) -> DataFrame:
    """
    Master transformation function for temperature data.
    Identifies temperature anomalies (exceptionally hot or cold years).
    Simplified approach: aggregate by year first, then detect anomalies.
    """
    # 1. Basic Cleaning
    df_cleaned = clean_data(df)
    
    # 2. Aggregate by year and city (reduces data volume significantly)
    df_yearly = aggregate_yearly_temperatures(df_cleaned)
    
    # 3. Detect anomalies on yearly data
    df_with_anomalies = detect_yearly_anomalies(df_yearly)

    return df_with_anomalies

def clean_data(df: DataFrame) -> DataFrame:
    """
    Standard cleaning: filtering null temperatures and type casting.
    Also extracts numeric latitude/longitude from string format (e.g., "57.05N" -> 57.05, "23.45S" -> -23.45).
    """
    df_cleaned = df.filter(
        F.col("AverageTemperature").isNotNull()
    ).withColumn("AverageTemperature", F.col("AverageTemperature").cast("double")) \
     .withColumn("date", F.to_date(F.col("dt"))) \
     .withColumn("year", F.year(F.col("date"))) \
     .withColumn(
        "latitude_numeric",
        F.when(F.col("Latitude").endswith("N"), 
               F.regexp_replace(F.col("Latitude"), "N", "").cast("double"))
        .when(F.col("Latitude").endswith("S"),
              -F.regexp_replace(F.col("Latitude"), "S", "").cast("double"))
        .otherwise(None)
    ).withColumn(
        "longitude_numeric",
        F.when(F.col("Longitude").endswith("E"), 
               F.regexp_replace(F.col("Longitude"), "E", "").cast("double"))
        .when(F.col("Longitude").endswith("W"),
              -F.regexp_replace(F.col("Longitude"), "W", "").cast("double"))
        .otherwise(None)
    )
    
    return df_cleaned

def aggregate_yearly_temperatures(df: DataFrame) -> DataFrame:
    """
    Aggregate temperatures by year and city.
    This reduces the data volume from 8M rows to ~200K rows.
    """
    df_yearly = df.groupBy("year", "City", "Country", "Latitude", "Longitude", "latitude_numeric", "longitude_numeric").agg(
        F.avg("AverageTemperature").alias("avg_yearly_temperature"),
        F.count("*").alias("months_count")
    ).filter(F.col("months_count") >= 6)  # Keep only years with at least 6 months of data
    
    return df_yearly

def detect_yearly_anomalies(df: DataFrame) -> DataFrame:
    """
    Detects yearly temperature anomalies using aggregated approach.
    Much faster than calculating on monthly data.
    """
    
    # Calculate mean and stddev per city across all years
    city_stats = df.groupBy("City", "Country").agg(
        F.avg("avg_yearly_temperature").alias("mean_temperature"),
        F.stddev("avg_yearly_temperature").alias("stddev_temperature")
    )
    
    # Join with broadcast (city_stats is small)
    df_joined = df.join(F.broadcast(city_stats), on=["City", "Country"], how="left")
    
    # Calculate z-score and flag anomalies
    df_anomalies = df_joined.withColumn(
        "temperature_zscore",
        (F.col("avg_yearly_temperature") - F.col("mean_temperature")) / F.col("stddev_temperature")
    ).withColumn(
        "anomaly_type",
        F.when(F.col("temperature_zscore") > 2, "Exceptionally Hot")
        .when(F.col("temperature_zscore") < -2, "Exceptionally Cold")
        .otherwise("Normal")
    ).withColumn(
        "is_anomaly",
        F.when(F.abs(F.col("temperature_zscore")) > 2, True)
        .otherwise(False)
    )
    
    return df_anomalies

def analyze_warming_by_latitude(df: DataFrame) -> DataFrame:
    """
    Analyzes warming rate by calculating temperature trend (slope) per city.
    Groups results by latitude bands to see which regions warm faster.
    """
    
    # Calculate warming trend per city using simple linear regression approximation
    # Slope = covariance(year, temp) / variance(year)
    city_trends = df.groupBy("City", "Country", "latitude_numeric").agg(
        F.corr("year", "avg_yearly_temperature").alias("correlation"),
        F.stddev("avg_yearly_temperature").alias("temp_stddev"),
        F.stddev("year").alias("year_stddev"),
        F.min("year").alias("first_year"),
        F.max("year").alias("last_year"),
        F.avg("avg_yearly_temperature").alias("mean_temp"),
        F.count("*").alias("num_years")
    ).withColumn(
        "warming_rate_per_decade",
        # warming_rate = correlation * (temp_stddev / year_stddev) * 10
        (F.col("correlation") * F.col("temp_stddev") / F.col("year_stddev")) * 10
    ).withColumn(
        "latitude_band",
        F.when(F.col("latitude_numeric") >= 60, "Arctic (60°+)")
        .when(F.col("latitude_numeric") >= 30, "Northern Temperate (30-60°)")
        .when(F.col("latitude_numeric") >= 0, "Tropical North (0-30°)")
        .when(F.col("latitude_numeric") >= -30, "Tropical South (0-30°)")
        .when(F.col("latitude_numeric") >= -60, "Southern Temperate (30-60°)")
        .otherwise("Antarctic (60°-)")
    ).filter(
        (F.col("num_years") >= 30) & F.col("warming_rate_per_decade").isNotNull()
    )
    
    return city_trends

def compare_hemispheres(df: DataFrame) -> dict:
    """
    Compares temperature patterns between Northern and Southern hemispheres.
    Returns aggregated statistics for comparison.
    """
    
    # Add hemisphere classification
    df_with_hemisphere = df.withColumn(
        "hemisphere",
        F.when(F.col("latitude_numeric") > 0, "Northern")
        .when(F.col("latitude_numeric") < 0, "Southern")
        .otherwise("Equatorial")
    ).filter(F.col("hemisphere").isin("Northern", "Southern"))
    
    # Compare basic temperature statistics
    hemisphere_stats = df_with_hemisphere.groupBy("hemisphere").agg(
        F.avg("avg_yearly_temperature").alias("avg_temperature"),
        F.stddev("avg_yearly_temperature").alias("stddev_temperature"),
        F.count("*").alias("total_records"),
        F.countDistinct("City", "Country").alias("num_cities")
    )
    
    # Compare anomaly counts
    anomaly_comparison = df_with_hemisphere.groupBy("hemisphere", "anomaly_type").agg(
        F.count("*").alias("count")
    )
    
    # Calculate warming trends per hemisphere
    warming_trends = df_with_hemisphere.groupBy("hemisphere", "City", "Country").agg(
        F.corr("year", "avg_yearly_temperature").alias("correlation"),
        F.stddev("avg_yearly_temperature").alias("temp_stddev"),
        F.stddev("year").alias("year_stddev"),
        F.count("*").alias("num_years")
    ).filter(F.col("num_years") >= 30).withColumn(
        "warming_rate_per_decade",
        (F.col("correlation") * F.col("temp_stddev") / F.col("year_stddev")) * 10
    ).filter(F.col("warming_rate_per_decade").isNotNull())
    
    hemisphere_warming = warming_trends.groupBy("hemisphere").agg(
        F.avg("warming_rate_per_decade").alias("avg_warming_rate"),
        F.count("*").alias("num_cities")
    )
    
    return {
        "stats": hemisphere_stats,
        "anomalies": anomaly_comparison,
        "warming": hemisphere_warming
    }

def generate_yearly_anomaly_summary(df: DataFrame) -> DataFrame:
    """
    Aggregates anomalies by year and city to identify which years
    were exceptionally hot or cold overall.
    """
    yearly_summary = df.filter(F.col("is_anomaly") == True).groupBy(
        "year", "City", "Country"
    ).agg(
        F.count("*").alias("anomaly_count"),
        F.avg("AverageTemperature").alias("avg_temperature"),
        F.max("temperature_zscore").alias("max_zscore"),
        F.min("temperature_zscore").alias("min_zscore"),
        F.sum(F.when(F.col("anomaly_type") == "Exceptionally Hot", 1).otherwise(0)).alias("hot_months"),
        F.sum(F.when(F.col("anomaly_type") == "Exceptionally Cold", 1).otherwise(0)).alias("cold_months")
    ).orderBy(F.desc("anomaly_count"))
    
    return yearly_summary
