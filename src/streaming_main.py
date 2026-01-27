"""
Streaming ETL Pipeline for Windy API
Continuously polls Windy API and processes data in real-time.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyspark.sql import functions as F
from utils.spark_session import get_spark_session
from jobs.streaming_windy import setup_windy_streaming
from jobs.extraction_windy import get_sample_locations
import config
import time

def main():
    print("="*80)
    print("WINDY API - STREAMING MODE")
    print("="*80)
    
    if not config.ENABLE_WINDY_EXTRACTION:
        print("Windy extraction is disabled in config.py")
        print("Set ENABLE_WINDY_EXTRACTION = True to enable")
        return
        
    if config.WINDY_API_KEY == "YOUR_WINDY_API_KEY_HERE":
        print("Please configure your Windy API key in config.py")
        print("Get a free key at: https://api.windy.com/keys")
        return
    
    # Create Spark session with streaming support
    spark = get_spark_session("WindyStreaming")
    
    # Configuration
    locations = get_sample_locations()
    poll_interval = 60  # Poll API every 60 seconds
    output_path = "data/streaming/windy_output"
    checkpoint_path = "data/streaming/checkpoints"
    
    print(f"\nConfiguration:")
    print(f"  Locations: {len(locations)}")
    print(f"  Poll interval: {poll_interval} seconds")
    print(f"  Output: {output_path}")
    
    # Load historical statistics for comparison
    print("\n" + "="*80)
    print("LOADING HISTORICAL DATA FOR COMPARISON")
    print("="*80)
    
    from jobs.extraction import extract_data
    from jobs.transformation import transform_data
    
    print("Loading historical temperature data...")
    df_historical = extract_data(spark, config.RAW_DATA_PATH)
    df_transformed = transform_data(df_historical)
    
    # Calculate historical statistics per city
    historical_stats = df_transformed.groupBy("City", "Country", "latitude_numeric", "longitude_numeric").agg(
        F.avg("avg_yearly_temperature").alias("mean_temperature"),
        F.stddev("avg_yearly_temperature").alias("stddev_temperature")
    ).filter(F.col("stddev_temperature").isNotNull())
    
    historical_stats.cache()
    print(f"Loaded statistics for {historical_stats.count()} cities")
    
    # Setup streaming
    print("\n" + "="*80)
    print("STARTING STREAMING PIPELINE")
    print("="*80)
    
    streaming_df, windy_source, schema = setup_windy_streaming(
        spark, 
        config.WINDY_API_KEY, 
        locations,
        output_path,
        checkpoint_path,
        poll_interval
    )
    
    print("\n[Streaming] Pipeline running...")
    print("[Streaming] Comparing real-time data with historical patterns...")
    print("[Streaming] Press Ctrl+C to stop\n")
    
    try:
        # Keep the main thread alive and monitor the stream
        iteration = 0
        while True:
            iteration += 1
            time.sleep(poll_interval)
            
            # Get data from queue if available
            if not windy_source.data_queue.empty():
                batch = windy_source.data_queue.get()
                records = batch.split('\n')
                
                # Parse JSON records and create DataFrame
                import json as json_lib
                parsed_records = [json_lib.loads(r) for r in records]
                
                if parsed_records:
                    batch_df = spark.createDataFrame(parsed_records, schema)
                    
                    # Process batch with historical comparison
                    from jobs.streaming_windy import process_windy_stream_batch
                    process_windy_stream_batch(batch_df, iteration, historical_stats)
                
    except KeyboardInterrupt:
        print("\n\n[Streaming] Stopping...")
        windy_source.stop_polling()
        historical_stats.unpersist()
        spark.stop()
        print("[Streaming] Stopped successfully")

if __name__ == "__main__":
    main()
