# 🔧 Guide de Dépannage - Observabilité

## Problèmes Courants et Solutions

### ❌ Erreur 504 : Grafana ne peut pas se connecter à Loki

**Symptôme** :
```
Status: 504. Message: Get "http://loki:3100/loki/api/v1/query_range...": 
dial tcp: lookup loki on 127.0.0.11:53: i/o timeout
```

**Cause** : Les conteneurs ne sont pas sur le même réseau Docker.

**Solution** : ✅ **DÉJÀ CORRIGÉ**

Le fichier `docker-compose.yml` a été mis à jour pour inclure un réseau partagé `app-network` pour tous les services.

**Vérification** :
```bash
# Tester la connexion depuis Grafana vers Loki
docker exec grafana wget -q -O- http://loki:3100/ready

# Devrait afficher: ready
```

---

### ❌ Loki : "permission denied" lors du démarrage

**Symptôme** :
```
mkdir /tmp/loki/rules: permission denied
error initialising module: ruler-storage
```

**Cause** : Loki n'a pas les permissions pour créer les répertoires.

**Solution** : ✅ **DÉJÀ CORRIGÉ**

- Volume monté sur `/loki` (au lieu de `/tmp/loki`)
- Configuration mise à jour dans `observability/loki-config.yml`
- Conteneur exécuté en tant que root (`user: "0"`)

---

### ❌ Aucun log dans Grafana

**Symptôme** : Dashboard vide, pas de logs visibles.

**Causes possibles** :

#### 1. Loki pas encore prêt
```bash
# Vérifier le statut
curl http://localhost:3100/ready

# Devrait afficher: ready
# Si "Ingester not ready", attendre 15-20 secondes
```

#### 2. Promtail ne collecte pas les logs
```bash
# Vérifier les logs de Promtail
docker logs promtail 2>&1 | grep -i error

# Vérifier les métriques
curl http://localhost:9080/metrics | grep promtail_sent_entries_total
```

**Solution** :
```bash
# Redémarrer Promtail
docker compose restart promtail

# Générer des logs de test
python3 test_logging.py
```

#### 3. Logs pas encore ingérés
Les logs peuvent prendre 10-30 secondes à apparaître.

```bash
# Attendre et vérifier
sleep 30
curl "http://localhost:3100/loki/api/v1/labels" | jq .
```

---

### ❌ Dashboard ne se charge pas

**Symptôme** : Dashboard "Temperature API - Logs Dashboard" introuvable.

**Solution** :
```bash
# 1. Vérifier que les fichiers sont montés
docker exec grafana ls -la /etc/grafana/provisioning/dashboards/

# 2. Redémarrer Grafana
docker compose restart grafana

# 3. Attendre 10 secondes
sleep 10

# 4. Vérifier dans Grafana UI
open http://localhost:3000
# Dashboards → Browse → Temperature API - Logs Dashboard
```

---

### ❌ Datasource Loki non connectée

**Symptôme** : "Data source connected, but no labels received."

**Solution** :
```bash
# 1. Vérifier que Loki est accessible
curl http://localhost:3100/ready

# 2. Tester depuis Grafana
docker exec grafana wget -q -O- http://loki:3100/ready

# 3. Vérifier la configuration datasource
docker exec grafana cat /etc/grafana/provisioning/datasources/datasources.yml

# 4. Redémarrer Grafana
docker compose restart grafana
```

---

### ❌ Logs Docker non collectés

**Symptôme** : Les logs Docker stdout/stderr n'apparaissent pas.

**Vérification** :
```bash
# Vérifier que Promtail a accès au socket Docker
docker exec promtail ls -la /var/run/docker.sock

# Devrait afficher: srw-rw---- ... docker.sock
```

**Solution** :
```bash
# Redémarrer Promtail avec les bonnes permissions
docker compose down promtail
docker compose up -d promtail
```

---

### ❌ API non démarrée

**Symptôme** : Dashboard vide car l'API n'est pas lancée.

**Solution** :
```bash
# Démarrer l'API
docker compose up -d api

# Vérifier qu'elle tourne
docker ps | grep spark-api

# Générer du trafic pour créer des logs
curl -H "X-API-Key: admin-key-004" http://localhost:8000/health
```

---

## 🔍 Commandes de Diagnostic

### Vérifier tous les services
```bash
# Status des conteneurs
docker compose ps

# Santé de Loki
curl http://localhost:3100/ready

# Santé de Grafana
curl http://localhost:3000/api/health

# Labels disponibles dans Loki
curl http://localhost:3100/loki/api/v1/labels | jq .
```

### Vérifier les logs des conteneurs
```bash
# Loki
docker logs loki 2>&1 | tail -20

# Promtail
docker logs promtail 2>&1 | tail -20

# Grafana
docker logs grafana 2>&1 | tail -20
```

### Vérifier la connectivité réseau
```bash
# Lister les réseaux
docker network ls

# Inspecter le réseau app-network
docker network inspect tp_spark_app-network

# Tester la résolution DNS
docker exec grafana ping -c 2 loki
docker exec promtail ping -c 2 loki
```

### Vérifier les volumes
```bash
# Lister les volumes
docker volume ls | grep loki

# Inspecter le volume Loki
docker volume inspect tp_spark_loki-data
```

---

## 🔄 Procédure de Redémarrage Complet

Si rien ne fonctionne, redémarrez tout :

```bash
# 1. Arrêter tous les conteneurs
docker compose down

# 2. (Optionnel) Supprimer les volumes pour repartir à zéro
docker compose down -v
docker volume rm tp_spark_loki-data tp_spark_grafana-data 2>/dev/null

# 3. Redémarrer
docker compose up -d loki promtail grafana

# 4. Attendre que Loki soit prêt (30 secondes)
sleep 30
curl http://localhost:3100/ready

# 5. Vérifier Grafana
curl http://localhost:3000/api/health

# 6. Générer des logs de test
python3 test_logging.py

# 7. Attendre l'ingestion (30 secondes)
sleep 30

# 8. Vérifier dans Grafana
open http://localhost:3000
```

---

## ✅ Test Complet

Utilisez le script de test automatique :

```bash
./test_observability.sh
```

Ce script vérifie :
- ✓ Conteneurs en cours d'exécution
- ✓ Loki Ready
- ✓ Loki API fonctionnelle
- ✓ Grafana opérationnel
- ✓ Logging Python
- ✓ Ingestion des logs

---

## 📞 Aide Supplémentaire

Si le problème persiste :

1. **Logs détaillés** :
   ```bash
   docker compose logs -f loki
   ```

2. **Vérifier la configuration** :
   ```bash
   cat observability/loki-config.yml
   cat observability/promtail-config.yml
   cat observability/grafana/datasources.yml
   ```

3. **Consulter la documentation** :
   - [observability/README.md](observability/README.md)
   - [QUICK_START_OBSERVABILITY.md](QUICK_START_OBSERVABILITY.md)

---

**Dernière mise à jour** : 29 janvier 2026  
**Corrections appliquées** :
- ✅ Réseau Docker partagé (`app-network`)
- ✅ Permissions Loki corrigées
- ✅ Chemins de volumes mis à jour
