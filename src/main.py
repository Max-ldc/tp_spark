import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pyspark.sql import functions as F
from utils.spark_session import get_spark_session
from jobs.extraction import extract_data
from jobs.transformation import transform_data, analyze_warming_by_latitude, compare_hemispheres
from jobs.loading import load_data

def main():
    spark = get_spark_session("Meteo")

    # 1. Extract
    # Now faster because of manual schema
    raw_data_path = "data/raw/GlobalLandTemperaturesByCity.csv"
    df = extract_data(spark, raw_data_path)

    # 2. Transform (Enrichment)
    print("Enriching data...")
    df_enriched = transform_data(df)
    
    # Cache because we split the pipeline here
    df_enriched.cache()

    # 3. Load Detailed Data
    print("Loading detailed enriched data...")
    # NOTE: We removed the .count() here. The write() is the only action we need.
    load_data(df_enriched, "data/processed/meteo_enriched")

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
    print("ETL Job Finished Successfully.")

    # Pause execution so you can check the Web UI
    input("Press Enter to finish...")
    
    print("\nÉvolution temporelle (dernières années):")
    df_hemisphere_evolution.filter(F.col("Year") >= 2010).show(20, truncate=False)

    df_cleaned.unpersist()
    print("\nAnalyse terminée.")

    input("Appuyez sur Entrée pour terminer...")
    spark.stop()


if __name__ == "__main__":
    main()