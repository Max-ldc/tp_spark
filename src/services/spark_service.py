import os
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from typing import List, Dict, Any, Optional


class SparkQueryService:
    """Service pour requêter les données température enrichies (stockées en Parquet)."""

    def __init__(self, parquet_path: str = None):
        self.spark = self._create_session()

        # Chemin des fichiers Parquet (là où le job ETL stocke les données)
        if parquet_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            parquet_path = os.path.join(base_dir, "data", "processed", "meteo_enriched")

        self.parquet_path = parquet_path

    def _create_session(self) -> SparkSession:
        """Crée la session Spark."""
        return SparkSession.builder \
            .appName("TemperatureQueryService") \
            .master("local[*]") \
            .config("spark.sql.shuffle.partitions", "2") \
            .config("spark.driver.memory", "2g") \
            .getOrCreate()

    def _read_data(self):
        """Lit les données Parquet."""
        return self.spark.read.parquet(self.parquet_path)

    def get_data(self, city: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Récupère les données température.
        """
        try:
            df = self._read_data()
        except Exception:
            return []

        if city:
            df = df.filter(F.col("City") == city)

        df = df.orderBy(F.col("year").desc()).limit(limit)

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
            df = df.filter(F.col("City") == city)

        stats = df.groupBy("City", "Country").agg(
            F.count("*").alias("count"),
            F.round(F.avg("avg_yearly_temperature"), 2).alias("temp_avg"),
            F.round(F.min("avg_yearly_temperature"), 2).alias("temp_min"),
            F.round(F.max("avg_yearly_temperature"), 2).alias("temp_max"),
            F.min("year").alias("year_min"),
            F.max("year").alias("year_max"),
            F.sum(F.when(F.col("is_anomaly") == True, 1).otherwise(0)).alias("anomaly_count"),
        ).orderBy("City")

        return {
            "cities": [row.asDict() for row in stats.collect()],
            "total_records": df.count()
        }

    def get_cities(self) -> List[str]:
        """Retourne la liste des villes disponibles."""
        try:
            df = self._read_data()
            cities = df.select("City").distinct().collect()
            return sorted([row.City for row in cities])
        except Exception:
            return []

    def get_anomalies(self, anomaly_type: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Récupère les anomalies de température.
        anomaly_type: "Exceptionally Hot" ou "Exceptionally Cold"
        """
        try:
            df = self._read_data()
        except Exception:
            return []

        df = df.filter(F.col("is_anomaly") == True)

        if anomaly_type:
            df = df.filter(F.col("anomaly_type") == anomaly_type)

        df = df.orderBy(F.abs(F.col("temperature_zscore")).desc()).limit(limit)

        return [row.asDict() for row in df.collect()]

    def get_years(self) -> List[int]:
        """Retourne la liste des années disponibles."""
        try:
            df = self._read_data()
            years = df.select("year").distinct().orderBy("year").collect()
            return [row.year for row in years]
        except Exception:
            return []

    def get_countries(self) -> List[str]:
        """Retourne la liste des pays disponibles."""
        try:
            df = self._read_data()
            countries = df.select("Country").distinct().collect()
            return sorted([row.Country for row in countries])
        except Exception:
            return []

    def get_data_by_year(self, year: int, limit: int = 1000) -> List[Dict[str, Any]]:
        """Récupère les données pour une année spécifique."""
        try:
            df = self._read_data()
        except Exception:
            return []

        df = df.filter(F.col("year") == year).orderBy("City").limit(limit)
        return [row.asDict() for row in df.collect()]

    def get_data_by_country(self, country: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """Récupère les données pour un pays spécifique."""
        try:
            df = self._read_data()
        except Exception:
            return []

        df = df.filter(F.col("Country") == country).orderBy(F.col("year").desc()).limit(limit)
        return [row.asDict() for row in df.collect()]

    def get_warming_top(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retourne les villes qui se réchauffent le plus vite."""
        try:
            df = self._read_data()
        except Exception:
            return []

        # Calculer la tendance de réchauffement par ville
        warming = df.groupBy("City", "Country", "latitude_numeric").agg(
            F.corr("year", "avg_yearly_temperature").alias("correlation"),
            F.stddev("avg_yearly_temperature").alias("temp_stddev"),
            F.stddev("year").alias("year_stddev"),
            F.min("year").alias("first_year"),
            F.max("year").alias("last_year"),
            F.avg("avg_yearly_temperature").alias("mean_temp"),
            F.count("*").alias("num_years")
        ).filter(F.col("num_years") >= 30).withColumn(
            "warming_rate_per_decade",
            F.round((F.col("correlation") * F.col("temp_stddev") / F.col("year_stddev")) * 10, 4)
        ).filter(F.col("warming_rate_per_decade").isNotNull())

        # Top réchauffement
        top = warming.orderBy(F.col("warming_rate_per_decade").desc()).limit(limit)
        return [row.asDict() for row in top.collect()]

    def get_warming_cooling(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retourne les villes qui refroidissent."""
        try:
            df = self._read_data()
        except Exception:
            return []

        warming = df.groupBy("City", "Country", "latitude_numeric").agg(
            F.corr("year", "avg_yearly_temperature").alias("correlation"),
            F.stddev("avg_yearly_temperature").alias("temp_stddev"),
            F.stddev("year").alias("year_stddev"),
            F.min("year").alias("first_year"),
            F.max("year").alias("last_year"),
            F.avg("avg_yearly_temperature").alias("mean_temp"),
            F.count("*").alias("num_years")
        ).filter(F.col("num_years") >= 30).withColumn(
            "warming_rate_per_decade",
            F.round((F.col("correlation") * F.col("temp_stddev") / F.col("year_stddev")) * 10, 4)
        ).filter(F.col("warming_rate_per_decade").isNotNull())

        # Top refroidissement (valeurs négatives)
        cooling = warming.filter(F.col("warming_rate_per_decade") < 0) \
            .orderBy(F.col("warming_rate_per_decade").asc()).limit(limit)
        return [row.asDict() for row in cooling.collect()]

    def get_hemispheres_comparison(self) -> Dict[str, Any]:
        """Compare les hémisphères Nord et Sud."""
        try:
            df = self._read_data()
        except Exception:
            return {"error": "Aucune donnée disponible"}

        df_with_hemisphere = df.withColumn(
            "hemisphere",
            F.when(F.col("latitude_numeric") > 0, "North")
            .when(F.col("latitude_numeric") < 0, "South")
            .otherwise("Equatorial")
        ).filter(F.col("hemisphere").isin("North", "South"))

        stats = df_with_hemisphere.groupBy("hemisphere").agg(
            F.round(F.avg("avg_yearly_temperature"), 2).alias("avg_temp"),
            F.round(F.stddev("avg_yearly_temperature"), 2).alias("stddev_temp"),
            F.countDistinct("City").alias("num_cities"),
            F.count("*").alias("total_records"),
            F.sum(F.when(F.col("is_anomaly") == True, 1).otherwise(0)).alias("anomaly_count")
        )

        return {
            "hemispheres": [row.asDict() for row in stats.collect()]
        }

    def get_latitude_bands(self) -> Dict[str, Any]:
        """Statistiques par bande de latitude."""
        try:
            df = self._read_data()
        except Exception:
            return {"error": "Aucune donnée disponible"}

        df_with_bands = df.withColumn(
            "latitude_band",
            F.when(F.col("latitude_numeric") >= 60, "Arctic (60°+)")
            .when(F.col("latitude_numeric") >= 30, "Northern Temperate (30-60°)")
            .when(F.col("latitude_numeric") >= 0, "Tropical North (0-30°)")
            .when(F.col("latitude_numeric") >= -30, "Tropical South (0-30°)")
            .when(F.col("latitude_numeric") >= -60, "Southern Temperate (30-60°)")
            .otherwise("Antarctic (60°-)")
        )

        stats = df_with_bands.groupBy("latitude_band").agg(
            F.round(F.avg("avg_yearly_temperature"), 2).alias("avg_temp"),
            F.round(F.min("avg_yearly_temperature"), 2).alias("min_temp"),
            F.round(F.max("avg_yearly_temperature"), 2).alias("max_temp"),
            F.countDistinct("City").alias("num_cities"),
            F.count("*").alias("total_records")
        ).orderBy("latitude_band")

        return {
            "latitude_bands": [row.asDict() for row in stats.collect()]
        }

    def search_cities(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Recherche de villes par nom partiel."""
        try:
            df = self._read_data()
        except Exception:
            return []

        cities = df.filter(F.lower(F.col("City")).contains(query.lower())) \
            .select("City", "Country").distinct() \
            .orderBy("City").limit(limit)

        return [row.asDict() for row in cities.collect()]

    def get_latest_data(self, limit: int = 100) -> Dict[str, Any]:
        """
        Récupère les données les plus récentes (dernière année disponible).
        """
        try:
            df = self._read_data()
        except Exception:
            return {"error": "Aucune donnée disponible", "data": []}

        # Trouver l'année la plus récente
        max_year = df.agg(F.max("year")).collect()[0][0]

        if max_year is None:
            return {"error": "Aucune donnée disponible", "data": []}

        df_latest = df.filter(F.col("year") == max_year).orderBy("City").limit(limit)

        return {
            "latest_year": max_year,
            "count": df_latest.count(),
            "data": [row.asDict() for row in df_latest.collect()]
        }

    def get_recent_years(self, num_years: int = 5, limit: int = 500) -> Dict[str, Any]:
        """
        Récupère les données des N dernières années.
        """
        try:
            df = self._read_data()
        except Exception:
            return {"error": "Aucune donnée disponible", "data": []}

        # Trouver les N années les plus récentes
        max_year = df.agg(F.max("year")).collect()[0][0]

        if max_year is None:
            return {"error": "Aucune donnée disponible", "data": []}

        min_year_filter = max_year - num_years + 1
        df_recent = df.filter(F.col("year") >= min_year_filter) \
            .orderBy(F.col("year").desc(), "City").limit(limit)

        return {
            "year_range": {"from": min_year_filter, "to": max_year},
            "count": df_recent.count(),
            "data": [row.asDict() for row in df_recent.collect()]
        }

    def get_recent_summary(self) -> Dict[str, Any]:
        """
        Résumé des données récentes : stats par année pour les 10 dernières années.
        """
        try:
            df = self._read_data()
        except Exception:
            return {"error": "Aucune donnée disponible"}

        max_year = df.agg(F.max("year")).collect()[0][0]

        if max_year is None:
            return {"error": "Aucune donnée disponible"}

        min_year_filter = max_year - 9  # 10 dernières années

        summary = df.filter(F.col("year") >= min_year_filter).groupBy("year").agg(
            F.countDistinct("City").alias("num_cities"),
            F.round(F.avg("avg_yearly_temperature"), 2).alias("global_avg_temp"),
            F.round(F.min("avg_yearly_temperature"), 2).alias("min_temp"),
            F.round(F.max("avg_yearly_temperature"), 2).alias("max_temp"),
            F.sum(F.when(F.col("is_anomaly") == True, 1).otherwise(0)).alias("anomaly_count"),
            F.sum(F.when(F.col("anomaly_type") == "Exceptionally Hot", 1).otherwise(0)).alias("hot_anomalies"),
            F.sum(F.when(F.col("anomaly_type") == "Exceptionally Cold", 1).otherwise(0)).alias("cold_anomalies")
        ).orderBy(F.col("year").desc())

        return {
            "year_range": {"from": min_year_filter, "to": max_year},
            "yearly_summary": [row.asDict() for row in summary.collect()]
        }

    def get_recent_anomalies(self, num_years: int = 5, limit: int = 50) -> Dict[str, Any]:
        """
        Récupère les anomalies récentes (N dernières années).
        """
        try:
            df = self._read_data()
        except Exception:
            return {"error": "Aucune donnée disponible", "data": []}

        max_year = df.agg(F.max("year")).collect()[0][0]

        if max_year is None:
            return {"error": "Aucune donnée disponible", "data": []}

        min_year_filter = max_year - num_years + 1

        df_anomalies = df.filter(
            (F.col("year") >= min_year_filter) & (F.col("is_anomaly") == True)
        ).orderBy(F.abs(F.col("temperature_zscore")).desc()).limit(limit)

        return {
            "year_range": {"from": min_year_filter, "to": max_year},
            "count": df_anomalies.count(),
            "data": [row.asDict() for row in df_anomalies.collect()]
        }

    def get_trends_comparison(self, city: str) -> Dict[str, Any]:
        """
        Compare les tendances récentes vs historiques pour une ville.
        """
        try:
            df = self._read_data()
        except Exception:
            return {"error": "Aucune donnée disponible"}

        df_city = df.filter(F.col("City") == city)

        if df_city.count() == 0:
            return {"error": f"Ville '{city}' non trouvée"}

        max_year = df_city.agg(F.max("year")).collect()[0][0]
        min_year = df_city.agg(F.min("year")).collect()[0][0]

        # Période récente (20 dernières années)
        recent_start = max_year - 19
        df_recent = df_city.filter(F.col("year") >= recent_start)

        # Période historique (avant les 20 dernières années)
        df_historical = df_city.filter(F.col("year") < recent_start)

        # Stats récentes
        recent_stats = df_recent.agg(
            F.round(F.avg("avg_yearly_temperature"), 2).alias("avg_temp"),
            F.round(F.min("avg_yearly_temperature"), 2).alias("min_temp"),
            F.round(F.max("avg_yearly_temperature"), 2).alias("max_temp"),
            F.count("*").alias("num_years")
        ).collect()[0].asDict()

        # Stats historiques
        historical_stats = df_historical.agg(
            F.round(F.avg("avg_yearly_temperature"), 2).alias("avg_temp"),
            F.round(F.min("avg_yearly_temperature"), 2).alias("min_temp"),
            F.round(F.max("avg_yearly_temperature"), 2).alias("max_temp"),
            F.count("*").alias("num_years")
        ).collect()[0].asDict()

        # Calculer la différence
        temp_diff = None
        if recent_stats["avg_temp"] and historical_stats["avg_temp"]:
            temp_diff = round(recent_stats["avg_temp"] - historical_stats["avg_temp"], 2)

        return {
            "city": city,
            "recent_period": {"from": recent_start, "to": max_year, "stats": recent_stats},
            "historical_period": {"from": min_year, "to": recent_start - 1, "stats": historical_stats},
            "temperature_change": temp_diff
        }

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
