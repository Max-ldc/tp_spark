"""
Module de logging structuré pour l'observabilité.

Ce module fournit un système de logging JSON structuré avec:
- Logs au format JSON pour faciliter le parsing par Loki
- Traçabilité avec trace_id
- Contexte enrichi (service, user, etc.)
- Rotation automatique des logs
"""

import logging
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import uuid
from contextvars import ContextVar

# Context variables pour le traçage
trace_id_var: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)


class JSONFormatter(logging.Formatter):
    """
    Formatter personnalisé pour produire des logs au format JSON.
    """
    
    def __init__(self, service_name: str = "unknown"):
        super().__init__()
        self.service_name = service_name
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Formate un record de log en JSON.
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": self.service_name,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Ajouter le trace_id si disponible
        trace_id = trace_id_var.get()
        if trace_id:
            log_data["trace_id"] = trace_id
        
        # Ajouter le user_id si disponible
        user_id = user_id_var.get()
        if user_id:
            log_data["user"] = user_id
        
        # Ajouter les données supplémentaires du record
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)
        
        # Ajouter l'exception si présente
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


class StructuredLogger:
    """
    Logger structuré avec support du contexte et traçabilité.
    """
    
    def __init__(
        self,
        name: str,
        service_name: str,
        log_dir: Optional[Path] = None,
        log_level: str = "INFO"
    ):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        self.service_name = service_name
        
        # Éviter les doublons de handlers
        if self.logger.handlers:
            return
        
        # Handler pour fichier JSON
        if log_dir:
            log_dir = Path(log_dir)
            log_dir.mkdir(parents=True, exist_ok=True)
            
            log_file = log_dir / f"{service_name}.log"
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(JSONFormatter(service_name))
            self.logger.addHandler(file_handler)
        
        # Handler pour stdout (aussi en JSON)
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(JSONFormatter(service_name))
        self.logger.addHandler(stdout_handler)
    
    def _log(self, level: str, message: str, **kwargs):
        """
        Log un message avec des données supplémentaires.
        """
        extra = {"extra_data": kwargs} if kwargs else {}
        getattr(self.logger, level)(message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        """Log un message de debug."""
        self._log("debug", message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log un message d'info."""
        self._log("info", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log un message d'avertissement."""
        self._log("warning", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log un message d'erreur."""
        self._log("error", message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log une exception."""
        self.logger.exception(message, extra={"extra_data": kwargs} if kwargs else {})
    
    def critical(self, message: str, **kwargs):
        """Log un message critique."""
        self._log("critical", message, **kwargs)


def set_trace_id(trace_id: Optional[str] = None) -> str:
    """
    Définit le trace_id pour le contexte actuel.
    Si aucun trace_id n'est fourni, en génère un nouveau.
    """
    if trace_id is None:
        trace_id = str(uuid.uuid4())
    trace_id_var.set(trace_id)
    return trace_id


def get_trace_id() -> Optional[str]:
    """
    Récupère le trace_id du contexte actuel.
    """
    return trace_id_var.get()


def set_user_id(user_id: str):
    """
    Définit le user_id pour le contexte actuel.
    """
    user_id_var.set(user_id)


def get_user_id() -> Optional[str]:
    """
    Récupère le user_id du contexte actuel.
    """
    return user_id_var.get()


def create_logger(
    name: str,
    service_name: str,
    log_dir: Optional[str] = None,
    log_level: str = "INFO"
) -> StructuredLogger:
    """
    Factory pour créer un logger structuré.
    
    Args:
        name: Nom du logger
        service_name: Nom du service (ex: 'temperature-api')
        log_dir: Répertoire où stocker les logs (optionnel)
        log_level: Niveau de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Instance de StructuredLogger
    """
    log_path = Path(log_dir) if log_dir else None
    return StructuredLogger(name, service_name, log_path, log_level)
