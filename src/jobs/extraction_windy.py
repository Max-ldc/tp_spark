from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType
import requests
import json
import math
from datetime import datetime, timedelta

def extract_windy_data(spark: SparkSession, api_key: str, locations: list) -> DataFrame:
    """
    Extracts CURRENT weather data from Windy API for specified locations.
    
    IMPORTANT: This API provides REAL-TIME/FORECAST data, NOT historical data.
    The extracted data represents current weather conditions at the time of extraction.
    This is different from the CSV which contains historical monthly averages (1743-2013).
    
    Use case: Compare current weather conditions against historical patterns to detect
    if today's temperatures are anomalies compared to long-term averages.
    
    Args:
        spark: SparkSession instance
        api_key: Windy API key (get one from https://api.windy.com/keys)
        locations: List of dictionaries with 'lat', 'lon', 'name' keys
    
    Returns:
        DataFrame with CURRENT weather data from Windy (temperature, wind, pressure, etc.)
    """
    
    # Define schema for Windy CURRENT data
    schema = StructType([
        StructField("timestamp", TimestampType(), True),
        StructField("location_name", StringType(), True),
        StructField("latitude", DoubleType(), True),
        StructField("longitude", DoubleType(), True),
        StructField("temperature", DoubleType(), True),  # Current temperature (Kelvin or Celsius)
        StructField("wind_speed", DoubleType(), True),
        StructField("wind_direction", DoubleType(), True),
        StructField("pressure", DoubleType(), True),
        StructField("humidity", DoubleType(), True),
        StructField("weather_condition", StringType(), True)
    ])
    
    # Collect data from API
    weather_data = []
    
    print(f"Fetching CURRENT weather for {len(locations)} locations...")
    
    for location in locations:
        try:
            # Windy Point Forecast API endpoint - provides CURRENT + FORECAST data
            url = "https://api.windy.com/api/point-forecast/v2"
            
            payload = {
                "lat": location['lat'],
                "lon": location['lon'],
                "model": "gfs",  # Global Forecast System
                "parameters": ["temp", "wind", "pressure", "rh"],
                "levels": ["surface"],  # Important: must specify levels
                "key": api_key
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract current values (first timestamp)
                if 'ts' in data and len(data['ts']) > 0:
                    timestamp = datetime.fromtimestamp(data['ts'][0] / 1000)
                    
                    # Extract wind components and calculate magnitude
                    wind_u = data.get('wind_u-surface', [None])[0]
                    wind_v = data.get('wind_v-surface', [None])[0]
                    
                    if wind_u is not None and wind_v is not None:
                        # Calculate wind speed magnitude from u and v components
                        wind_speed = (wind_u**2 + wind_v**2)**0.5
                        # Calculate wind direction (meteorological convention: direction FROM which wind blows)
                        wind_direction = (270 - math.degrees(math.atan2(wind_v, wind_u))) % 360
                    else:
                        wind_speed = None
                        wind_direction = None
                    
                    # According to API docs, parameters are returned as "parameter-level" format
                    weather_data.append({
                        'timestamp': timestamp,
                        'location_name': location.get('name', f"Lat{location['lat']}_Lon{location['lon']}"),
                        'latitude': location['lat'],
                        'longitude': location['lon'],
                        'temperature': data.get('temp-surface', [None])[0] if 'temp-surface' in data else None,
                        'wind_speed': wind_speed,
                        'wind_direction': wind_direction,
                        'pressure': data.get('pressure-surface', [None])[0] if 'pressure-surface' in data else None,
                        'humidity': data.get('rh-surface', [None])[0] if 'rh-surface' in data else None,
                        'weather_condition': 'unknown'
                    })
                    # Convert Kelvin to Celsius for display
                    temp_celsius = data.get('temp-surface', [None])[0] - 273.15 if 'temp-surface' in data and data.get('temp-surface', [None])[0] else None
                    print(f"  ✓ {location.get('name')}: {temp_celsius:.1f}°C" if temp_celsius else f"  ✓ {location.get('name')}: data retrieved")
            else:
                print(f"Failed to fetch data for {location.get('name')}: Status {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"  Error details: {error_detail}")
                except:
                    print(f"  Response text: {response.text[:200]}")
                
        except Exception as e:
            print(f"Error fetching data for {location.get('name')}: {str(e)}")
    
    # Create DataFrame from collected data
    if weather_data:
        df = spark.createDataFrame(weather_data, schema)
        return df
    else:
        # Return empty DataFrame with schema if no data
        return spark.createDataFrame([], schema)


def get_sample_locations():
    """
    Returns a list of sample locations for testing.
    You can customize this list based on your needs.
    """
    return [
        {'lat': 48.8566, 'lon': 2.3522, 'name': 'Paris'},
        {'lat': 51.5074, 'lon': -0.1278, 'name': 'London'},
        {'lat': 40.7128, 'lon': -74.0060, 'name': 'New York'},
        {'lat': 35.6762, 'lon': 139.6503, 'name': 'Tokyo'},
        {'lat': -33.8688, 'lon': 151.2093, 'name': 'Sydney'},
        {'lat': 55.7558, 'lon': 37.6173, 'name': 'Moscow'},
        {'lat': 52.5200, 'lon': 13.4050, 'name': 'Berlin'},
        {'lat': 41.9028, 'lon': 12.4964, 'name': 'Rome'},
        {'lat': 39.9042, 'lon': 116.4074, 'name': 'Beijing'},
        {'lat': -23.5505, 'lon': -46.6333, 'name': 'São Paulo'}
    ]
