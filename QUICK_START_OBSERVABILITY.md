# Guide de Démarrage Rapide - Observabilité

## 🎯 Objectif

Ce guide vous permet de démarrer rapidement la solution d'observabilité des logs pour le projet Temperature API.

## 🚀 Démarrage en 3 étapes

### 1. Démarrer tous les services

```bash
./start_observability.sh
```

Ou manuellement :

```bash
docker compose up -d --build
```

### 2. Accéder à Grafana

Ouvrez votre navigateur : **http://localhost:3000**

- **Login** : `admin`
- **Password** : `admin`

### 3. Visualiser les logs

1. Dans Grafana, cliquez sur **"Dashboards"** (icône grille à gauche)
2. Sélectionnez **"Temperature API - Logs Dashboard"**
3. Vous verrez les logs en temps réel de tous les services

## 📊 Que vais-je voir ?

Le dashboard affiche :

- **API Logs** : Tous les logs de l'API REST
- **Logs par niveau** : Graphique montrant INFO, ERROR, WARNING, etc.
- **Erreurs récentes** : Filtrage automatique des erreurs
- **ETL Logs** : Logs du job Spark d'extraction
- **Windy Streaming Logs** : Logs du streaming temps réel

## 🧪 Générer des logs de test

### Test 1 : Vérifier le logging Python

```bash
python3 test_logging.py
```

Vous devriez voir des logs JSON dans `./logs/test-service.log`

### Test 2 : Générer du trafic API

```bash
# Obtenir un token
TOKEN=$(curl -s -X POST "http://localhost:8000/auth/token?api_key=admin-key-004" | jq -r .access_token)

# Faire quelques requêtes
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/health
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/cities
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/data?limit=10
```

### Test 3 : Générer une erreur

```bash
# Tentative avec mauvaise clé API
curl -H "X-API-Key: invalid-key" http://localhost:8000/health
```

Allez dans Grafana, panneau **"Erreurs récentes"** pour voir l'erreur !

## 🔍 Rechercher dans les logs

### Via Grafana Explore

1. Cliquez sur **"Explore"** (icône boussole à gauche)
2. Sélectionnez la datasource **"Loki"**
3. Essayez ces requêtes :

```logql
# Tous les logs de l'API
{service="temperature-api"}

# Uniquement les erreurs
{service="temperature-api"} |= "ERROR"

# Logs contenant "Paris"
{service="temperature-api"} | json | message =~ ".*Paris.*"

# Logs d'un utilisateur spécifique
{service="temperature-api"} | json | user="Admin User"
```

### Via API Loki

```bash
# Récupérer les derniers logs
curl -G -s "http://localhost:3100/loki/api/v1/query" \
  --data-urlencode 'query={service="temperature-api"}' \
  --data-urlencode 'limit=10' \
  | jq .
```

## 🎓 Comprendre les logs JSON

Exemple de log structuré :

```json
{
  "timestamp": "2026-01-29T14:30:00Z",
  "level": "INFO",
  "service": "temperature-api",
  "message": "Requête de données",
  "trace_id": "a1b2c3d4-...",
  "user": "Admin User",
  "city": "Paris",
  "limit": 100
}
```

**Avantages** :
- ✅ Facilement parsable par Loki
- ✅ Contexte riche (user, city, trace_id)
- ✅ Traçabilité de bout en bout
- ✅ Recherche et filtrage puissants

## 📈 Surveiller en temps réel

### Dashboard auto-refresh

Le dashboard se rafraîchit automatiquement toutes les 10 secondes.

Pour changer :
1. Cliquez sur l'icône d'horloge en haut à droite
2. Sélectionnez l'intervalle souhaité (5s, 10s, 30s, 1m)

### Plage de temps

Par défaut : **dernière heure**

Pour changer :
1. Cliquez sur la sélection de temps en haut à droite
2. Choisissez une plage (15m, 1h, 6h, 24h, etc.)

## 🛑 Arrêter les services

```bash
docker compose down
```

Pour supprimer aussi les volumes (données Loki/Grafana) :

```bash
docker compose down -v
```

## 🔧 Dépannage

### "Cannot connect to Loki"

Vérifiez que Loki est démarré :

```bash
docker ps | grep loki
docker logs loki
```

### "No data in dashboard"

1. Vérifiez que l'API est en cours d'exécution :
   ```bash
   docker ps | grep spark-api
   ```

2. Générez du trafic pour créer des logs :
   ```bash
   curl -H "X-API-Key: admin-key-004" http://localhost:8000/health
   ```

3. Attendez quelques secondes pour que Promtail collecte les logs

### "Permission denied" sur les logs

```bash
sudo chmod -R 777 logs/
```

## 📚 Documentation complète

Pour aller plus loin :
- **Observabilité** : [observability/README.md](observability/README.md)
- **API** : [HYBRID_AUTH.md](HYBRID_AUTH.md)
- **Architecture** : [README.md](README.md)

## 💡 Astuces

### Créer une alerte

1. Dans Grafana, allez dans **Alerting** > **Alert rules**
2. Créez une règle, exemple :
   - Nom: "Taux d'erreur élevé"
   - Condition: `sum(rate({service="temperature-api"} |= "ERROR" [5m])) > 10`
   - Notification: Email, Slack, etc.

### Exporter des logs

```bash
# Via API Loki
curl -G "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={service="temperature-api"}' \
  --data-urlencode 'start=2026-01-29T00:00:00Z' \
  --data-urlencode 'end=2026-01-29T23:59:59Z' \
  > logs_export.json
```

### Logs Docker natifs

```bash
# Voir les logs d'un conteneur
docker compose logs -f api

# Avec timestamps
docker compose logs -f -t api

# Dernières 100 lignes
docker compose logs --tail=100 api
```

---

**Bon monitoring ! 📊🔍**
