#!/bin/bash

# Script de test de la solution d'observabilité

echo "🧪 Test de la solution d'observabilité"
echo "======================================="
echo ""

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction de test
test_service() {
    local name=$1
    local url=$2
    local expected=$3
    
    echo -n "Testing $name... "
    
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
    
    if [ "$response" = "$expected" ]; then
        echo -e "${GREEN}✓ OK${NC} (HTTP $response)"
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (Expected $expected, got $response)"
        return 1
    fi
}

# Vérifier que les conteneurs tournent
echo "1. Vérification des conteneurs Docker"
echo "--------------------------------------"

containers=("loki" "promtail" "grafana")
all_running=true

for container in "${containers[@]}"; do
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        echo -e "${GREEN}✓${NC} $container est en cours d'exécution"
    else
        echo -e "${RED}✗${NC} $container n'est PAS en cours d'exécution"
        all_running=false
    fi
done

echo ""

if [ "$all_running" = false ]; then
    echo -e "${RED}Certains conteneurs ne sont pas démarrés.${NC}"
    echo "Lancez: docker compose up -d"
    exit 1
fi

# Tests des endpoints
echo "2. Test des endpoints"
echo "---------------------"

# Test Loki
test_service "Loki Ready" "http://localhost:3100/ready" "200"

# Test Loki API
test_service "Loki API" "http://localhost:3100/loki/api/v1/labels" "200"

# Test Grafana
test_service "Grafana" "http://localhost:3000/api/health" "200"

# Test API (si lancée)
if docker ps --format '{{.Names}}' | grep -q "^spark-api$"; then
    test_service "Temperature API" "http://localhost:8000/health" "200"
else
    echo -e "${YELLOW}⚠${NC}  Temperature API non démarrée (optionnel)"
fi

echo ""

# Test du système de logging Python
echo "3. Test du système de logging Python"
echo "-------------------------------------"

if python3 test_logging.py > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Logging Python fonctionne"
    
    # Vérifier que le fichier de log a été créé
    if [ -f "./logs/test-service.log" ]; then
        echo -e "${GREEN}✓${NC} Fichier de log créé"
        
        # Vérifier le format JSON
        if head -1 ./logs/test-service.log | python3 -m json.tool > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} Format JSON valide"
        else
            echo -e "${RED}✗${NC} Format JSON invalide"
        fi
    else
        echo -e "${RED}✗${NC} Fichier de log non créé"
    fi
else
    echo -e "${RED}✗${NC} Erreur lors du test de logging"
fi

echo ""

# Test de requête Loki
echo "4. Test de requête Loki"
echo "-----------------------"

# Attendre un peu pour que les logs soient ingérés
echo "Attente de l'ingestion des logs (5 secondes)..."
sleep 5

# Requête Loki pour vérifier qu'il y a des logs
labels=$(curl -s "http://localhost:3100/loki/api/v1/labels" 2>/dev/null | python3 -c "import sys, json; print(json.load(sys.stdin)['data'])" 2>/dev/null)

if [ -n "$labels" ] && [ "$labels" != "[]" ]; then
    echo -e "${GREEN}✓${NC} Loki a des labels (logs ingérés)"
    echo "   Labels disponibles: $labels"
else
    echo -e "${YELLOW}⚠${NC}  Aucun label trouvé (logs peut-être pas encore ingérés)"
fi

echo ""

# Résumé
echo "📊 Résumé"
echo "========="
echo ""
echo "Services disponibles:"
echo "  - Grafana:  http://localhost:3000 (admin/admin)"
echo "  - Loki:     http://localhost:3100"
echo "  - Promtail: http://localhost:9080/metrics"
echo ""
echo "Dashboard Grafana:"
echo "  http://localhost:3000/d/temperature-api-logs/temperature-api-logs-dashboard"
echo ""
echo "Prochaines étapes:"
echo "  1. Ouvrir Grafana dans votre navigateur"
echo "  2. Aller dans Dashboards → Temperature API - Logs Dashboard"
echo "  3. Générer du trafic: curl -H \"X-API-Key: admin-key-004\" http://localhost:8000/health"
echo "  4. Voir les logs apparaître en temps réel !"
echo ""

echo -e "${GREEN}✅ Test d'observabilité terminé !${NC}"
