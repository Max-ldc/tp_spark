import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyspark.sql import functions as F
from utils.spark_session import get_spark_session
from jobs.extraction import extract_data
from jobs.extraction_windy import extract_windy_data, get_sample_locations
from jobs.transformation import transform_data, analyze_warming_by_latitude, compare_hemispheres
from jobs.transformation_windy import transform_windy_data, analyze_windy_by_hemisphere, analyze_windy_by_latitude
from jobs.loading import load_data
import config

def main():
    spark = get_spark_session("Meteo")

    print("="*80)
    print("PART 1: HISTORICAL DATA ANALYSIS (CSV)")
    print("="*80)
    
    # 1. Extract historical data
    raw_data_path = config.RAW_DATA_PATH
    df = extract_data(spark, raw_data_path)

    # 2. Transform (Enrichment)
    print("\nEnriching historical data...")
    df_enriched = transform_data(df)
    
    # Cache because we split the pipeline here
    df_enriched.cache()

    # 3. Load Detailed Data
    print("\nLoading detailed enriched data...")
    # NOTE: We removed the .count() here. The write() is the only action we need.
    load_data(df_enriched, config.OUTPUT_PATH_METEO)

    # 4. Display results
    print("\n" + "="*80)
    print("RESULTS SUMMARY")
    print("="*80)
    
    total_records = df_enriched.count()
    print(f"\nTotal records processed: {total_records:,}")
    
    # Show dataset statistics
    num_cities = df_enriched.select("City", "Country").distinct().count()
    num_years = df_enriched.select("year").distinct().count()
    print(f"Number of unique cities: {num_cities:,}")
    print(f"Number of unique years: {num_years}")
    print(f"Average records per city: {total_records / num_cities:.1f}")
    
    # Show anomaly statistics
    anomaly_stats = df_enriched.groupBy("anomaly_type").count().orderBy("count", ascending=False)
    print("\nAnomaly Distribution:")
    anomaly_stats.show()
    
    # Show top 10 hottest years
    print("\nTop 10 Hottest Years (highest positive z-score):")
    df_enriched.filter(df_enriched.is_anomaly == True) \
        .filter(df_enriched.anomaly_type == "Exceptionally Hot") \
        .orderBy("temperature_zscore", ascending=False) \
        .select("year", "City", "Country", "avg_yearly_temperature", "mean_temperature", "stddev_temperature", "temperature_zscore") \
        .limit(10) \
        .show(truncate=False)
    
    # Show top 10 coldest years
    print("\nTop 10 Coldest Years (lowest negative z-score):")
    df_enriched.filter(df_enriched.is_anomaly == True) \
        .filter(df_enriched.anomaly_type == "Exceptionally Cold") \
        .orderBy("temperature_zscore", ascending=True) \
        .select("year", "City", "Country", "avg_yearly_temperature", "mean_temperature", "stddev_temperature", "temperature_zscore") \
        .limit(10) \
        .show(truncate=False)
    
    print("\n" + "="*80)

    df_enriched.unpersist()
    
    # 5. Analyze warming rate by latitude
    print("\n" + "="*80)
    print("WARMING RATE BY LATITUDE ANALYSIS")
    print("="*80)
    
    warming_analysis = analyze_warming_by_latitude(df_enriched)
    
    # Show average warming rate by latitude band
    print("\nAverage Warming Rate by Latitude Band (°C per decade):")
    warming_by_band = warming_analysis.groupBy("latitude_band").agg(
        F.avg("warming_rate_per_decade").alias("avg_warming_rate"),
        F.count("*").alias("num_cities")
    ).orderBy("avg_warming_rate", ascending=False)
    warming_by_band.show(truncate=False)
    
    # Show top 10 fastest warming cities
    print("\nTop 10 Fastest Warming Cities:")
    warming_analysis.orderBy("warming_rate_per_decade", ascending=False) \
        .select("City", "Country", "latitude_numeric", "warming_rate_per_decade", "mean_temp", "first_year", "last_year") \
        .limit(10) \
        .show(truncate=False)
    
    # Show top 10 fastest cooling cities
    print("\nTop 10 Fastest Cooling Cities:")
    warming_analysis.orderBy("warming_rate_per_decade", ascending=True) \
        .select("City", "Country", "latitude_numeric", "warming_rate_per_decade", "mean_temp", "first_year", "last_year") \
        .limit(10) \
        .show(truncate=False)
    
    print("\n" + "="*80)
    
    # 6. Compare hemispheres
    print("\n" + "="*80)
    print("HEMISPHERE COMPARISON (NORTH vs SOUTH)")
    print("="*80)
    
    hemisphere_comparison = compare_hemispheres(df_enriched)
    
    print("\nGeneral Statistics by Hemisphere:")
    hemisphere_comparison["stats"].show(truncate=False)
    
    print("\nAnomaly Distribution by Hemisphere:")
    hemisphere_comparison["anomalies"].orderBy("hemisphere", "anomaly_type").show(truncate=False)
    
    print("\nWarming Rate Comparison (°C per decade):")
    hemisphere_comparison["warming"].show(truncate=False)
    
    print("\n" + "="*80)
    
    # ========================================================================
    # PART 2: WINDY CURRENT DATA ANALYSIS
    # ========================================================================
    
    if config.ENABLE_WINDY_EXTRACTION and config.WINDY_API_KEY != "YOUR_WINDY_API_KEY_HERE":
        print("\n" + "="*80)
        print("PART 2: CURRENT WEATHER DATA ANALYSIS (WINDY API)")
        print("="*80)
        
        # Extract historical statistics for comparison
        print("\nPreparing historical statistics for comparison...")
        historical_stats = df_enriched.groupBy("City", "Country", "latitude_numeric").agg(
            F.avg("avg_yearly_temperature").alias("mean_temperature"),
            F.stddev("avg_yearly_temperature").alias("stddev_temperature")
        ).filter(F.col("stddev_temperature").isNotNull())
        
        # Extract Windy current data
        print("\nExtracting current weather data from Windy API...")
        try:
            locations = get_sample_locations()
            df_windy = extract_windy_data(spark, config.WINDY_API_KEY, locations)
            
            if df_windy.count() > 0:
                print(f"Successfully extracted data for {df_windy.count()} locations from Windy")
                
                # Transform Windy data with anomaly detection
                print("\nAnalyzing current weather vs historical patterns...")
                df_windy_enriched = transform_windy_data(df_windy, historical_stats)
                
                # Display current weather with anomaly status
                print("\nCurrent Weather Conditions:")
                df_windy_enriched.select(
                    "location_name", "temperature_celsius", "mean_temperature", 
                    "temperature_zscore", "anomaly_status", "wind_speed", "pressure"
                ).show(truncate=False)
                
                # Analyze by latitude
                print("\nCurrent Weather by Latitude Band:")
                windy_latitude = analyze_windy_by_latitude(df_windy_enriched)
                windy_latitude.show(truncate=False)
                
                # Analyze by hemisphere
                print("\nCurrent Weather by Hemisphere:")
                windy_hemisphere = analyze_windy_by_hemisphere(df_windy_enriched)
                windy_hemisphere.show(truncate=False)
                
                # Save enriched Windy data
                df_windy_enriched.write.mode("overwrite").parquet(config.OUTPUT_PATH_WINDY)
                print(f"\nWindy analysis saved to {config.OUTPUT_PATH_WINDY}")
                
            else:
                print("No data extracted from Windy API")
        except Exception as e:
            print(f"Error in Windy analysis: {str(e)}")
            import traceback
            traceback.print_exc()
    elif config.ENABLE_WINDY_EXTRACTION:
        print("\n" + "="*80)
        print("Windy extraction enabled but API key not configured.")
        print("Please set your API key in config.py")
        print("Get a free key at: https://api.windy.com/keys")
        print("="*80)
    
    print("\n" + "="*80)
    print("ETL Job Finished Successfully.")
    print("="*80)

    # Pause execution so you can check the Web UI
    input("Press Enter to finish...")
    
    spark.stop()


if __name__ == "__main__":
    main()