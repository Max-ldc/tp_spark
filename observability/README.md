# Solution d'Observabilité des Logs

Ce projet utilise une stack complète d'observabilité basée sur **Loki + Promtail + Grafana** pour centraliser et visualiser les logs de tous les services.

## 🏗️ Architecture

```
┌─────────────────┐
│  Applications   │
│  (API, ETL,     │
│   Streaming)    │
└────────┬────────┘
         │ Logs JSON
         ▼
┌─────────────────┐
│    Promtail     │ ◄── Collecte les logs
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│      Loki       │ ◄── Stocke et indexe
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Grafana      │ ◄── Visualisation
└─────────────────┘
```

## 📦 Composants

### 1. **Loki** (Port 3100)
- Base de données de logs optimisée
- Stockage des logs avec indexation par labels
- Rétention configurée à 7 jours
- Query language similaire à Prometheus (LogQL)

### 2. **Promtail** (Port 9080)
- Agent de collecte de logs
- Scrape les fichiers de logs et les logs Docker
- Parsing et enrichissement des logs JSON
- Push des logs vers Loki

### 3. **Grafana** (Port 3000)
- Interface de visualisation
- Dashboards pré-configurés
- Recherche et filtrage avancés
- Alerting (configurable)

## 🚀 Démarrage

### Lancer la stack complète

```bash
docker compose up -d
```

Cela démarre tous les services incluant Loki, Promtail et Grafana.

### Accès aux interfaces

- **Grafana**: http://localhost:3000
  - Login: `admin`
  - Password: `admin`
  
- **Loki API**: http://localhost:3100
  - Endpoint de santé: http://localhost:3100/ready

## 📊 Dashboards Grafana

### Dashboard principal: "Temperature API - Logs Dashboard"

Le dashboard inclut:

1. **API Logs** - Tous les logs de l'API en temps réel
2. **Logs par niveau** - Graphique temporel des logs par niveau (INFO, ERROR, etc.)
3. **Erreurs récentes** - Filtrage automatique des erreurs
4. **ETL Logs** - Logs du job Spark ETL
5. **Windy Streaming Logs** - Logs du streaming Windy

### Navigation

```
Grafana UI
├── Dashboards
│   └── Temperature API - Logs Dashboard
└── Explore
    └── Recherche interactive avec LogQL
```

## 🔍 Recherche de Logs

### Dans Grafana Explore

Exemples de requêtes LogQL:

```logql
# Tous les logs de l'API
{service="temperature-api"}

# Uniquement les erreurs
{service="temperature-api"} |= "ERROR"

# Logs d'un utilisateur spécifique
{service="temperature-api"} | json | user="Admin User"

# Requêtes avec une ville spécifique
{service="temperature-api"} | json | message =~ ".*Paris.*"

# Compte des logs par niveau sur 5 minutes
sum(count_over_time({service="temperature-api"} [5m])) by (level)

# Taux d'erreur
sum(rate({service="temperature-api"} |= "ERROR" [5m]))
```

### Via API Loki

```bash
# Requête directe à Loki
curl -G -s "http://localhost:3100/loki/api/v1/query" \
  --data-urlencode 'query={service="temperature-api"}' \
  | jq .
```

## 📝 Format des Logs

### Logs structurés JSON

Tous les logs sont au format JSON pour faciliter le parsing:

```json
{
  "timestamp": "2026-01-29T14:30:00Z",
  "level": "INFO",
  "service": "temperature-api",
  "logger": "temperature-api",
  "message": "Requête de données",
  "module": "main",
  "function": "get_data",
  "line": 380,
  "trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "user": "Admin User",
  "city": "Paris",
  "limit": 100,
  "role": "ADMIN"
}
```

### Champs disponibles

- `timestamp`: Date/heure UTC (ISO 8601)
- `level`: Niveau de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `service`: Nom du service (temperature-api, spark-etl, etc.)
- `message`: Message principal
- `trace_id`: ID unique pour tracer une requête
- `user`: Utilisateur ayant fait la requête
- **Champs métier**: city, limit, role, etc. (contextuel)

## 🛠️ Configuration

### Fichiers de configuration

```
observability/
├── loki-config.yml          # Configuration Loki
├── promtail-config.yml      # Configuration Promtail
└── grafana/
    ├── datasources.yml      # Datasources Grafana
    ├── dashboards.yml       # Provisioning dashboards
    └── dashboard.json       # Dashboard principal
```

### Modifier la rétention

Éditer [observability/loki-config.yml](observability/loki-config.yml):

```yaml
limits_config:
  retention_period: 168h  # 7 jours par défaut
```

### Ajouter un nouveau job de collecte

Éditer [observability/promtail-config.yml](observability/promtail-config.yml):

```yaml
scrape_configs:
  - job_name: mon-nouveau-service
    static_configs:
      - targets:
          - localhost
        labels:
          job: mon-service
          service: mon-service-name
          __path__: /var/log/mon-service/*.log
```

## 🔧 Intégration dans le Code

### Utiliser le logger structuré

```python
from utils.logger import create_logger

# Créer un logger
logger = create_logger(
    name="mon-service",
    service_name="mon-service",
    log_dir="/var/log/temperature-api",
    log_level="INFO"
)

# Logger avec contexte
logger.info("Message simple")
logger.info("Message avec contexte", user="john", action="query")
logger.error("Une erreur", error_code=500)
logger.exception("Exception capturée")  # Inclut la stack trace
```

### Utiliser le traçage

```python
from utils.logger import set_trace_id, set_user_id

# Définir un trace_id pour suivre une requête
trace_id = set_trace_id()

# Définir l'utilisateur
set_user_id("admin@example.com")

# Tous les logs suivants incluront trace_id et user_id
logger.info("Traitement démarré")
```

## 📈 Monitoring et Alerting

### Créer une alerte dans Grafana

1. Aller dans **Alerting** > **Alert rules**
2. Créer une nouvelle règle
3. Exemple: alerte si taux d'erreur > 10%

```logql
sum(rate({service="temperature-api"} |= "ERROR" [5m])) 
/ 
sum(rate({service="temperature-api"} [5m]))
> 0.1
```

## 🐛 Debugging

### Vérifier les logs de Loki

```bash
docker logs loki
```

### Vérifier les logs de Promtail

```bash
docker logs promtail
```

### Vérifier que Promtail envoie des logs

```bash
# Statistiques Promtail
curl http://localhost:9080/metrics | grep promtail
```

### Tester une requête Loki directement

```bash
curl -G "http://localhost:3100/loki/api/v1/label"
curl -G "http://localhost:3100/loki/api/v1/label/service/values"
```

## 📚 Ressources

- [Documentation Loki](https://grafana.com/docs/loki/latest/)
- [LogQL Query Language](https://grafana.com/docs/loki/latest/logql/)
- [Grafana Dashboards](https://grafana.com/docs/grafana/latest/dashboards/)
- [Promtail Configuration](https://grafana.com/docs/loki/latest/clients/promtail/configuration/)

## 🎯 Best Practices

1. **Utiliser des logs structurés** (JSON) pour faciliter le parsing
2. **Ajouter du contexte** (user, trace_id, action) pour le debugging
3. **Logger aux bons niveaux**:
   - DEBUG: Informations de développement
   - INFO: Événements normaux importants
   - WARNING: Situations anormales mais gérables
   - ERROR: Erreurs nécessitant attention
   - CRITICAL: Échecs critiques du système
4. **Utiliser trace_id** pour suivre les requêtes de bout en bout
5. **Ne pas logger de données sensibles** (mots de passe, tokens, etc.)
6. **Configurer la rotation** pour éviter la saturation disque

## 🔒 Sécurité

- Les logs peuvent contenir des informations sensibles
- En production, activer l'authentification Loki (`auth_enabled: true`)
- Configurer des rôles et permissions dans Grafana
- Utiliser HTTPS pour les connexions
- Auditer régulièrement les logs d'accès
