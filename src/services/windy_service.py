import os
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from typing import List, Dict, Any, Optional


class WindyQueryService:
    """Service pour requêter les données Windy (météo actuelle et streaming)."""

    def __init__(self, current_path: str = None, streaming_path: str = None):
        self.spark = self._create_session()

        # Chemins des données Windy
        if current_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            current_path = os.path.join(base_dir, "data", "processed", "windy_current")
        
        if streaming_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            streaming_path = os.path.join(base_dir, "data", "processed", "windy_streaming")

        self.current_path = current_path
        self.streaming_path = streaming_path

    def _create_session(self) -> SparkSession:
        """Crée la session Spark."""
        return SparkSession.builder \
            .appName("WindyQueryService") \
            .master("local[*]") \
            .config("spark.sql.shuffle.partitions", "2") \
            .config("spark.driver.memory", "1g") \
            .getOrCreate()

    def _read_current_data(self):
        """Lit les données Windy actuelles depuis Parquet."""
        return self.spark.read.parquet(self.current_path)
    
    def _read_streaming_data(self):
        """Lit les données Windy streaming depuis Parquet."""
        return self.spark.read.parquet(self.streaming_path)

    def get_current_weather(self, location: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Récupère les conditions météo actuelles.
        """
        try:
            df = self._read_current_data()
        except Exception:
            return []

        if location:
            df = df.filter(F.col("location_name").contains(location))

        return [row.asDict() for row in df.collect()]

    def get_current_anomalies(self) -> List[Dict[str, Any]]:
        """
        Récupère les anomalies météo actuelles (températures inhabituelles par rapport à l'historique).
        """
        try:
            df = self._read_current_data()
        except Exception:
            return []

        # Filtrer uniquement les anomalies
        df_anomalies = df.filter(
            (F.col("anomaly_status") == "Hot Anomaly") | 
            (F.col("anomaly_status") == "Cold Anomaly")
        ).orderBy(F.abs(F.col("temperature_zscore")).desc())

        return [row.asDict() for row in df_anomalies.collect()]

    def get_current_by_hemisphere(self) -> Dict[str, Any]:
        """
        Statistiques météo actuelles par hémisphère.
        """
        try:
            df = self._read_current_data()
        except Exception:
            return {"error": "Aucune donnée disponible"}

        df_with_hemisphere = df.withColumn(
            "hemisphere",
            F.when(F.col("latitude") > 0, "North")
            .when(F.col("latitude") < 0, "South")
            .otherwise("Equatorial")
        )

        stats = df_with_hemisphere.groupBy("hemisphere").agg(
            F.round(F.avg("temperature_celsius"), 2).alias("avg_temp_celsius"),
            F.round(F.avg("wind_speed"), 2).alias("avg_wind_speed"),
            F.round(F.avg("pressure"), 2).alias("avg_pressure"),
            F.round(F.avg("humidity"), 2).alias("avg_humidity"),
            F.count("*").alias("num_locations"),
            F.sum(F.when(
                (F.col("anomaly_status") == "Hot Anomaly") | 
                (F.col("anomaly_status") == "Cold Anomaly"), 1
            ).otherwise(0)).alias("anomaly_count")
        )

        return {
            "hemispheres": [row.asDict() for row in stats.collect()]
        }

    def get_current_by_latitude(self) -> List[Dict[str, Any]]:
        """
        Statistiques météo actuelles par bande de latitude.
        """
        try:
            df = self._read_current_data()
        except Exception:
            return []

        df_with_bands = df.withColumn(
            "latitude_band",
            F.when(F.col("latitude") >= 60, "Arctic (60°+)")
            .when(F.col("latitude") >= 30, "Northern Temperate (30-60°)")
            .when(F.col("latitude") >= 0, "Tropical North (0-30°)")
            .when(F.col("latitude") >= -30, "Tropical South (0-30°)")
            .when(F.col("latitude") >= -60, "Southern Temperate (30-60°)")
            .otherwise("Antarctic (60°-)")
        )

        stats = df_with_bands.groupBy("latitude_band").agg(
            F.round(F.avg("temperature_celsius"), 2).alias("avg_temp"),
            F.round(F.avg("wind_speed"), 2).alias("avg_wind"),
            F.round(F.avg("pressure"), 2).alias("avg_pressure"),
            F.count("*").alias("num_locations")
        ).orderBy("latitude_band")

        return [row.asDict() for row in stats.collect()]

    def get_streaming_history(self, location: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Récupère l'historique streaming (données collectées en continu).
        """
        try:
            df = self._read_streaming_data()
        except Exception:
            return []

        if location:
            df = df.filter(F.col("location_name").contains(location))

        df = df.orderBy(F.col("timestamp").desc()).limit(limit)

        return [row.asDict() for row in df.collect()]

    def get_streaming_trends(self, location: str, hours: int = 24) -> Dict[str, Any]:
        """
        Analyse les tendances météo sur les N dernières heures pour une localisation.
        """
        try:
            df = self._read_streaming_data()
        except Exception:
            return {"error": "Aucune donnée disponible"}

        from datetime import datetime, timedelta

        cutoff_time = datetime.now() - timedelta(hours=hours)

        df_location = df.filter(
            (F.col("location_name") == location) &
            (F.col("timestamp") >= cutoff_time)
        ).orderBy("timestamp")

        if df_location.count() == 0:
            return {"error": f"Aucune donnée pour {location} sur les {hours} dernières heures"}

        # Calculer les tendances
        stats = df_location.agg(
            F.round(F.avg("temperature_celsius"), 2).alias("avg_temp"),
            F.round(F.min("temperature_celsius"), 2).alias("min_temp"),
            F.round(F.max("temperature_celsius"), 2).alias("max_temp"),
            F.round(F.avg("wind_speed"), 2).alias("avg_wind"),
            F.round(F.max("wind_speed"), 2).alias("max_wind"),
            F.round(F.avg("pressure"), 2).alias("avg_pressure"),
            F.count("*").alias("num_measurements")
        ).collect()[0].asDict()

        # Données temporelles
        time_series = df_location.select(
            "timestamp", "temperature_celsius", "wind_speed", "pressure", "humidity"
        ).orderBy("timestamp").collect()

        return {
            "location": location,
            "period_hours": hours,
            "statistics": stats,
            "time_series": [row.asDict() for row in time_series]
        }

    def get_locations(self) -> List[str]:
        """Retourne la liste des localisations disponibles."""
        try:
            df = self._read_current_data()
            locations = df.select("location_name").distinct().collect()
            return sorted([row.location_name for row in locations])
        except Exception:
            return []

    def stop(self):
        """Arrête la session Spark."""
        self.spark.stop()


# Instance singleton
_windy_service: Optional[WindyQueryService] = None


def get_windy_service() -> WindyQueryService:
    """Retourne l'instance singleton du service Windy."""
    global _windy_service
    if _windy_service is None:
        _windy_service = WindyQueryService()
    return _windy_service
