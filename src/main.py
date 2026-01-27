import os
import sys

import shutil
from pyspark.sql.types import StructType, StructField, DateType, DoubleType, StringType

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.spark_session import get_spark_session
from jobs.extraction import extract_data
from jobs.transformation import (
    transform_global_temperature_by_year,
    transform_temperature_by_latitude_and_year,
    detect_exceptional_years,
    transform_hemisphere_comparison
)
from jobs.loading import load_data

def clear_processed_data(path: str):
    """
    Deletes the processed data directory if it exists to ensure a clean slate.
    """
    if os.path.exists(path):
        print(f"Clearing existing data at {path}...")
        shutil.rmtree(path)
    else:
        print(f"No existing data found at {path}, proceeding.")

def main():
    # --- 0. Pre-run Cleanup ---
    processed_dir = "data/processed"
    clear_processed_data(processed_dir)

    spark = get_spark_session("GlobalTemperatureETL")

    # Define strict schemas to avoid expensive schema inference
    
    # 1. GlobalTemperatures.csv
    # We only map the fields we use or that are essential. 
    # Note: If the file has more columns, they might be ignored or handled depending on CSV options, 
    # but defining the main ones usually works well for performance. 
    # Ideally, we should list all if we want to read all.
    # Here we list what we saw in the header to ensure correct parsing.
    global_schema = StructType([
        StructField("dt", DateType(), True),
        StructField("LandAverageTemperature", DoubleType(), True),
        StructField("LandAverageTemperatureUncertainty", DoubleType(), True),
        StructField("LandMaxTemperature", DoubleType(), True),
        StructField("LandMaxTemperatureUncertainty", DoubleType(), True),
        StructField("LandMinTemperature", DoubleType(), True),
        StructField("LandMinTemperatureUncertainty", DoubleType(), True),
        StructField("LandAndOceanAverageTemperature", DoubleType(), True),
        StructField("LandAndOceanAverageTemperatureUncertainty", DoubleType(), True)
    ])

    # 2. GlobalLandTemperaturesByCity.csv
    city_schema = StructType([
        StructField("dt", DateType(), True),
        StructField("AverageTemperature", DoubleType(), True),
        StructField("AverageTemperatureUncertainty", DoubleType(), True),
        StructField("City", StringType(), True),
        StructField("Country", StringType(), True),
        StructField("Latitude", StringType(), True),
        StructField("Longitude", StringType(), True)
    ])

    # --- 1. Extraction ---
    print("1. Extracting data...")
    df_global = extract_data(spark, "data/raw/GlobalTemperatures.csv", global_schema)
    df_city = extract_data(spark, "data/raw/GlobalLandTemperaturesByCity.csv", city_schema)

    # Optimization: Cache df_city as it is used in multiple transformations
    df_city.cache()

    # --- 2. Transformation & Loading Loop ---
    
    # Transformation 1: Avg Temp by Year (Global)
    print("\nProcessing: Average temperature by year (Global, >6 months data)...")
    df_global_year = transform_global_temperature_by_year(df_global)
    load_data(df_global_year, "data/processed/global_avg_temp_by_year", "parquet")

    # Transformation 1b: Exceptional Years (Anomalies)
    print("\nProcessing: Detecting exceptional years (Anomalies)...")
    df_anomalies = detect_exceptional_years(df_global_year)
    load_data(df_anomalies, "data/processed/global_temp_anomalies", "parquet")

    # Transformation 2: Avg Temp by Latitude and Year
    print("\nProcessing: Average temperature by latitude and year...")
    df_lat_year = transform_temperature_by_latitude_and_year(df_city)
    load_data(df_lat_year, "data/processed/avg_temp_by_latitude_year", "parquet")

    # Transformation 3: Hemisphere Comparison
    print("\nProcessing: Comparing North vs South Hemisphere...")
    df_hemisphere = transform_hemisphere_comparison(df_city)
    load_data(df_hemisphere, "data/processed/hemisphere_comparison", "parquet")

    # Unpersist the cached DataFrame
    df_city.unpersist()

    print("\nETL Job Finished Successfully.")
    spark.stop()

if __name__ == "__main__":
    main()
