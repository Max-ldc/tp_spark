import os
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from typing import List, Dict, Any, Optional


class SparkQueryService:
    """Service pour requêter les données météo ingérées par Spark (stockées en Parquet)."""

    def __init__(self, parquet_path: str = None):
        self.spark = self._create_session()

        # Chemin des fichiers Parquet (là où Spark stocke les données ingérées)
        if parquet_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            parquet_path = os.path.join(base_dir, "data", "parquet")

        self.parquet_path = parquet_path

    def _create_session(self) -> SparkSession:
        """Crée la session Spark."""
        return SparkSession.builder \
            .appName("WeatherQueryService") \
            .master("local[*]") \
            .config("spark.sql.shuffle.partitions", "2") \
            .config("spark.driver.memory", "2g") \
            .getOrCreate()

    def _read_data(self):
        """Lit les données Parquet."""
        return self.spark.read.parquet(self.parquet_path)

    def get_data(self, city: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Récupère les données météo.

        Args:
            city: Filtre optionnel par ville
            limit: Nombre max d'enregistrements
        """
        try:
            df = self._read_data()
        except Exception:
            return []

        if city:
            df = df.filter(F.col("city") == city)

        df = df.orderBy(F.col("timestamp").desc()).limit(limit)

        return [row.asDict() for row in df.collect()]

    def get_stats(self, city: Optional[str] = None) -> Dict[str, Any]:
        """
        Calcule les statistiques agrégées par ville.
        """
        try:
            df = self._read_data()
        except Exception:
            return {"error": "Aucune donnée disponible", "cities": [], "total_records": 0}

        if city:
            df = df.filter(F.col("city") == city)

        stats = df.groupBy("city").agg(
            F.count("*").alias("count"),
            F.round(F.avg("temp"), 2).alias("temp_avg"),
            F.round(F.min("temp"), 2).alias("temp_min"),
            F.round(F.max("temp"), 2).alias("temp_max"),
            F.round(F.avg("wind"), 2).alias("wind_avg"),
            F.round(F.avg("rh"), 2).alias("humidity_avg"),
            F.round(F.avg("pressure"), 2).alias("pressure_avg"),
            F.round(F.avg("clouds"), 2).alias("clouds_avg"),
        ).orderBy("city")

        return {
            "cities": [row.asDict() for row in stats.collect()],
            "total_records": df.count()
        }

    def get_cities(self) -> List[str]:
        """Retourne la liste des villes disponibles."""
        try:
            df = self._read_data()
            cities = df.select("city").distinct().collect()
            return sorted([row.city for row in cities])
        except Exception:
            return []

    def stop(self):
        """Arrête la session Spark."""
        self.spark.stop()


# Instance singleton
_query_service: Optional[SparkQueryService] = None


def get_query_service() -> SparkQueryService:
    """Retourne l'instance singleton du service de requêtage."""
    global _query_service
    if _query_service is None:
        _query_service = SparkQueryService()
    return _query_service
