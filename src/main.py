import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pyspark.sql import functions as F
from utils.spark_session import get_spark_session
from jobs.extraction import extract_data
from jobs.transformation import (
    clean_data,
    identify_temperature_anomalies,
    warming_speed_by_latitude,
    compare_hemispheres
)


def main():
    spark = get_spark_session("TemperatureAnalysis")

    # 1. Extract
    raw_data_path = "data/raw/GlobalLandTemperaturesByCity.csv"
    print("Chargement des données...")
    df = extract_data(spark, raw_data_path)

    # 2. Clean
    print("Nettoyage des données...")
    df_cleaned = clean_data(df)
    df_cleaned.cache()

    # 3. Identification des anomalies de température
    print("\n" + "=" * 80)
    print("ANNÉES EXCEPTIONNELLEMENT CHAUDES OU FROIDES")
    print("=" * 80)
    df_anomalies = identify_temperature_anomalies(df_cleaned)
    df_anomalies.show(30, truncate=False)

    # 4. Vitesse de réchauffement par bande de latitude
    print("\n" + "=" * 80)
    print("VITESSE DE RÉCHAUFFEMENT PAR BANDE DE LATITUDE")
    print("=" * 80)
    df_warming = warming_speed_by_latitude(df_cleaned)
    df_warming.show(50, truncate=False)

    # 5. Comparaison hémisphère Nord vs Sud
    print("\n" + "=" * 80)
    print("COMPARAISON HÉMISPHÈRE NORD VS SUD")
    print("=" * 80)
    df_hemisphere_evolution, df_hemisphere_stats = compare_hemispheres(df_cleaned)
    
    print("\nStatistiques globales par hémisphère:")
    df_hemisphere_stats.show(truncate=False)
    
    print("\nÉvolution temporelle (premières années):")
    df_hemisphere_evolution.filter(F.col("Year") <= 1760).show(20, truncate=False)
    
    print("\nÉvolution temporelle (dernières années):")
    df_hemisphere_evolution.filter(F.col("Year") >= 2010).show(20, truncate=False)

    df_cleaned.unpersist()
    print("\nAnalyse terminée.")

    input("Appuyez sur Entrée pour terminer...")
    spark.stop()


if __name__ == "__main__":
    main()