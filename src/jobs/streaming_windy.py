from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.streaming import StreamingQuery
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType
import requests
import json
from datetime import datetime
import time
import threading
import queue

class WindyStreamSource:
    """
    Custom streaming source for Windy API.
    Polls the API at regular intervals and feeds data into a queue.
    """
    
    def __init__(self, api_key: str, locations: list, poll_interval: int = 60):
        """
        Args:
            api_key: Windy API key
            locations: List of locations to monitor
            poll_interval: Polling interval in seconds (default: 60s)
        """
        self.api_key = api_key
        self.locations = locations
        self.poll_interval = poll_interval
        self.data_queue = queue.Queue()
        self.stop_flag = threading.Event()
        
    def start_polling(self):
        """Start background thread to poll API."""
        self.polling_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.polling_thread.start()
        
    def _poll_loop(self):
        """Background loop that polls Windy API periodically."""
        iteration = 0
        while not self.stop_flag.is_set():
            iteration += 1
            print(f"\n[Streaming] Iteration {iteration} - Fetching data from Windy API...")
            
            batch_data = []
            for location in self.locations:
                try:
                    url = "https://api.windy.com/api/point-forecast/v2"
                    payload = {
                        "lat": location['lat'],
                        "lon": location['lon'],
                        "model": "gfs",
                        "parameters": ["temp", "wind", "pressure", "rh"],
                        "levels": ["surface"],
                        "key": self.api_key
                    }
                    
                    response = requests.post(url, json=payload, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if 'ts' in data and len(data['ts']) > 0:
                            timestamp = datetime.fromtimestamp(data['ts'][0] / 1000)
                            temp_celsius = data.get('temp-surface', [None])[0] - 273.15 if 'temp-surface' in data else None
                            
                            record = {
                                'timestamp': timestamp.isoformat(),
                                'poll_time': datetime.now().isoformat(),
                                'location_name': location.get('name'),
                                'latitude': float(location['lat']),
                                'longitude': float(location['lon']),
                                'temperature_celsius': float(temp_celsius) if temp_celsius is not None else None,
                                'wind_u': float(data.get('wind_u-surface', [None])[0]) if data.get('wind_u-surface', [None])[0] is not None else None,
                                'wind_v': float(data.get('wind_v-surface', [None])[0]) if data.get('wind_v-surface', [None])[0] is not None else None,
                                'pressure': float(data.get('pressure-surface', [None])[0]) if data.get('pressure-surface', [None])[0] is not None else None,
                                'humidity': float(data.get('rh-surface', [None])[0]) if data.get('rh-surface', [None])[0] is not None else None
                            }
                            batch_data.append(json.dumps(record))
                            print(f"  ✓ {location.get('name')}: {temp_celsius:.1f}°C")
                    else:
                        print(f"  ✗ {location.get('name')}: HTTP {response.status_code}")
                        
                except Exception as e:
                    print(f"  ✗ {location.get('name')}: {str(e)}")
            
            # Put batch data into queue
            if batch_data:
                self.data_queue.put("\n".join(batch_data))
                print(f"[Streaming] Queued {len(batch_data)} records")
            
            # Wait for next poll (or stop if requested)
            self.stop_flag.wait(self.poll_interval)
    
    def stop_polling(self):
        """Stop the polling thread."""
        self.stop_flag.set()
        if hasattr(self, 'polling_thread'):
            self.polling_thread.join(timeout=5)


def create_streaming_source(spark: SparkSession, api_key: str, locations: list, 
                            poll_interval: int = 60) -> tuple:
    """
    Creates a Spark Structured Streaming source for Windy API.
    Uses a socket-based approach where data is written to a local socket.
    
    Args:
        spark: SparkSession
        api_key: Windy API key
        locations: List of locations to monitor
        poll_interval: Polling interval in seconds
        
    Returns:
        (streaming_df, wind_source) - The streaming DataFrame and source object
    """
    
    # Define schema for streaming data
    schema = StructType([
        StructField("timestamp", StringType(), True),
        StructField("poll_time", StringType(), True),
        StructField("location_name", StringType(), True),
        StructField("latitude", DoubleType(), True),
        StructField("longitude", DoubleType(), True),
        StructField("temperature_celsius", DoubleType(), True),
        StructField("wind_u", DoubleType(), True),
        StructField("wind_v", DoubleType(), True),
        StructField("pressure", DoubleType(), True),
        StructField("humidity", DoubleType(), True)
    ])
    
    # Create Windy stream source
    windy_source = WindyStreamSource(api_key, locations, poll_interval)
    
    # Start background polling
    windy_source.start_polling()
    
    # For demonstration, we'll use rate source and simulate streaming
    # In production, you'd use a proper streaming source like Kafka
    print("[Streaming] Setting up Spark Structured Streaming...")
    
    return windy_source, schema


def setup_windy_streaming(spark: SparkSession, api_key: str, locations: list,
                          output_path: str, checkpoint_path: str,
                          poll_interval: int = 60) -> tuple:
    """
    Sets up complete Windy streaming pipeline.
    
    Args:
        spark: SparkSession
        api_key: Windy API key
        locations: Locations to monitor
        output_path: Where to write streaming results
        checkpoint_path: Checkpoint location for streaming
        poll_interval: Polling interval in seconds
        
    Returns:
        (streaming_query, windy_source) - The query and source objects
    """
    
    windy_source, schema = create_streaming_source(spark, api_key, locations, poll_interval)
    
    # Create a simple streaming DataFrame using rate source for demo
    # This simulates continuous data flow
    streaming_df = spark.readStream \
        .format("rate") \
        .option("rowsPerSecond", 1) \
        .load() \
        .select(F.current_timestamp().alias("processing_time"))
    
    print(f"[Streaming] Windy streaming initialized")
    print(f"[Streaming] Polling every {poll_interval} seconds")
    print(f"[Streaming] Monitoring {len(locations)} locations")
    
    return streaming_df, windy_source, schema


def process_windy_stream_batch(batch_df: DataFrame, batch_id: int, historical_stats: DataFrame):
    """
    Process each micro-batch of Windy streaming data.
    Compares current temperatures with historical patterns in real-time.
    
    Args:
        batch_df: Micro-batch DataFrame from streaming
        batch_id: Batch identifier
        historical_stats: Historical statistics from CSV for comparison
    """
    from pyspark.sql.window import Window
    
    print(f"\n[Batch {batch_id}] Processing streaming data...")
    
    if batch_df.isEmpty():
        print(f"[Batch {batch_id}] No data to process")
        return
    
    # Join with historical stats using cross join + distance calculation
    # to find the closest matching city (using both latitude AND longitude)
    enriched_df = batch_df.crossJoin(
        F.broadcast(historical_stats.select(
            F.col("City").alias("historical_city"),
            F.col("Country").alias("historical_country"),
            F.col("latitude_numeric").alias("historical_lat"),
            F.col("longitude_numeric").alias("historical_lon"),
            "mean_temperature",
            "stddev_temperature"
        ))
    ).withColumn(
        "distance",
        # Simple Euclidean distance using both lat and lon
        F.sqrt(
            F.pow(F.col("latitude") - F.col("historical_lat"), 2) +
            F.pow(F.col("longitude") - F.col("historical_lon"), 2)
        )
    ).withColumn(
        "row_num",
        F.row_number().over(
            Window.partitionBy("location_name").orderBy("distance")
        )
    ).filter(F.col("row_num") == 1)  # Keep only closest match
    
    # Calculate z-score for anomaly detection
    anomaly_df = enriched_df.withColumn(
        "temperature_zscore",
        (F.col("temperature_celsius") - F.col("mean_temperature")) / F.col("stddev_temperature")
    ).withColumn(
        "is_anomaly",
        F.abs(F.col("temperature_zscore")) > 2
    ).withColumn(
        "anomaly_status",
        F.when(F.col("temperature_zscore") > 2, "🔥 Exceptionally Hot")
        .when(F.col("temperature_zscore") < -2, "❄️ Exceptionally Cold")
        .otherwise("✓ Normal")
    )
    
    # Display results
    print(f"\n[Batch {batch_id}] Real-time Weather Analysis:")
    print("Historical avg = Average temperature of this city from 1743-2013 (CSV data)")
    print("Z-score = (Current temp - Historical avg) / Standard deviation")
    print()
    anomaly_df.select(
        "location_name",
        F.concat(F.col("historical_city"), F.lit(" ("), F.col("historical_country"), F.lit(")")).alias("matched_city"),
        F.round("temperature_celsius", 1).alias("current_temp"),
        F.round("mean_temperature", 1).alias("historical_avg"),
        F.round("stddev_temperature", 2).alias("std_dev"),
        F.round("temperature_zscore", 2).alias("z_score"),
        "anomaly_status"
    ).show(truncate=False)
    
    # Count anomalies
    anomaly_count = anomaly_df.filter(F.col("is_anomaly") == True).count()
    total_count = anomaly_df.count()
    print(f"[Batch {batch_id}] Anomalies detected: {anomaly_count}/{total_count}")
    
    # Persist results to Parquet with consistent schema and partitioning
    output_base_path = "data/processed/windy_streaming"
    
    # Harmonize column names to match CSV schema
    harmonized_df = anomaly_df.select(
        F.to_date(F.col("poll_time")).alias("date"),
        F.col("historical_city").alias("City"),
        F.col("historical_country").alias("Country"),
        F.col("latitude").alias("latitude_numeric"),
        F.col("longitude").alias("longitude_numeric"),
        F.col("temperature_celsius").alias("temperature"),
        F.col("mean_temperature").alias("historical_mean_temperature"),
        F.col("stddev_temperature").alias("historical_stddev_temperature"),
        F.col("temperature_zscore"),
        F.col("is_anomaly"),
        F.col("anomaly_status"),
        # Windy-specific columns
        F.col("location_name"),
        F.col("poll_time").alias("timestamp"),
        F.col("wind_u"),
        F.col("wind_v"),
        F.col("pressure"),
        F.col("humidity")
    )
    
    # Partition by Country like the CSV data
    harmonized_df.write \
        .mode("append") \
        .partitionBy("Country") \
        .parquet(output_base_path)
    
    print(f"[Batch {batch_id}] Results saved to {output_base_path} (partitioned by Country)")
