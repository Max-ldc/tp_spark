# 🌡️ Spark ETL - Analyse de Températures Globales avec API Windy

Projet d'analyse de données climatiques combinant :
- **Données historiques** : Températures mondiales (1743-2013) depuis CSV
- **Données temps réel** : Météo actuelle via API Windy
- **Streaming** : Monitoring continu des conditions météorologiques

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SOURCES DE DONNÉES                            │
├─────────────────────────────────────────────────────────────────┤
│  CSV Historique                    │  API Windy (Temps Réel)    │
│  GlobalLandTemperatures...         │  https://api.windy.com/    │
│  1743-2013                         │  Polling toutes les 60s    │
└──────────┬──────────────────────────┴──────────────┬─────────────┘
           │                                         │
           ▼                                         ▼
┌─────────────────────┐                   ┌─────────────────────┐
│   ETL BATCH         │                   │  ETL STREAMING      │
│   (main.py)         │                   │  (streaming_main.py)│
├─────────────────────┤                   ├─────────────────────┤
│ • Extract CSV       │                   │ • Poll Windy API    │
│ • Transform         │                   │ • Detect anomalies  │
│   - Anomalies       │                   │ • Continuous save   │
│   - Latitude bands  │                   │                     │
│   - Hemispheres     │                   │                     │
│ • Load to Parquet   │                   │                     │
└──────────┬──────────┘                   └──────────┬──────────┘
           │                                         │
           ▼                                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STOCKAGE (Parquet)                            │
├─────────────────────────────────────────────────────────────────┤
│  meteo_enriched/    │  windy_current/    │  windy_streaming/   │
│  Données historiques│  Snapshot actuel   │  Série temporelle   │
│  avec anomalies     │  Comparaison       │  Historique polls   │
└──────────┬──────────┴────────────────────┴─────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    COUCHE SERVICE                                │
├─────────────────────────────────────────────────────────────────┤
│  SparkQueryService         │  WindyQueryService                  │
│  (spark_service.py)        │  (windy_service.py)                 │
│  • Requêtes historiques    │  • Météo actuelle                   │
│  • Statistiques par ville  │  • Anomalies temps réel             │
│  • Tendances latitude      │  • Tendances streaming              │
└──────────┬─────────────────┴─────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API REST (FastAPI)                            │
├─────────────────────────────────────────────────────────────────┤
│  Port 8000 - http://localhost:8000/docs                         │
│                                                                  │
│  HISTORIQUE               │  WINDY (TEMPS RÉEL)                 │
│  /data                    │  /windy/current                     │
│  /stats                   │  /windy/anomalies                   │
│  /anomalies               │  /windy/hemispheres                 │
│  /warming/top             │  /windy/streaming/history           │
│  /hemispheres             │  /windy/streaming/trends/{loc}      │
│  /latitude-bands          │                                     │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Démarrage Rapide

### Prérequis
- Docker & Docker Compose
- Clé API Windy gratuite : https://api.windy.com/keys

### Configuration
```bash
# 1. Cloner le repo et naviguer
cd tp_spark

# 2. Configurer la clé API
cp .env.example .env
# Éditer .env et remplacer WINDY_API_KEY

# 3. Lancer tous les services
docker compose up --build
```

### Services Docker

```yaml
etl:               # Job ETL batch (CSV + Windy snapshot)
  port: 4040       # Spark UI

api:               # API FastAPI de requêtage  
  port: 8000       # API REST
  port: 4041       # Spark UI

windy-streaming:   # Polling continu Windy
  port: 4042       # Spark UI
```

## 📊 Utilisation

### 1. Exécuter l'ETL Batch

```bash
docker compose up etl
```

**Ce job :**
1. Lit le CSV historique (500k+ enregistrements)
2. Enrichit avec calculs :
   - Z-score par ville (détection anomalies)
   - Bandes de latitude
   - Hémisphère (Nord/Sud)
   - Taux de réchauffement
3. Interroge l'API Windy pour données actuelles
4. Compare actuel vs historique
5. Sauvegarde en Parquet optimisé

**Sortie :**
- `data/processed/meteo_enriched/` : Données historiques
- `data/processed/windy_current/` : Snapshot météo actuel

### 2. Lancer l'API

```bash
docker compose up -d api
```

**Endpoints disponibles :**

#### Données Historiques
```bash
# Vue d'ensemble
curl http://localhost:8000/stats

# Anomalies (années exceptionnellement chaudes/froides)
curl http://localhost:8000/anomalies

# Villes qui se réchauffent le plus
curl http://localhost:8000/warming/top

# Comparaison Nord vs Sud
curl http://localhost:8000/hemispheres
```

#### Données Temps Réel (Windy)
```bash
# Météo actuelle toutes localisations
curl http://localhost:8000/windy/current

# Anomalies météo détectées maintenant
curl http://localhost:8000/windy/anomalies

# Stats par hémisphère (temps réel)
curl http://localhost:8000/windy/hemispheres
```

**Documentation interactive :**
http://localhost:8000/docs

### 3. Streaming Continu

```bash
docker compose up -d windy-streaming
```

**Fonctionnement :**
- Poll l'API Windy toutes les 60 secondes
- Compare avec statistiques historiques
- Détecte anomalies en temps réel
- Sauvegarde série temporelle

**Consulter l'historique :**
```bash
# Dernières 100 mesures
curl http://localhost:8000/windy/streaming/history

# Tendances sur 24h pour Paris
curl "http://localhost:8000/windy/streaming/trends/Paris?hours=24"
```

## 🔬 Analyses Disponibles

### Analyse 1 : Détection d'Anomalies
Identifie les années exceptionnellement chaudes/froides en utilisant le z-score :
- **Z > +2** : Exceptionally Hot (au-dessus de 2 écarts-types)
- **Z < -2** : Exceptionally Cold (en-dessous de 2 écarts-types)

```bash
curl http://localhost:8000/anomalies?anomaly_type=Exceptionally%20Hot&limit=10
```

### Analyse 2 : Vitesse de Réchauffement par Latitude
Calcule le taux de réchauffement (°C/décennie) pour chaque bande de latitude :
- Arctic (60°+)
- Northern Temperate (30-60°)
- Tropical North (0-30°)
- Tropical South (0-30°)
- Southern Temperate (-30 à -60°)
- Antarctic (-60°-)

```bash
curl http://localhost:8000/latitude-bands
```

### Analyse 3 : Comparaison Hémisphères
Compare Nord vs Sud sur :
- Température moyenne
- Écart-type
- Nombre d'anomalies
- Taux de réchauffement

```bash
curl http://localhost:8000/hemispheres
```

### Analyse 4 : Météo Actuelle vs Historique
Compare la température actuelle (Windy) avec la moyenne historique de la ville :
- Calcule z-score en temps réel
- Identifie si température actuelle est anormale
- Fournit contexte historique

```bash
curl http://localhost:8000/windy/anomalies
```

## 📁 Structure du Projet

```
tp_spark/
├── src/
│   ├── api/
│   │   └── main.py                # API FastAPI (port 8000)
│   ├── jobs/
│   │   ├── extraction.py          # Extract CSV
│   │   ├── extraction_windy.py    # Extract Windy API
│   │   ├── transformation.py      # Transform CSV
│   │   ├── transformation_windy.py# Transform Windy
│   │   ├── loading.py             # Load to Parquet
│   │   └── streaming_windy.py     # Windy streaming logic
│   ├── services/
│   │   ├── spark_service.py       # Query service (historique)
│   │   └── windy_service.py       # Query service (Windy)
│   ├── utils/
│   │   └── spark_session.py       # Spark config centralisée
│   ├── main.py                    # ETL Batch entry point
│   └── streaming_main.py          # Streaming entry point
├── data/
│   ├── raw/
│   │   └── GlobalLandTemperaturesByCity.csv  # Source
│   └── processed/
│       ├── meteo_enriched/        # Historique enrichi
│       ├── windy_current/         # Snapshot Windy
│       └── windy_streaming/       # Série temporelle
├── config.py                      # Configuration (clés API)
├── docker-compose.yml             # Orchestration services
├── Dockerfile                     # Image Java 17 + Python + Spark
├── requirements.txt               # Dépendances Python
├── ARCHITECTURE_REVIEW.md         # Revue architecture
├── TEST_GUIDE.md                  # Guide de test complet
└── README.md                      # Ce fichier
```

## 🛠️ Technologies

- **Apache Spark 4.1.1** : Traitement distribué
- **PySpark** : API Python pour Spark
- **FastAPI** : API REST moderne
- **Docker** : Conteneurisation
- **Parquet** : Format de stockage columnaire optimisé
- **Windy API** : Données météo temps réel

## 🔧 Configuration

### Fichier `config.py`

```python
# Clé API Windy
WINDY_API_KEY = "votre_clé_ici"

# Activer extraction Windy
ENABLE_WINDY_EXTRACTION = True

# Interval de polling (secondes)
WINDY_POLL_INTERVAL = 60

# Chemins
RAW_DATA_PATH = "data/raw/GlobalLandTemperaturesByCity.csv"
OUTPUT_PATH_METEO = "data/processed/meteo_enriched"
OUTPUT_PATH_WINDY = "data/processed/windy_current"
OUTPUT_PATH_WINDY_STREAMING = "data/processed/windy_streaming"
```

### Variables d'Environnement (.env)

```bash
WINDY_API_KEY=votre_clé_ici
ENABLE_WINDY_EXTRACTION=True
WINDY_POLL_INTERVAL=60
```

## 📈 Performances

### ETL Batch
- **Dataset** : 500k+ enregistrements, 100+ pays, 200+ ans
- **Temps** : ~5-10 min (dépend machine)
- **Output** : ~50 MB Parquet compressé

### API
- **Latence** : <100ms (données en cache Parquet)
- **Throughput** : 100+ req/s

### Streaming
- **Fréquence** : 1 poll/minute
- **Latence** : <2s par poll
- **Rate limit** : Respecte limites API Windy

## 🧪 Tests

Voir [TEST_GUIDE.md](TEST_GUIDE.md) pour guide de test complet.

**Quick test :**
```bash
# 1. Lancer ETL
docker compose up etl

# 2. Lancer API
docker compose up -d api

# 3. Tester
curl http://localhost:8000/health
curl http://localhost:8000/stats
curl http://localhost:8000/windy/current
```

## 🐛 Dépannage

### "Windy extraction enabled but API key not configured"
→ Éditer `config.py` et mettre votre clé API

### "No data extracted from Windy API"
→ Vérifier clé API valide
→ Vérifier connexion internet
→ Vérifier rate limit non dépassé

### API retourne "Aucune donnée disponible"
→ Lancer d'abord `docker compose up etl`
→ Attendre fin du job ETL
→ Vérifier présence des fichiers Parquet

### Erreurs Hadoop sur Windows
→ Déjà géré dans `spark_session.py`
→ Si problème, vérifier `HADOOP_HOME` pointant vers `~\hadoop`

## 📚 Documentation Complète

- [ARCHITECTURE_REVIEW.md](ARCHITECTURE_REVIEW.md) : Revue architecture détaillée
- [TEST_GUIDE.md](TEST_GUIDE.md) : Guide de test exhaustif
- [API Docs](http://localhost:8000/docs) : Documentation interactive Swagger

## 🤝 Contribution

Projet académique - M2 Données Distribuées

## 📄 Licence

Projet éducatif

## 🔗 Ressources

- [API Windy Documentation](https://api.windy.com/point-forecast/docs)
- [PySpark Documentation](https://spark.apache.org/docs/latest/api/python/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
