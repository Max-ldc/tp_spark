#!/usr/bin/env python3
"""
Script de test pour vérifier le système de logging.
"""
import sys
import os
from pathlib import Path

# Ajouter le répertoire src au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.logger import create_logger, set_trace_id, set_user_id


def test_logging():
    """Teste le système de logging structuré."""
    
    # Créer un logger
    logger = create_logger(
        name="test-logger",
        service_name="test-service",
        log_dir="./logs",
        log_level="DEBUG"
    )
    
    print("=== Test du système de logging ===\n")
    
    # Test 1: Logs simples
    print("1. Logs simples")
    logger.debug("Ceci est un message de debug")
    logger.info("Ceci est un message d'info")
    logger.warning("Ceci est un avertissement")
    logger.error("Ceci est une erreur")
    
    # Test 2: Logs avec contexte
    print("\n2. Logs avec contexte enrichi")
    logger.info(
        "Requête utilisateur",
        user="john.doe",
        action="query",
        city="Paris",
        limit=100
    )
    
    # Test 3: Trace ID
    print("\n3. Logs avec trace_id")
    trace_id = set_trace_id()
    set_user_id("admin@example.com")
    
    logger.info("Début du traitement", operation="data_extraction")
    logger.info("Traitement en cours", progress=50)
    logger.info("Traitement terminé", status="success")
    
    # Test 4: Exception
    print("\n4. Log d'exception")
    try:
        result = 1 / 0
    except ZeroDivisionError:
        logger.exception("Division par zéro détectée", operation="calculation")
    
    # Test 5: Log critique
    print("\n5. Log critique")
    logger.critical(
        "Service critique indisponible",
        service="database",
        error_code="DB_CONNECTION_FAILED"
    )
    
    print(f"\n✅ Logs générés dans: ./logs/test-service.log")
    print(f"📊 Trace ID utilisé: {trace_id}")
    
    # Afficher un extrait du fichier
    log_file = Path("./logs/test-service.log")
    if log_file.exists():
        print("\n=== Extrait des logs ===")
        with open(log_file, 'r') as f:
            lines = f.readlines()
            for line in lines[-3:]:  # Afficher les 3 dernières lignes
                print(line.strip())


if __name__ == "__main__":
    test_logging()
