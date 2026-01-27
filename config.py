"""
Configuration file for the Spark ETL pipeline.
Store your API keys and configuration here.
"""

# Windy API Configuration
# Get your free API key from: https://api.windy.com/keys
WINDY_API_KEY = "dT9rNPplqAZyl62aipk8KIT2ygokOZMR"  # Remplacez par votre vraie clé

# Set to True to enable Windy data extraction
# NOTE: Windy provides CURRENT/REAL-TIME weather data, not historical data
# The pipeline will compare current Windy data against historical CSV statistics
# to detect if today's weather is anomalous compared to long-term patterns
ENABLE_WINDY_EXTRACTION = True  # Changé de False à True

# Data paths
RAW_DATA_PATH = "data/raw/GlobalLandTemperaturesByCity.csv"
OUTPUT_PATH_METEO = "data/processed/meteo_enriched"
OUTPUT_PATH_WINDY = "data/processed/windy_current"
OUTPUT_PATH_WINDY_STREAMING = "data/processed/windy_streaming"

# Streaming configuration
WINDY_POLL_INTERVAL = 60  # seconds between API calls in streaming mode
STREAMING_OUTPUT_PATH = "data/streaming/windy_output"
STREAMING_CHECKPOINT_PATH = "data/streaming/checkpoints"
