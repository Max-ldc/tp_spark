import os
import sys
import platform

# Configuration pour Windows
if platform.system() == "Windows":
    hadoop_home = os.path.join(os.path.expanduser("~"), "hadoop")
    os.environ["HADOOP_HOME"] = hadoop_home
    os.environ["JAVA_HOME"] = r"C:\Program Files\Java\jdk-17"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Query, Security, Request
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Optional
import jwt
from datetime import datetime, timedelta, timezone
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from services.spark_service import get_query_service
from services.windy_service import get_windy_service
from auth import HybridAuthManager, create_hybrid_auth_dependency
from utils.logger import create_logger
from utils.logging_middleware import LoggingMiddleware


# ============================================================================
# CONFIGURATION LOGGING
# ============================================================================

# Créer le logger pour l'API
logger = create_logger(
    name="temperature-api",
    service_name="temperature-api",
    log_dir="/var/log/temperature-api",
    log_level=os.getenv("LOG_LEVEL", "INFO")
)

logger.info("Démarrage de l'API Temperature Query")


# ============================================================================
# CONFIGURATION AUTHENTIFICATION HYBRIDE
# ============================================================================

# Rôles disponibles et leur hiérarchie d'accès
# BASIC    : Socle commun (données de base)
# ANALYST  : Analyse historique (inclut BASIC)
# WINDY    : Temps réel Windy (inclut BASIC)
# ADMIN    : Accès complet (inclut tout)
ROLE_HIERARCHY = {
    "BASIC": {"BASIC"},
    "ANALYST": {"BASIC", "ANALYST"},
    "WINDY": {"BASIC", "WINDY"},
    "ADMIN": {"BASIC", "ANALYST", "WINDY", "ADMIN"},
}

# Clés API valides (en production, utiliser une base de données ou env vars)
VALID_API_KEYS = {
    "basic-key-001": {"name": "Basic User", "role": "BASIC", "max_results": 50},
    "analyst-key-002": {"name": "Analyst User", "role": "ANALYST", "max_results": 200},
    "windy-key-003": {"name": "Windy User", "role": "WINDY", "max_results": 200},
    "admin-key-004": {"name": "Admin User", "role": "ADMIN", "max_results": 1000},
}

# Configuration JWT
JWT_SECRET = "spark-api-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 1

# Configuration Certificats (optionnel)
CERTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "certs")
CA_CERT_PATH = os.path.join(CERTS_DIR, "ca", "ca-cert.pem") if os.path.exists(os.path.join(CERTS_DIR, "ca")) else None

# Initialiser le gestionnaire d'authentification hybride
auth_manager = HybridAuthManager(
    jwt_secret=JWT_SECRET,
    jwt_algorithm=JWT_ALGORITHM,
    ca_cert_path=CA_CERT_PATH,
    valid_api_keys=VALID_API_KEYS
)

# Créer la dépendance Security pour l'authentification hybride
require_auth = create_hybrid_auth_dependency(auth_manager)


def require_role(api_info: dict, required_zone: str):
    """
    Vérifie que le rôle de l'utilisateur donne accès à la zone demandée.
    Lève une 403 si le rôle est insuffisant.
    """
    user_role = api_info.get("role", "BASIC")
    allowed_zones = ROLE_HIERARCHY.get(user_role, set())
    if required_zone not in allowed_zones:
        raise HTTPException(
            status_code=403,
            detail=f"Accès refusé. Rôle '{user_role}' insuffisant, zone '{required_zone}' requise."
        )


def limit_results(data: list, api_info: dict) -> list:
    """Limite le nombre de résultats selon le niveau de l'API key."""
    max_results = api_info.get("max_results", 3)
    return data[:max_results]


app = FastAPI(
    title="Temperature Query API",
    description="API pour requêter les données de température enrichies par Spark",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# Ajouter le middleware de logging
app.add_middleware(LoggingMiddleware, logger=logger)

# Configuration Rate Limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configuration CORS pour le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5500",  # Live Server
        "file://"  # Fichiers locaux
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoints bêta (NOT WORKING) - masqués du Swagger sauf pour ADMIN
BETA_PATHS = {
    "/stats", "/warming/top", "/warming/cooling",
    "/hemispheres", "/latitude-bands", "/trends/{city}",
    "/recent/summary", "/windy/streaming/trends/{location}",
}


@app.get("/openapi.json", include_in_schema=False)
async def custom_openapi(key: Optional[str] = Query(None)):
    """Génère le schéma OpenAPI filtré selon le rôle."""
    resolved_key = key
    show_beta = False
    if resolved_key and resolved_key in VALID_API_KEYS:
        role = VALID_API_KEYS[resolved_key]["role"]
        if "ADMIN" in ROLE_HIERARCHY.get(role, set()):
            show_beta = True

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    if not show_beta:
        schema["paths"] = {
            path: ops for path, ops in schema["paths"].items()
            if path not in BETA_PATHS
        }

    # Ajouter le schéma de sécurité Bearer pour Swagger UI
    schema["components"] = schema.get("components", {})
    schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Entrez le JWT obtenu via POST /auth/token"
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "Clé API statique"
        }
    }
    
    # Appliquer les schémas de sécurité à tous les endpoints (sauf /auth/token)
    for path, path_item in schema.get("paths", {}).items():
        for method, operation in path_item.items():
            if method in ["get", "post", "put", "delete", "patch"]:
                if path != "/auth/token":
                    operation["security"] = [
                        {"BearerAuth": []},
                        {"ApiKeyAuth": []}
                    ]

    return JSONResponse(schema)


@app.get("/docs", include_in_schema=False)
async def custom_docs(key: Optional[str] = Query(None)):
    """Swagger UI. Passer ?key=ADMIN_KEY pour voir les endpoints bêta."""
    openapi_url = "/openapi.json"
    if key:
        openapi_url = f"/openapi.json?key={key}"

    return HTMLResponse(f"""<!DOCTYPE html>
<html><head>
<title>Temperature Query API - Docs</title>
<link rel="stylesheet" type="text/css"
      href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
</head><body>
<div id="swagger-ui"></div>
<script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
<script>
SwaggerUIBundle({{
    url: "{openapi_url}",
    dom_id: '#swagger-ui',
    presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
    layout: "BaseLayout"
}})
</script>
</body></html>""")


# ============================================================================
# ENDPOINTS D'AUTHENTIFICATION
# ============================================================================

@app.post("/auth/token")
@limiter.limit("5/minute")
async def generate_token(
    request: Request,
    api_key: Optional[str] = Query(None, description="Clé API (peut aussi être passée en header X-API-Key)"),
    header_key: Optional[str] = Security(APIKeyHeader(name="X-API-Key", auto_error=False))
):
    """
    Génère un JWT à partir d'une clé API statique valide.
    
    La clé API peut être passée soit :
    - En paramètre query : POST /auth/token?api_key=votre-cle
    - Dans le header X-API-Key
    
    Retourne un token JWT valide pour 1 heure.
    
    🔐 Authentification hybride :
    - Certificat X.509 (optionnel)
    - JWT Bearer token
    - API Keys statiques
    """
    # Prioriser le paramètre query, sinon utiliser le header
    resolved_key = api_key or header_key
    
    if resolved_key is None:
        logger.warning("Tentative de génération de token sans clé API")
        raise HTTPException(
            status_code=401,
            detail="Clé API requise (paramètre 'api_key' ou header 'X-API-Key')"
        )
    if resolved_key not in VALID_API_KEYS:
        logger.warning("Tentative d'authentification avec clé API invalide", api_key=resolved_key[:10] + "...")
        raise HTTPException(
            status_code=403,
            detail="Clé API invalide"
        )
    
    user_info = VALID_API_KEYS[resolved_key]
    
    # Utiliser le gestionnaire d'authentification hybride pour générer le JWT
    token_response = auth_manager.generate_jwt_token(
        name=user_info["name"],
        role=user_info["role"],
        max_results=user_info["max_results"],
        expiration_hours=JWT_EXPIRATION_HOURS
    )
    
    logger.info(
        f"Token JWT généré avec succès",
        user=user_info["name"],
        role=user_info["role"]
    )
    
    return token_response


@app.post("/auth/certificate")
@limiter.limit("10/minute")
async def validate_certificate(
    request: Request,
    cert_pem: str = Query(..., description="Certificat client au format PEM")
):
    """
    Valide un certificat X.509 client et extrait les informations d'authentification.
    
    Optionnel : Génère un JWT si le certificat est valide.
    
    📋 Usage:
    ```bash
    # 1. Valider le certificat
    curl -X POST "http://localhost:8000/auth/certificate?cert_pem=$(cat client-cert.pem)"
    
    # 2. Utiliser le JWT reçu
    curl -H "Authorization: Bearer <access_token>" http://localhost:8000/health
    ```
    """
    is_valid, cert_info, error_msg = auth_manager.cert_validator.validate_certificate_pem(cert_pem)
    
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"Certificat invalide: {error_msg}"
        )
    
    # Extraire les infos et générer un JWT
    cn = cert_info.get("cn", "certificate-client")
    role = cert_info.get("role", "BASIC")
    max_results = auth_manager._get_max_results_for_role(role)
    
    token_response = auth_manager.generate_jwt_token(
        name=cn,
        role=role,
        max_results=max_results,
        expiration_hours=JWT_EXPIRATION_HOURS
    )
    
    return {
        **token_response,
        "certificate_info": {
            "cn": cn,
            "role": role,
            "valid_from": cert_info["valid_from"].isoformat(),
            "valid_until": cert_info["valid_until"].isoformat(),
            "subject": cert_info["subject"],
            "issuer": cert_info["issuer"],
        }
    }


@app.get("/auth/test")
@limiter.limit("60/minute")
async def test_auth(request: Request, api_info: dict = Security(require_auth)):
    """
    Endpoint de test simple pour vérifier l'authentification.
    Ne nécessite pas Spark - retourne juste les infos d'authentification.
    🔐 Zone BASIC
    """
    require_role(api_info, "BASIC")
    return {
        "status": "authenticated",
        "auth_method": api_info.get("auth_method"),
        "name": api_info.get("name"),
        "role": api_info.get("role"),
        "max_results": api_info.get("max_results"),
        "message": "Authentification réussie !"
    }


# ============================================================================
# ENDPOINTS DE REQUÊTAGE
# ============================================================================

@app.get("/data")
@limiter.limit("100/minute")
async def get_data(
    request: Request,
    city: Optional[str] = Query(None, description="Filtrer par ville"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre max d'enregistrements"),
    api_info: dict = Security(require_auth)
):
    """
    Récupère les données température par année/ville.
    🔐 Zone BASIC
    """
    require_role(api_info, "BASIC")
    try:
        logger.info(
            "Requête de données",
            city=city,
            limit=limit,
            user=api_info.get("name"),
            role=api_info.get("role")
        )
        service = get_query_service()
        data = service.get_data(city=city, limit=limit)
        data = limit_results(data, api_info)
        
        logger.info("Données retournées avec succès", count=len(data), city=city)
        
        return {
            "count": len(data),
            "data": data,
            "limited_to": api_info.get("max_results")
        }
    except Exception as e:
        logger.exception("Erreur lors de la récupération des données", city=city)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats(
    city: Optional[str] = Query(None, description="Filtrer par ville"),
    api_info: dict = Security(require_auth)
):
    """
    Calcule les statistiques agrégées par ville.
    🔐 Zone ADMIN

    Retourne :
    - Température moyenne, min, max
    - Années couvertes
    - Nombre d'anomalies
    """
    require_role(api_info, "ADMIN")
    try:
        service = get_query_service()
        stats = service.get_stats(city=city)
        if isinstance(stats, list):
            stats = limit_results(stats, api_info)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/anomalies")
async def get_anomalies(
    anomaly_type: Optional[str] = Query(None, description="Type: 'Exceptionally Hot' ou 'Exceptionally Cold'"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre max d'enregistrements"),
    api_info: dict = Security(require_auth)
):
    """
    Récupère les anomalies de température (années exceptionnellement chaudes ou froides).
    🔐 Zone ANALYST
    """
    require_role(api_info, "ANALYST")
    try:
        service = get_query_service()
        data = service.get_anomalies(anomaly_type=anomaly_type, limit=limit)
        data = limit_results(data, api_info)
        return {
            "count": len(data),
            "data": data,
            "limited_to": api_info.get("max_results")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cities")
@limiter.limit("100/minute")
async def get_cities(request: Request, api_info: dict = Security(require_auth)):
    """
    Retourne la liste des villes disponibles.
    🔐 Zone BASIC
    """
    require_role(api_info, "BASIC")
    try:
        service = get_query_service()
        cities = service.get_cities()
        return {"cities": cities, "count": len(cities)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/years")
@limiter.limit("100/minute")
async def get_years(request: Request, api_info: dict = Security(require_auth)):
    """
    Retourne la liste des années disponibles.
    🔐 Zone BASIC
    """
    require_role(api_info, "BASIC")
    try:
        service = get_query_service()
        years = service.get_years()
        return {"years": years, "count": len(years)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/countries")
@limiter.limit("100/minute")
async def get_countries(request: Request, api_info: dict = Security(require_auth)):
    """
    Retourne la liste des pays disponibles.
    🔐 Zone BASIC
    """
    require_role(api_info, "BASIC")
    try:
        service = get_query_service()
        countries = service.get_countries()
        return {"countries": countries, "count": len(countries)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/data/year/{year}")
async def get_data_by_year(
    year: int,
    limit: int = Query(1000, ge=1, le=5000, description="Nombre max d'enregistrements"),
    api_info: dict = Security(require_auth)
):
    """
    Récupère les données pour une année spécifique.
    🔐 Zone BASIC
    """
    require_role(api_info, "BASIC")
    try:
        service = get_query_service()
        data = service.get_data_by_year(year=year, limit=limit)
        data = limit_results(data, api_info)
        return {"year": year, "count": len(data), "data": data, "limited_to": api_info.get("max_results")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/data/country/{country}")
async def get_data_by_country(
    country: str,
    limit: int = Query(1000, ge=1, le=5000, description="Nombre max d'enregistrements"),
    api_info: dict = Security(require_auth)
):
    """
    Récupère les données pour un pays spécifique.
    🔐 Zone BASIC
    """
    require_role(api_info, "BASIC")
    try:
        service = get_query_service()
        data = service.get_data_by_country(country=country, limit=limit)
        data = limit_results(data, api_info)
        return {"country": country, "count": len(data), "data": data, "limited_to": api_info.get("max_results")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/warming/top")
async def get_warming_top(
    limit: int = Query(20, ge=1, le=100, description="Nombre de villes à retourner"),
    api_info: dict = Security(require_auth)
):
    """
    Retourne les villes qui se réchauffent le plus rapidement.
    🔐 Zone ADMIN

    Calcule le taux de réchauffement par décennie basé sur la corrélation
    entre l'année et la température moyenne.
    """
    require_role(api_info, "ADMIN")
    try:
        service = get_query_service()
        data = service.get_warming_top(limit=limit)
        data = limit_results(data, api_info)
        return {"count": len(data), "data": data, "limited_to": api_info.get("max_results")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/warming/cooling")
async def get_warming_cooling(
    limit: int = Query(20, ge=1, le=100, description="Nombre de villes à retourner"),
    api_info: dict = Security(require_auth)
):
    """
    Retourne les villes qui refroidissent (taux de réchauffement négatif).
    🔐 Zone ADMIN
    """
    require_role(api_info, "ADMIN")
    try:
        service = get_query_service()
        data = service.get_warming_cooling(limit=limit)
        data = limit_results(data, api_info)
        return {"count": len(data), "data": data, "limited_to": api_info.get("max_results")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/hemispheres")
async def get_hemispheres_comparison(api_info: dict = Security(require_auth)):
    """
    Compare les statistiques de température entre les hémisphères Nord et Sud.
    🔐 Zone ADMIN

    Retourne :
    - Température moyenne par hémisphère
    - Écart-type des températures
    - Nombre de villes et d'enregistrements
    - Nombre d'anomalies
    """
    require_role(api_info, "ADMIN")
    try:
        service = get_query_service()
        data = service.get_hemispheres_comparison()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/latitude-bands")
async def get_latitude_bands(api_info: dict = Security(require_auth)):
    """
    Statistiques par bande de latitude.
    🔐 Requiert une API Key (header X-API-Key)

    Bandes :
    - Arctic (60°+)
    - Northern Temperate (30-60°)
    - Tropical North (0-30°)
    - Tropical South (0-30°)
    - Southern Temperate (30-60°)
    - Antarctic (60°-)
    """
    require_role(api_info, "ADMIN")
    try:
        service = get_query_service()
        data = service.get_latitude_bands()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search")
async def search_cities(
    q: str = Query(..., min_length=2, description="Terme de recherche (min 2 caractères)"),
    limit: int = Query(50, ge=1, le=200, description="Nombre max de résultats"),
    api_info: dict = Security(require_auth)
):
    """
    Recherche de villes par nom partiel.
    🔐 Zone ANALYST

    Exemple : /search?q=Par retourne Paris, Paraná, etc.
    """
    require_role(api_info, "ANALYST")
    try:
        service = get_query_service()
        data = service.search_cities(query=q, limit=limit)
        data = limit_results(data, api_info)
        return {"query": q, "count": len(data), "results": data, "limited_to": api_info.get("max_results")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS DONNÉES RÉCENTES
# ============================================================================

@app.get("/recent/latest")
async def get_latest_data(
    limit: int = Query(100, ge=1, le=1000, description="Nombre max d'enregistrements"),
    api_info: dict = Security(require_auth)
):
    """
    Récupère les données de l'année la plus récente.
    🔐 Zone ANALYST

    Utile pour voir les dernières données ingérées par Spark.
    """
    require_role(api_info, "ANALYST")
    try:
        service = get_query_service()
        result = service.get_latest_data(limit=limit)
        if "data" in result and isinstance(result["data"], list):
            result["data"] = limit_results(result["data"], api_info)
            result["count"] = len(result["data"])
            result["limited_to"] = api_info.get("max_results")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recent/years")
async def get_recent_years(
    num_years: int = Query(5, ge=1, le=20, description="Nombre d'années récentes"),
    limit: int = Query(500, ge=1, le=2000, description="Nombre max d'enregistrements"),
    api_info: dict = Security(require_auth)
):
    """
    Récupère les données des N dernières années.
    🔐 Zone ANALYST
    """
    require_role(api_info, "ANALYST")
    try:
        service = get_query_service()
        result = service.get_recent_years(num_years=num_years, limit=limit)
        if "data" in result and isinstance(result["data"], list):
            result["data"] = limit_results(result["data"], api_info)
            result["count"] = len(result["data"])
            result["limited_to"] = api_info.get("max_results")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recent/summary")
async def get_recent_summary(api_info: dict = Security(require_auth)):
    """
    Résumé des 10 dernières années.
    🔐 Zone ADMIN (bêta)

    Retourne pour chaque année :
    - Nombre de villes
    - Température moyenne globale
    - Min/Max température
    - Nombre d'anomalies (chaudes/froides)
    """
    require_role(api_info, "ADMIN")
    try:
        service = get_query_service()
        result = service.get_recent_summary()
        if "yearly_summary" in result and isinstance(result["yearly_summary"], list):
            result["yearly_summary"] = limit_results(result["yearly_summary"], api_info)
            result["limited_to"] = api_info.get("max_results")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recent/anomalies")
async def get_recent_anomalies(
    num_years: int = Query(5, ge=1, le=20, description="Nombre d'années récentes"),
    limit: int = Query(50, ge=1, le=200, description="Nombre max d'anomalies"),
    api_info: dict = Security(require_auth)
):
    """
    Récupère les anomalies des N dernières années.
    🔐 Zone ANALYST

    Triées par intensité (z-score le plus extrême en premier).
    """
    require_role(api_info, "ANALYST")
    try:
        service = get_query_service()
        result = service.get_recent_anomalies(num_years=num_years, limit=limit)
        if "data" in result and isinstance(result["data"], list):
            result["data"] = limit_results(result["data"], api_info)
            result["count"] = len(result["data"])
            result["limited_to"] = api_info.get("max_results")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trends/{city}")
async def get_city_trends(city: str, api_info: dict = Security(require_auth)):
    """
    Compare les tendances récentes vs historiques pour une ville.
    🔐 Zone ADMIN

    Compare les 20 dernières années avec la période précédente
    pour voir l'évolution de la température.
    """
    require_role(api_info, "ADMIN")
    try:
        service = get_query_service()
        return service.get_trends_comparison(city=city)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check(api_info: dict = Security(require_auth)):
    """
    Vérifie que l'API et Spark fonctionnent.
    🔐 Zone BASIC
    """
    require_role(api_info, "BASIC")
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
# ENDPOINTS WINDY (Météo en Temps Réel)
# ============================================================================

@app.get("/windy/current")
async def get_windy_current(
    location: Optional[str] = Query(None, description="Filtrer par nom de localisation"),
    api_info: dict = Security(require_auth)
):
    """
    Récupère les conditions météo ACTUELLES depuis l'API Windy.
    🔐 Zone WINDY

    Retourne les dernières mesures avec:
    - Température actuelle
    - Vitesse et direction du vent
    - Pression atmosphérique
    - Humidité
    - Statut d'anomalie (comparé à l'historique)
    """
    require_role(api_info, "WINDY")
    try:
        service = get_windy_service()
        data = service.get_current_weather(location=location)
        data = limit_results(data, api_info)
        return {
            "count": len(data),
            "data": data,
            "limited_to": api_info.get("max_results")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/windy/anomalies")
async def get_windy_anomalies(api_info: dict = Security(require_auth)):
    """
    Récupère les ANOMALIES météo actuelles.
    🔐 Requiert une API Key (header X-API-Key)

    Identifie les localisations où la température actuelle est
    significativement différente de la moyenne historique (z-score > 2).
    """
    require_role(api_info, "WINDY")
    try:
        service = get_windy_service()
        data = service.get_current_anomalies()
        data = limit_results(data, api_info)
        return {
            "count": len(data),
            "anomalies": data,
            "limited_to": api_info.get("max_results")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/windy/hemispheres")
async def get_windy_hemispheres(api_info: dict = Security(require_auth)):
    """
    Statistiques météo ACTUELLES par hémisphère (Nord vs Sud).
    🔐 Zone WINDY
    """
    require_role(api_info, "WINDY")
    try:
        service = get_windy_service()
        return service.get_current_by_hemisphere()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/windy/latitude-bands")
async def get_windy_latitude_bands(api_info: dict = Security(require_auth)):
    """
    Statistiques météo ACTUELLES par bande de latitude.
    🔐 Zone WINDY

    Groupes: Arctic, Northern Temperate, Tropical North,
             Tropical South, Southern Temperate, Antarctic
    """
    require_role(api_info, "WINDY")
    try:
        service = get_windy_service()
        data = service.get_current_by_latitude()
        return {
            "latitude_bands": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/windy/locations")
async def get_windy_locations(api_info: dict = Security(require_auth)):
    """
    Retourne la liste des localisations surveillées par Windy.
    🔐 Zone WINDY
    """
    require_role(api_info, "WINDY")
    try:
        service = get_windy_service()
        locations = service.get_locations()
        locations = limit_results(locations, api_info)
        return {
            "locations": locations,
            "count": len(locations),
            "limited_to": api_info.get("max_results")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/windy/streaming/history")
async def get_windy_streaming_history(
    location: Optional[str] = Query(None, description="Filtrer par localisation"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre max d'enregistrements"),
    api_info: dict = Security(require_auth)
):
    """
    Historique des mesures streaming (données collectées en continu).
    🔐 Zone WINDY

    Retourne les mesures collectées par le service de streaming Windy,
    triées par timestamp décroissant.
    """
    require_role(api_info, "WINDY")
    try:
        service = get_windy_service()
        data = service.get_streaming_history(location=location, limit=limit)
        data = limit_results(data, api_info)
        return {
            "count": len(data),
            "data": data,
            "limited_to": api_info.get("max_results")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/windy/streaming/trends/{location}")
async def get_windy_streaming_trends(
    location: str,
    hours: int = Query(24, ge=1, le=168, description="Nombre d'heures à analyser"),
    api_info: dict = Security(require_auth)
):
    """
    Analyse les tendances météo sur les N dernières heures.
    🔐 Zone ADMIN (bêta)

    Calcule statistiques (min/max/avg) et retourne la série temporelle
    pour visualiser l'évolution de la température, vent, pression.
    """
    require_role(api_info, "ADMIN")
    try:
        service = get_windy_service()
        result = service.get_streaming_trends(location=location, hours=hours)
        if "time_series" in result and isinstance(result["time_series"], list):
            result["time_series"] = limit_results(result["time_series"], api_info)
            result["limited_to"] = api_info.get("max_results")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    print("\n  -- API Windy (Temps Réel) --")
    print("  GET  /windy/current           - Météo actuelle (toutes localisations)")
    print("  GET  /windy/anomalies         - Anomalies météo actuelles")
    print("  GET  /windy/hemispheres       - Stats actuelles par hémisphère")
    print("  GET  /windy/latitude-bands    - Stats actuelles par latitude")
    print("  GET  /windy/locations         - Localisations surveillées")
    print("  GET  /windy/streaming/history - Historique streaming")
    print("  GET  /windy/streaming/trends/{loc} - Tendances sur N heures")
    print("\n  GET  /health            - État de l'API")
    print("\nDocumentation : http://localhost:8000/docs")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000)
