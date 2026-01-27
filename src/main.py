import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.spark_session import get_spark_session
from jobs.extraction import extract_data
from jobs.transformation import transform_data, generate_user_profile
from jobs.loading import load_data

def main():
    spark = get_spark_session("ECommerceETL")

    # 1. Extract
    # Now faster because of manual schema
    raw_data_path = "data/raw/*.csv"
    df = extract_data(spark, raw_data_path)

    # 2. Transform (Enrichment)
    print("Enriching data with Category Stats...")
    df_enriched = transform_data(df)
    
    # Cache because we split the pipeline here
    df_enriched.cache()

    # 3. Load Detailed Data
    print("Loading detailed enriched data...")
    # NOTE: We removed the .count() here. The write() is the only action we need.
    load_data(df_enriched, "data/processed/ecommerce_enriched")

    # 4. Transform (User Aggregation)
    print("Generating User Profiles...")
    df_user_profile = generate_user_profile(df_enriched)
    
    # 5. Load User Data
    print("Loading user profiles...")
    df_user_profile.write.mode("overwrite").parquet("data/processed/user_profiles")

    df_enriched.unpersist()
    print("ETL Job Finished Successfully.")

    # Pause execution so you can check the Web UI
    input("Press Enter to finish...")
    
    spark.stop()

if __name__ == "__main__":
    main()