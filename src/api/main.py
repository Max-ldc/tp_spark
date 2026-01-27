import os
import sys
import platform

# Configuration pour Windows
if platform.system() == "Windows":
    hadoop_home = os.path.join(os.path.expanduser("~"), "hadoop")
    os.environ["HADOOP_HOME"] = hadoop_home
    os.environ["JAVA_HOME"] = r"C:\Program Files\Java\jdk-17"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Query
from typing import Optional
from services.spark_service import get_query_service


app = FastAPI(
    title="Temperature Query API",
    description="API pour requêter les données de température enrichies par Spark",
    version="1.0.0"
)


# ============================================================================
# ENDPOINTS DE REQUÊTAGE
# ============================================================================

@app.get("/data")
async def get_data(
    city: Optional[str] = Query(None, description="Filtrer par ville"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre max d'enregistrements")
):
    """
    Récupère les données température par année/ville.
    """
    try:
        service = get_query_service()
        data = service.get_data(city=city, limit=limit)
        return {
            "count": len(data),
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats(
    city: Optional[str] = Query(None, description="Filtrer par ville")
):
    """
    Calcule les statistiques agrégées par ville.

    Retourne :
    - Température moyenne, min, max
    - Années couvertes
    - Nombre d'anomalies
    """
    try:
        service = get_query_service()
        stats = service.get_stats(city=city)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/anomalies")
async def get_anomalies(
    anomaly_type: Optional[str] = Query(None, description="Type: 'Exceptionally Hot' ou 'Exceptionally Cold'"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre max d'enregistrements")
):
    """
    Récupère les anomalies de température (années exceptionnellement chaudes ou froides).
    """
    try:
        service = get_query_service()
        data = service.get_anomalies(anomaly_type=anomaly_type, limit=limit)
        return {
            "count": len(data),
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cities")
async def get_cities():
    """Retourne la liste des villes disponibles."""
    try:
        service = get_query_service()
        cities = service.get_cities()
        return {"cities": cities, "count": len(cities)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/years")
async def get_years():
    """Retourne la liste des années disponibles."""
    try:
        service = get_query_service()
        years = service.get_years()
        return {"years": years, "count": len(years)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/countries")
async def get_countries():
    """Retourne la liste des pays disponibles."""
    try:
        service = get_query_service()
        countries = service.get_countries()
        return {"countries": countries, "count": len(countries)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/data/year/{year}")
async def get_data_by_year(
    year: int,
    limit: int = Query(1000, ge=1, le=5000, description="Nombre max d'enregistrements")
):
    """Récupère les données pour une année spécifique."""
    try:
        service = get_query_service()
        data = service.get_data_by_year(year=year, limit=limit)
        return {"year": year, "count": len(data), "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/data/country/{country}")
async def get_data_by_country(
    country: str,
    limit: int = Query(1000, ge=1, le=5000, description="Nombre max d'enregistrements")
):
    """Récupère les données pour un pays spécifique."""
    try:
        service = get_query_service()
        data = service.get_data_by_country(country=country, limit=limit)
        return {"country": country, "count": len(data), "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/warming/top")
async def get_warming_top(
    limit: int = Query(20, ge=1, le=100, description="Nombre de villes à retourner")
):
    """
    Retourne les villes qui se réchauffent le plus rapidement.

    Calcule le taux de réchauffement par décennie basé sur la corrélation
    entre l'année et la température moyenne.
    """
    try:
        service = get_query_service()
        data = service.get_warming_top(limit=limit)
        return {"count": len(data), "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/warming/cooling")
async def get_warming_cooling(
    limit: int = Query(20, ge=1, le=100, description="Nombre de villes à retourner")
):
    """
    Retourne les villes qui refroidissent (taux de réchauffement négatif).
    """
    try:
        service = get_query_service()
        data = service.get_warming_cooling(limit=limit)
        return {"count": len(data), "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/hemispheres")
async def get_hemispheres_comparison():
    """
    Compare les statistiques de température entre les hémisphères Nord et Sud.

    Retourne :
    - Température moyenne par hémisphère
    - Écart-type des températures
    - Nombre de villes et d'enregistrements
    - Nombre d'anomalies
    """
    try:
        service = get_query_service()
        data = service.get_hemispheres_comparison()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/latitude-bands")
async def get_latitude_bands():
    """
    Statistiques par bande de latitude.

    Bandes :
    - Arctic (60°+)
    - Northern Temperate (30-60°)
    - Tropical North (0-30°)
    - Tropical South (0-30°)
    - Southern Temperate (30-60°)
    - Antarctic (60°-)
    """
    try:
        service = get_query_service()
        data = service.get_latitude_bands()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search")
async def search_cities(
    q: str = Query(..., min_length=2, description="Terme de recherche (min 2 caractères)"),
    limit: int = Query(50, ge=1, le=200, description="Nombre max de résultats")
):
    """
    Recherche de villes par nom partiel.

    Exemple : /search?q=Par retourne Paris, Paraná, etc.
    """
    try:
        service = get_query_service()
        data = service.search_cities(query=q, limit=limit)
        return {"query": q, "count": len(data), "results": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS DONNÉES RÉCENTES
# ============================================================================

@app.get("/recent/latest")
async def get_latest_data(
    limit: int = Query(100, ge=1, le=1000, description="Nombre max d'enregistrements")
):
    """
    Récupère les données de l'année la plus récente.

    Utile pour voir les dernières données ingérées par Spark.
    """
    try:
        service = get_query_service()
        return service.get_latest_data(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recent/years")
async def get_recent_years(
    num_years: int = Query(5, ge=1, le=20, description="Nombre d'années récentes"),
    limit: int = Query(500, ge=1, le=2000, description="Nombre max d'enregistrements")
):
    """
    Récupère les données des N dernières années.
    """
    try:
        service = get_query_service()
        return service.get_recent_years(num_years=num_years, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recent/summary")
async def get_recent_summary():
    """
    Résumé des 10 dernières années.

    Retourne pour chaque année :
    - Nombre de villes
    - Température moyenne globale
    - Min/Max température
    - Nombre d'anomalies (chaudes/froides)
    """
    try:
        service = get_query_service()
        return service.get_recent_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recent/anomalies")
async def get_recent_anomalies(
    num_years: int = Query(5, ge=1, le=20, description="Nombre d'années récentes"),
    limit: int = Query(50, ge=1, le=200, description="Nombre max d'anomalies")
):
    """
    Récupère les anomalies des N dernières années.

    Triées par intensité (z-score le plus extrême en premier).
    """
    try:
        service = get_query_service()
        return service.get_recent_anomalies(num_years=num_years, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trends/{city}")
async def get_city_trends(city: str):
    """
    Compare les tendances récentes vs historiques pour une ville.

    Compare les 20 dernières années avec la période précédente
    pour voir l'évolution de la température.
    """
    try:
        service = get_query_service()
        return service.get_trends_comparison(city=city)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Vérifie que l'API et Spark fonctionnent."""
    try:
        service = get_query_service()
        return {
            "status": "healthy",
            "spark": "connected",
            "app_name": service.spark.sparkContext.appName
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# ============================================================================
# DÉMARRAGE
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("TEMPERATURE QUERY API - Requêteur Spark")
    print("=" * 60)
    print("\nEndpoints disponibles :")
    print("  GET  /data              - Données température par année/ville")
    print("  GET  /stats             - Statistiques par ville")
    print("  GET  /anomalies         - Anomalies de température")
    print("  GET  /cities            - Liste des villes")
    print("  GET  /years             - Liste des années")
    print("  GET  /countries         - Liste des pays")
    print("  GET  /data/year/{year}  - Données par année")
    print("  GET  /data/country/{c}  - Données par pays")
    print("  GET  /warming/top       - Villes qui se réchauffent le plus")
    print("  GET  /warming/cooling   - Villes qui refroidissent")
    print("  GET  /hemispheres       - Comparaison Nord vs Sud")
    print("  GET  /latitude-bands    - Stats par bande de latitude")
    print("  GET  /search?q=...      - Recherche de villes")
    print("\n  -- Données récentes (Windy) --")
    print("  GET  /recent/latest     - Dernière année de données")
    print("  GET  /recent/years      - N dernières années")
    print("  GET  /recent/summary    - Résumé des 10 dernières années")
    print("  GET  /recent/anomalies  - Anomalies récentes")
    print("  GET  /trends/{city}     - Tendances récentes vs historiques")
    print("\n  GET  /health            - État de l'API")
    print("\nDocumentation : http://localhost:8000/docs")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000)
