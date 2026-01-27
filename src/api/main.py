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
    title="Weather Query API",
    description="API pour requêter les données météo ingérées par Spark",
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
    Récupère les données météo stockées par Spark.

    Paramètres optionnels :
    - city: filtrer par ville (ex: Paris, London)
    - limit: nombre max de résultats (défaut: 100)
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
    - Vent moyen
    - Humidité moyenne
    - Pression moyenne
    - Couverture nuageuse moyenne
    """
    try:
        service = get_query_service()
        stats = service.get_stats(city=city)
        return stats
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
    print("WEATHER QUERY API - Requêteur Spark")
    print("=" * 60)
    print("\nEndpoints disponibles :")
    print("  GET  /data    - Récupérer les données météo")
    print("  GET  /stats   - Statistiques par ville")
    print("  GET  /cities  - Liste des villes")
    print("  GET  /health  - État de l'API")
    print("\nDocumentation : http://localhost:8000/docs")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000)
