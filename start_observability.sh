#!/bin/bash

# Script de démarrage de la stack complète avec observabilité

echo "🚀 Démarrage de la stack Temperature API avec Observabilité"
echo "=============================================================="
echo ""

# Vérifier que docker compose est disponible
if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé. Veuillez installer Docker."
    exit 1
fi

# Créer le répertoire logs s'il n'existe pas
mkdir -p logs

echo "📦 Construction et démarrage des conteneurs..."
docker compose up -d --build

echo ""
echo "⏳ Attente du démarrage des services (30 secondes)..."
sleep 30

echo ""
echo "✅ Stack démarrée avec succès !"
echo ""
echo "📊 Services disponibles :"
echo "  - API:              http://localhost:8000"
echo "  - API Docs:         http://localhost:8000/docs"
echo "  - Grafana:          http://localhost:3000 (admin/admin)"
echo "  - Loki:             http://localhost:3100"
echo "  - Keycloak:         http://localhost:8080"
echo "  - Spark UI (ETL):   http://localhost:4040"
echo "  - Spark UI (API):   http://localhost:4041"
echo "  - Spark UI (Windy): http://localhost:4042"
echo ""
echo "📈 Dashboard de logs :"
echo "  http://localhost:3000/d/temperature-api-logs/temperature-api-logs-dashboard"
echo ""
echo "🧪 Tester l'API :"
echo "  curl -X POST \"http://localhost:8000/auth/token?api_key=admin-key-004\""
echo "  curl -H \"X-API-Key: admin-key-004\" http://localhost:8000/health"
echo ""
echo "📝 Voir les logs des conteneurs :"
echo "  docker compose logs -f api"
echo "  docker compose logs -f loki"
echo "  docker compose logs -f promtail"
echo ""
echo "🛑 Arrêter la stack :"
echo "  docker compose down"
echo ""
