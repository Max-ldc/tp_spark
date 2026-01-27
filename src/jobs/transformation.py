from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window


def clean_data(df: DataFrame) -> DataFrame:
    """
    Nettoie les données : filtre les valeurs nulles de température et extrait l'année.
    Ajoute la latitude numérique et l'hémisphère.
    """
    df_cleaned = df.filter(
        F.col("AverageTemperature").isNotNull() &
        F.col("Latitude").isNotNull()
    ).withColumn("Year", F.year(F.col("dt"))) \
     .withColumn("LatitudeValue", F.regexp_extract(F.col("Latitude"), r"([\d.]+)", 1).cast("double")) \
     .withColumn("LatitudeDirection", F.regexp_extract(F.col("Latitude"), r"([NS])", 1)) \
     .withColumn("LatitudeNumeric", 
                 F.when(F.col("LatitudeDirection") == "N", F.col("LatitudeValue"))
                  .otherwise(-F.col("LatitudeValue"))) \
     .withColumn("Hemisphere", 
                 F.when(F.col("LatitudeDirection") == "N", "Nord")
                  .otherwise("Sud")) \
     .drop("LatitudeValue", "LatitudeDirection")

    return df_cleaned


def identify_temperature_anomalies(df: DataFrame) -> DataFrame:
    """
    Identifie les années exceptionnellement chaudes ou froides.
    Utilise la méthode des écarts-types (anomalie si > 2σ ou < -2σ).
    """
    # Température moyenne par année
    yearly_temps = df.groupBy("Year").agg(
        F.avg("AverageTemperature").alias("AvgTemp")
    )
    
    # Calculer statistiques globales avec window function
    stats_window = Window.orderBy(F.lit(1))
    
    anomalies = yearly_temps.withColumn(
        "GlobalMean", F.avg("AvgTemp").over(stats_window)
    ).withColumn(
        "GlobalStdDev", F.stddev("AvgTemp").over(stats_window)
    ).withColumn(
        "Deviation", (F.col("AvgTemp") - F.col("GlobalMean")) / F.col("GlobalStdDev")
    ).withColumn(
        "Anomaly",
        F.when(F.col("Deviation") > 2, "Exceptionnellement chaud")
         .when(F.col("Deviation") < -2, "Exceptionnellement froid")
         .otherwise("Normal")
    ).filter(F.col("Anomaly") != "Normal") \
     .select("Year", "AvgTemp", "Deviation", "Anomaly") \
     .orderBy(F.desc("Deviation"))
    
    return anomalies


def warming_speed_by_latitude(df: DataFrame) -> DataFrame:
    """
    Calcule la vitesse de réchauffement selon la latitude.
    Regroupe par bandes de latitude de 10 degrés.
    """
    # Créer des bandes de latitude
    df_with_bands = df.withColumn(
        "LatitudeBand",
        (F.floor(F.col("LatitudeNumeric") / 10) * 10).cast("int")
    )
    
    # Température moyenne par bande et année
    temp_by_band_year = df_with_bands.groupBy("LatitudeBand", "Year").agg(
        F.avg("AverageTemperature").alias("AvgTemp")
    )
    
    # Calculer la corrélation (indicateur de tendance)
    warming_speed = temp_by_band_year.groupBy("LatitudeBand").agg(
        F.corr("Year", "AvgTemp").alias("Correlation"),
        F.min("Year").alias("PremièreAnnée"),
        F.max("Year").alias("DernièreAnnée"),
        F.avg("AvgTemp").alias("TempMoyenne"),
        F.count("Year").alias("NombreAnnées")
    ).withColumn(
        "TendanceRechauffement",
        F.when(F.col("Correlation") > 0.5, "Fort réchauffement")
         .when(F.col("Correlation") > 0.2, "Réchauffement modéré")
         .when(F.col("Correlation") > -0.2, "Stable")
         .otherwise("Refroidissement")
    ).orderBy("LatitudeBand")
    
    return warming_speed


def compare_hemispheres(df: DataFrame) -> DataFrame:
    """
    Compare l'évolution des températures entre hémisphères Nord et Sud.
    Retourne deux DataFrames : évolution temporelle et statistiques globales.
    """
    # Évolution temporelle
    hemisphere_evolution = df.groupBy("Hemisphere", "Year").agg(
        F.avg("AverageTemperature").alias("TempMoyenne"),
        F.count("*").alias("NombreMesures")
    ).orderBy("Year", "Hemisphere")
    
    # Statistiques globales par hémisphère
    hemisphere_stats = df.groupBy("Hemisphere").agg(
        F.avg("AverageTemperature").alias("TempMoyenneGlobale"),
        F.min("AverageTemperature").alias("TempMin"),
        F.max("AverageTemperature").alias("TempMax"),
        F.stddev("AverageTemperature").alias("EcartType"),
        F.count("*").alias("TotalMesures")
    )
    
    return hemisphere_evolution, hemisphere_stats
