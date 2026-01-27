from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.functions import broadcast

def transform_data(df: DataFrame) -> DataFrame:
    """
    Master transformation function.
    """
    # 1. Basic Cleaning (Previous step)
    df_cleaned = clean_data(df)
    
    # 2. Enrichment (New step: Joins and Window-like logic)
    df_enriched = enrich_with_category_stats(df_cleaned)

    return df_enriched

def clean_data(df: DataFrame) -> DataFrame:
    """
    Standard cleaning: filtering and type casting.
    """
    df_cleaned = df.filter(
        (F.col("user_id").isNotNull()) & 
        (F.col("price") >= 0)
    ).fillna({
        "category_code": "unknown",
        "brand": "unknown"
    }).withColumn("event_date", F.to_date(F.col("event_time")))
    
    return df_cleaned

def enrich_with_category_stats(df: DataFrame) -> DataFrame:
    """
    Complex transformation:
    1. Calculates average price per category.
    2. Joins distinct stats back to the main table.
    3. Flags products as 'Premium' or 'Budget'.
    """
    
    # --- Aggregation Step ---
    # Group by category and calculate average price
    # We rename the column immediately to avoid ambiguity during the join
    category_stats = df.groupBy("category_code").agg(
        F.avg("price").alias("avg_category_price")
    )

    # --- Join Step ---
    # We join the original distinct events with the aggregated stats.
    # 'left' join ensures we don't lose events if stats are missing (though unlikely here)
    df_joined = df.join(broadcast(category_stats), on="category_code", how="left")

    # --- Classification Step ---
    # Create a new business column comparing specific price to category average
    df_final = df_joined.withColumn(
        "price_segment",
        F.when(F.col("price") > F.col("avg_category_price"), "Premium")
        .otherwise("Budget")
    )

    return df_final

def generate_user_profile(df: DataFrame) -> DataFrame:
    """
    Multi-level aggregation to create a User Profile.
    Pivots the event_type to create columns: views_count, purchases_count, etc.
    """
    user_profile = df.groupBy("user_id").agg(
        F.count("*").alias("total_activity"),
        F.sum(F.when(F.col("event_type") == "purchase", F.col("price")).otherwise(0)).alias("total_spend"),
        # The Pivot: turns row values ('view', 'cart') into columns
        F.sum(F.when(F.col("event_type") == "view", 1).otherwise(0)).alias("views_count"),
        F.sum(F.when(F.col("event_type") == "cart", 1).otherwise(0)).alias("cart_adds_count"),
        F.sum(F.when(F.col("event_type") == "purchase", 1).otherwise(0)).alias("purchases_count")
    )
    
    return user_profile