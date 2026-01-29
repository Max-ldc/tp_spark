# 📊 Solution d'Observabilité des Logs - Mise en Place Terminée

## ✅ Ce qui a été créé

### Infrastructure (Loki + Promtail + Grafana)

- **Loki** : Base de données de logs (port 3100)
- **Promtail** : Collecteur de logs 
- **Grafana** : Visualisation et dashboards (port 3000)
- **Dashboard pré-configuré** avec 5 panneaux de visualisation

### Code Python

- **Système de logging structuré** (JSON) avec traçabilité
- **Middleware FastAPI** pour logs HTTP automatiques
- **Context variables** pour trace_id et user_id

### Documentation

- ✅ [observability/README.md](observability/README.md) - Documentation complète
- ✅ [QUICK_START_OBSERVABILITY.md](QUICK_START_OBSERVABILITY.md) - Guide rapide
- ✅ [OBSERVABILITY_IMPLEMENTATION.md](OBSERVABILITY_IMPLEMENTATION.md) - Récapitulatif implémentation
- ✅ [observability/LOGQL_EXAMPLES.md](observability/LOGQL_EXAMPLES.md) - Exemples de requêtes

### Scripts

- ✅ `test_logging.py` - Tester le système de logging
- ✅ `start_observability.sh` - Démarrer la stack complète
- ✅ `test_observability.sh` - Vérifier que tout fonctionne

## 🚀 Démarrage Rapide

### 1. Lancer tous les services

```bash
./start_observability.sh
```

### 2. Accéder à Grafana

Ouvrez : **http://localhost:3000**
- Login: `admin`
- Password: `admin`

### 3. Voir le Dashboard

Dashboards → **"Temperature API - Logs Dashboard"**

### 4. Générer des logs de test

```bash
# Test du logging Python
python3 test_logging.py

# Tester l'API (générer du trafic)
curl -H "X-API-Key: admin-key-004" http://localhost:8000/health
```

### 5. Vérifier que tout fonctionne

```bash
./test_observability.sh
```

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [observability/README.md](observability/README.md) | Guide complet de la solution |
| [QUICK_START_OBSERVABILITY.md](QUICK_START_OBSERVABILITY.md) | Démarrage en 3 étapes |
| [OBSERVABILITY_IMPLEMENTATION.md](OBSERVABILITY_IMPLEMENTATION.md) | Détails de l'implémentation |
| [observability/LOGQL_EXAMPLES.md](observability/LOGQL_EXAMPLES.md) | 50+ exemples de requêtes |

## 🔍 Fonctionnalités Clés

### Logs Structurés JSON

Tous les logs sont au format JSON :
```json
{
  "timestamp": "2026-01-29T14:30:00Z",
  "level": "INFO",
  "service": "temperature-api",
  "message": "Requête de données",
  "trace_id": "a1b2c3d4-...",
  "user": "Admin User",
  "city": "Paris"
}
```

### Traçabilité Complète

- **trace_id** unique pour chaque requête
- Suivi de bout en bout dans tous les logs
- Identification de l'utilisateur

### Dashboard Temps Réel

- Logs de tous les services
- Graphiques par niveau (INFO, ERROR, etc.)
- Filtrage des erreurs
- Auto-refresh 10 secondes

### Recherche Puissante

Exemples de requêtes LogQL :
```logql
# Tous les logs API
{service="temperature-api"}

# Erreurs uniquement
{service="temperature-api"} |= "ERROR"

# Logs d'un utilisateur
{service="temperature-api"} | json | user="Admin User"
```

## 🎯 Utilisation dans le Code

### Créer un Logger

```python
from utils.logger import create_logger

logger = create_logger(
    name="mon-service",
    service_name="mon-service",
    log_dir="/var/log/temperature-api"
)
```

### Logger avec Contexte

```python
logger.info("Message simple")
logger.info("Message enrichi", user="john", city="Paris")
logger.error("Erreur détectée", error_code=500)
```

### Traçage

```python
from utils.logger import set_trace_id, set_user_id

trace_id = set_trace_id()  # Générer un trace_id
set_user_id("john.doe")    # Définir l'utilisateur

# Tous les logs suivants incluront trace_id et user
logger.info("Traitement démarré")
```

## 📊 Accès aux Interfaces

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana | http://localhost:3000 | admin / admin |
| Loki API | http://localhost:3100 | - |
| Temperature API | http://localhost:8000 | Voir README |
| API Docs | http://localhost:8000/docs | - |

## 🧪 Tests

```bash
# Test système de logging
python3 test_logging.py

# Test infrastructure complète
./test_observability.sh

# Générer du trafic API
curl -H "X-API-Key: admin-key-004" http://localhost:8000/health
curl -H "X-API-Key: admin-key-004" http://localhost:8000/cities
```

## 📈 Dashboard Grafana

Le dashboard "Temperature API - Logs Dashboard" comprend :

1. **API Logs** - Flux en temps réel de tous les logs
2. **Logs par niveau** - Graphique temporel (INFO, ERROR, etc.)
3. **Erreurs récentes** - Filtrage automatique des erreurs
4. **ETL Logs** - Logs du job Spark ETL
5. **Windy Streaming Logs** - Logs du streaming temps réel

## 💡 Exemples de Requêtes

### Grafana Explore

```logql
# Tous les logs des 15 dernières minutes
{service="temperature-api"}

# Erreurs uniquement
{service="temperature-api"} |= "ERROR"

# Logs contenant "Paris"
{service="temperature-api"} |~ ".*Paris.*"

# Nombre de logs par minute
sum(count_over_time({service="temperature-api"} [1m]))

# Taux d'erreur
sum(rate({service="temperature-api"} |= "ERROR" [5m]))
```

### Via API Loki

```bash
# Requête directe
curl -G "http://localhost:3100/loki/api/v1/query" \
  --data-urlencode 'query={service="temperature-api"}' \
  | jq .
```

## 🔧 Configuration

### Rétention des Logs

**Par défaut : 7 jours**

Modifier dans [observability/loki-config.yml](observability/loki-config.yml#L40) :
```yaml
limits_config:
  retention_period: 168h  # 7 jours
```

### Niveau de Log

**Par défaut : INFO**

Changer via variable d'environnement :
```bash
export LOG_LEVEL=DEBUG
docker compose up -d api
```

## 🛑 Arrêter les Services

```bash
# Arrêter tout
docker compose down

# Supprimer aussi les volumes (données Loki/Grafana)
docker compose down -v
```

## 📚 Ressources

- **Loki Documentation** : https://grafana.com/docs/loki/latest/
- **LogQL Query Language** : https://grafana.com/docs/loki/latest/logql/
- **Grafana Dashboards** : https://grafana.com/docs/grafana/latest/dashboards/

## ✨ Bénéfices

- 🔍 **Debugging facilité** avec traçabilité complète
- 📊 **Visibilité en temps réel** sur tous les services
- 🚨 **Détection proactive** des problèmes
- 📈 **Métriques** de performance et qualité
- 🔐 **Audit** des actions utilisateurs
- 🎯 **Optimisation** via identification des goulots

---

## 🎉 C'est prêt !

La solution d'observabilité est opérationnelle.

**Prochaines étapes :**
1. Démarrer : `./start_observability.sh`
2. Ouvrir Grafana : http://localhost:3000
3. Explorer les logs et créer vos propres dashboards !

**Besoin d'aide ?**
- Guide rapide : [QUICK_START_OBSERVABILITY.md](QUICK_START_OBSERVABILITY.md)
- Documentation : [observability/README.md](observability/README.md)
- Exemples : [observability/LOGQL_EXAMPLES.md](observability/LOGQL_EXAMPLES.md)

**Date de mise en place** : 29 janvier 2026
