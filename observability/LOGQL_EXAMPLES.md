# Exemples de Requêtes LogQL

Ce fichier contient des exemples de requêtes LogQL utiles pour interroger les logs dans Grafana.

## 🔍 Requêtes de Base

### Tous les logs d'un service
```logql
{service="temperature-api"}
```

### Logs d'un service sur une plage de temps
```logql
{service="temperature-api"} [5m]
```

### Filtrer par niveau
```logql
{service="temperature-api"} | json | level="ERROR"
```

### Recherche de texte simple
```logql
{service="temperature-api"} |= "Paris"
```

### Recherche de texte (exclusion)
```logql
{service="temperature-api"} != "DEBUG"
```

## 📊 Requêtes d'Agrégation

### Nombre total de logs sur 5 minutes
```logql
sum(count_over_time({service="temperature-api"} [5m]))
```

### Logs par niveau (graphique empilé)
```logql
sum(count_over_time({service="temperature-api"} [5m])) by (level)
```

### Taux de logs par seconde
```logql
sum(rate({service="temperature-api"} [5m]))
```

### Logs par utilisateur
```logql
sum(count_over_time({service="temperature-api"} [5m])) by (user)
```

## ⚠️ Surveillance des Erreurs

### Taux d'erreur
```logql
sum(rate({service="temperature-api"} |= "ERROR" [5m]))
```

### Pourcentage d'erreurs
```logql
sum(rate({service="temperature-api"} |= "ERROR" [5m])) 
/ 
sum(rate({service="temperature-api"} [5m]))
```

### Top 5 des erreurs fréquentes
```logql
topk(5, sum(count_over_time({service="temperature-api"} |= "ERROR" [1h])) by (message))
```

### Alertes critiques
```logql
{service="temperature-api"} | json | level="CRITICAL"
```

## 👤 Requêtes par Utilisateur

### Logs d'un utilisateur spécifique
```logql
{service="temperature-api"} | json | user="Admin User"
```

### Nombre de requêtes par utilisateur
```logql
sum(count_over_time({service="temperature-api"} | json | user!="" [1h])) by (user)
```

### Erreurs par utilisateur
```logql
sum(count_over_time({service="temperature-api"} |= "ERROR" | json [1h])) by (user)
```

## 🌍 Requêtes Métier (Température API)

### Requêtes sur une ville spécifique
```logql
{service="temperature-api"} | json | city="Paris"
```

### Requêtes par pays
```logql
sum(count_over_time({service="temperature-api"} | json | country!="" [1h])) by (country)
```

### Requêtes Windy (temps réel)
```logql
{service="temperature-api"} |~ "windy|Windy"
```

### Anomalies détectées
```logql
{service="temperature-api"} |~ "anomal|Anomal"
```

## 🔎 Recherche Avancée

### Regex sur le message
```logql
{service="temperature-api"} | json | message =~ ".*température.*"
```

### Filtrer par fonction Python
```logql
{service="temperature-api"} | json | function="get_data"
```

### Logs d'un module spécifique
```logql
{service="temperature-api"} | json | module="main"
```

### Filtrer par trace_id (suivre une requête)
```logql
{service="temperature-api"} | json | trace_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

## 📈 Métriques de Performance

### Durée moyenne des requêtes (si loggée)
```logql
avg_over_time({service="temperature-api"} | json | unwrap duration_ms [5m])
```

### Requêtes les plus lentes (percentile 95)
```logql
quantile_over_time(0.95, {service="temperature-api"} | json | unwrap duration_ms [5m])
```

### Débit de requêtes par minute
```logql
sum(rate({service="temperature-api"} | json | message =~ ".*Requête.*" [1m])) * 60
```

## 🔢 Comparaisons et Calculs

### Comparer deux services
```logql
sum(count_over_time({service=~"temperature-api|spark-etl"} [5m])) by (service)
```

### Logs avec des valeurs numériques spécifiques
```logql
{service="temperature-api"} | json | limit > 100
```

### Logs sans erreurs (succès)
```logql
{service="temperature-api"} | json | level!="ERROR" | level!="CRITICAL"
```

## 🕐 Requêtes Temporelles

### Logs de la dernière heure
```logql
{service="temperature-api"}
```
(Ajuster la plage de temps dans l'UI : Last 1 hour)

### Logs entre deux dates
```logql
{service="temperature-api"}
```
(Ajuster : From: 2026-01-29 00:00:00, To: 2026-01-29 23:59:59)

### Comparer hier vs aujourd'hui
```logql
sum(count_over_time({service="temperature-api"} [1d] offset 1d))
vs
sum(count_over_time({service="temperature-api"} [1d]))
```

## 🚨 Alertes Recommandées

### 1. Taux d'erreur élevé (> 5%)
```logql
sum(rate({service="temperature-api"} |= "ERROR" [5m])) 
/ 
sum(rate({service="temperature-api"} [5m])) 
> 0.05
```

### 2. Service indisponible (aucun log depuis 2 min)
```logql
absent_over_time({service="temperature-api"} [2m])
```

### 3. Erreur critique
```logql
count_over_time({service="temperature-api"} | json | level="CRITICAL" [5m]) > 0
```

### 4. Pic de trafic (> 100 req/min)
```logql
sum(rate({service="temperature-api"} [1m])) * 60 > 100
```

## 💡 Astuces

### Combiner plusieurs filtres
```logql
{service="temperature-api"} 
| json 
| level="ERROR" 
| user="Admin User" 
| city=~"Paris|London"
```

### Extraire et formater
```logql
{service="temperature-api"} 
| json 
| line_format "{{.timestamp}} - {{.user}}: {{.message}}"
```

### Logs distincts par champ
```logql
count(count_over_time({service="temperature-api"} | json [5m])) by (user)
```

### Logs sans un champ spécifique
```logql
{service="temperature-api"} | json | trace_id=""
```

## 📝 Variables pour Dashboards

Créer des dashboards dynamiques avec des variables :

### Variable : Service
```logql
label_values(service)
```

### Variable : Niveau de log
```logql
label_values(level)
```

### Variable : Utilisateur
```logql
label_values({service="temperature-api"}, user)
```

Utiliser dans les requêtes :
```logql
{service="$service"} | json | level="$level"
```

## 🎯 Exemples d'Utilisation Réelle

### Debugging : Tracer une requête utilisateur
```logql
{service="temperature-api"} 
| json 
| trace_id="<ID_FROM_RESPONSE_HEADER>"
```

### Audit : Actions d'un utilisateur sur 24h
```logql
{service="temperature-api"} 
| json 
| user="john.doe" 
[24h]
```

### Performance : Identifier les requêtes lentes
```logql
{service="temperature-api"} 
| json 
| duration_ms > 1000
```

### Monitoring : Santé du service
```logql
sum(rate({service="temperature-api"} [5m])) by (level)
```

---

**Pour plus d'informations sur LogQL** : https://grafana.com/docs/loki/latest/logql/
