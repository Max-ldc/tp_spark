"""
Middleware de logging pour FastAPI.

Ce middleware ajoute le logging automatique des requêtes/réponses HTTP
avec traçabilité et contexte enrichi.
"""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from utils.logger import set_trace_id, set_user_id, get_trace_id


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware pour logger toutes les requêtes HTTP.
    """
    
    def __init__(self, app: ASGIApp, logger):
        super().__init__(app)
        self.logger = logger
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Générer ou récupérer le trace_id
        trace_id = request.headers.get("X-Trace-ID") or set_trace_id()
        
        # Extraire l'utilisateur si disponible (depuis auth)
        user = getattr(request.state, "user", None)
        if user:
            user_id = user.get("name", "unknown")
            set_user_id(user_id)
        
        # Timing
        start_time = time.time()
        
        # Logger la requête entrante
        self.logger.info(
            f"Requête entrante: {request.method} {request.url.path}",
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params),
            client_ip=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent", "unknown")
        )
        
        # Traiter la requête
        try:
            response = await call_next(request)
            
            # Calculer la durée
            duration = time.time() - start_time
            
            # Logger la réponse
            self.logger.info(
                f"Réponse envoyée: {request.method} {request.url.path} - {response.status_code}",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2)
            )
            
            # Ajouter le trace_id dans les headers de réponse
            response.headers["X-Trace-ID"] = trace_id
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Logger l'erreur
            self.logger.exception(
                f"Erreur lors du traitement de {request.method} {request.url.path}",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration * 1000, 2),
                error_type=type(e).__name__
            )
            raise
