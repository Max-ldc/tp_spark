# 📋 Index de la Solution d'Observabilité

## 📁 Structure Complète des Fichiers

### 🔧 Configuration Infrastructure

```
observability/
├── loki-config.yml              # Configuration Loki (stockage, rétention)
├── promtail-config.yml          # Configuration Promtail (collecte)
└── grafana/
    ├── datasources.yml          # Connexion Loki datasource
    ├── dashboards.yml           # Provisioning dashboards
    └── dashboard.json           # Dashboard "Temperature API - Logs"
```

### 💻 Code Python

```
src/utils/
├── logger.py                    # Module logging structuré JSON
└── logging_middleware.py        # Middleware FastAPI (logs HTTP auto)
```

### 📚 Documentation

```
├── OBSERVABILITY_READY.md              # 🎯 COMMENCER ICI - Vue d'ensemble
├── QUICK_START_OBSERVABILITY.md        # Guide démarrage rapide (3 étapes)
├── OBSERVABILITY_IMPLEMENTATION.md     # Récapitulatif implémentation
├── observability/README.md             # Documentation technique complète
└── observability/LOGQL_EXAMPLES.md     # 50+ exemples de requêtes
```

### 🧪 Scripts et Tests

```
├── start_observability.sh       # Démarrer la stack complète
├── test_observability.sh        # Tester que tout fonctionne
└── test_logging.py             # Tester le système de logging Python
```

### 🐳 Docker

```
docker-compose.yml               # Services: loki, promtail, grafana (modifié)
```

### 📂 Données

```
logs/                           # Répertoire pour les fichiers de logs
└── .gitignore                  # Exclure *.log du git
```

---

## 🚀 Par où commencer ?

### 1️⃣ Démarrage Ultra-Rapide (2 minutes)

```bash
./start_observability.sh
# Puis ouvrir http://localhost:3000 (admin/admin)
```

**Lire** : [OBSERVABILITY_READY.md](OBSERVABILITY_READY.md)

### 2️⃣ Guide Pas-à-Pas (5 minutes)

**Lire** : [QUICK_START_OBSERVABILITY.md](QUICK_START_OBSERVABILITY.md)

Couvre :
- Démarrage des services
- Navigation dans Grafana
- Génération de logs de test
- Recherche de logs

### 3️⃣ Documentation Complète (15 minutes)

**Lire** : [observability/README.md](observability/README.md)

Couvre :
- Architecture détaillée
- Configuration avancée
- Bonnes pratiques
- Troubleshooting

### 4️⃣ Apprendre LogQL (30 minutes)

**Lire** : [observability/LOGQL_EXAMPLES.md](observability/LOGQL_EXAMPLES.md)

50+ exemples de requêtes :
- Requêtes de base
- Agrégations
- Surveillance erreurs
- Métriques de performance

### 5️⃣ Détails de l'Implémentation

**Lire** : [OBSERVABILITY_IMPLEMENTATION.md](OBSERVABILITY_IMPLEMENTATION.md)

Pour comprendre :
- Ce qui a été créé
- Comment ça fonctionne
- Comment l'intégrer dans du nouveau code

---

## 📖 Guide par Cas d'Usage

### Je veux juste voir les logs maintenant

1. `./start_observability.sh`
2. Ouvrir http://localhost:3000
3. Dashboards → "Temperature API - Logs Dashboard"

### Je veux chercher un log spécifique

1. Dans Grafana, cliquer "Explore"
2. Essayer : `{service="temperature-api"} |~ ".*Paris.*"`
3. Voir : [observability/LOGQL_EXAMPLES.md](observability/LOGQL_EXAMPLES.md)

### Je veux suivre une requête utilisateur

1. Récupérer le `trace_id` du header HTTP `X-Trace-ID`
2. Dans Grafana Explore :
   ```logql
   {service="temperature-api"} | json | trace_id="<ID>"
   ```

### Je veux ajouter du logging dans mon code

**Exemple minimal** :

```python
from utils.logger import create_logger

logger = create_logger(
    name="mon-service",
    service_name="mon-service",
    log_dir="/var/log/temperature-api"
)

logger.info("Message", user="john", action="query")
```

**Voir** : [OBSERVABILITY_IMPLEMENTATION.md#intégration-dans-nouveau-code](OBSERVABILITY_IMPLEMENTATION.md)

### Je veux créer une alerte

1. Grafana → Alerting → Alert rules
2. Créer une règle avec une requête LogQL
3. Exemple : Alerte si taux d'erreur > 5%
   ```logql
   sum(rate({service="temperature-api"} |= "ERROR" [5m])) 
   / 
   sum(rate({service="temperature-api"} [5m])) 
   > 0.05
   ```

### Je veux comprendre l'architecture

**Schéma** :

```
Applications (API, ETL, Streaming)
         ↓ (Logs JSON)
      Promtail (Collecte)
         ↓
        Loki (Stockage)
         ↓
      Grafana (Visualisation)
```

**Lire** : [observability/README.md#architecture](observability/README.md)

---

## 🎯 Fichiers Clés par Tâche

| Tâche | Fichier(s) |
|-------|-----------|
| **Démarrer** | `start_observability.sh` |
| **Tester** | `test_observability.sh`, `test_logging.py` |
| **Configurer Loki** | `observability/loki-config.yml` |
| **Configurer Promtail** | `observability/promtail-config.yml` |
| **Modifier Dashboard** | `observability/grafana/dashboard.json` |
| **Ajouter Logging Code** | `src/utils/logger.py` |
| **Logging HTTP Auto** | `src/utils/logging_middleware.py` |
| **Apprendre LogQL** | `observability/LOGQL_EXAMPLES.md` |

---

## 🔗 Liens Rapides

### Interfaces Web

- **Grafana** : http://localhost:3000 (admin/admin)
- **Loki API** : http://localhost:3100
- **API Docs** : http://localhost:8000/docs
- **Dashboard Direct** : http://localhost:3000/d/temperature-api-logs/temperature-api-logs-dashboard

### Commandes Utiles

```bash
# Démarrer
./start_observability.sh

# Tester
./test_observability.sh

# Voir logs conteneurs
docker compose logs -f loki
docker compose logs -f promtail
docker compose logs -f api

# Générer du trafic
curl -H "X-API-Key: admin-key-004" http://localhost:8000/health

# Arrêter
docker compose down
```

---

## 📊 Résumé des Capacités

✅ **Logs structurés JSON** pour tous les services  
✅ **Traçabilité** avec trace_id unique  
✅ **Collecte automatique** via Promtail  
✅ **Stockage optimisé** dans Loki  
✅ **Dashboard temps réel** dans Grafana  
✅ **Recherche puissante** avec LogQL  
✅ **Rétention 7 jours** (configurable)  
✅ **API Loki** pour intégrations  
✅ **Alerting** (configurable)  
✅ **Documentation complète**  

---

## 🆘 Besoin d'Aide ?

1. **Démarrage** → [OBSERVABILITY_READY.md](OBSERVABILITY_READY.md)
2. **Guide rapide** → [QUICK_START_OBSERVABILITY.md](QUICK_START_OBSERVABILITY.md)
3. **Documentation** → [observability/README.md](observability/README.md)
4. **Requêtes** → [observability/LOGQL_EXAMPLES.md](observability/LOGQL_EXAMPLES.md)
5. **Implémentation** → [OBSERVABILITY_IMPLEMENTATION.md](OBSERVABILITY_IMPLEMENTATION.md)

---

**Mise à jour** : 29 janvier 2026  
**Version** : 1.0  
**Status** : ✅ Prêt à l'emploi
