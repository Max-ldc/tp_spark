# 🔐 Système d'Authentification Hybride - CESI Temperature API

## Vue d'ensemble

L'API supporte maintenant une **authentification hybride** avec priorité :

```
Certificats X.509 > JWT Bearer Token > API Keys Statiques
```

### 🎯 Trois méthodes d'authentification

| Méthode | Priorité | Cas d'usage | Sécurité |
|---------|----------|-----------|---------|
| **Certificats X.509** | 1️⃣ Haute | Clients de confiance, production | ⭐⭐⭐ |
| **JWT Bearer Token** | 2️⃣ Moyenne | Applications web, intégrations | ⭐⭐ |
| **API Keys Statiques** | 3️⃣ Basse | Tests, développement | ⭐ |

---

## 🚀 Démarrage rapide

### 1️⃣ Générer les certificats

```bash
cd src/jobs
python generate_certificates.py
```

Cela crée :
- `certs/ca/` - Autorité de certification
- `certs/server/` - Certificat serveur
- `certs/clients/` - Certificats clients (4 rôles)

### 2️⃣ Démarrer l'API

```bash
python src/api/main.py
```

---

## 📋 Utilisation

### Méthode 1: JWT Bearer Token (Recommandée)

#### Étape 1 : Obtenir un JWT

```bash
# Avec API Key en paramètre
curl -X POST "http://localhost:8000/auth/token?api_key=admin-key-004"

# Ou avec header
curl -X POST -H "X-API-Key: admin-key-004" http://localhost:8000/auth/token
```

**Réponse :**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "auth_method": "jwt"
}
```

#### Étape 2 : Utiliser le JWT

```bash
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Requête avec Bearer token
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/cities
```

---

### Méthode 2: Certificats X.509 (Entreprise)

#### Étape 1 : Valider un certificat

```bash
# Lire le certificat client
CERT=$(cat certs/clients/client-admin-cert.pem)

# Valider auprès de l'API
curl -X POST "http://localhost:8000/auth/certificate?cert_pem=$CERT"
```

**Réponse :**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "auth_method": "certificate",
  "certificate_info": {
    "cn": "client-admin-ADMIN",
    "role": "ADMIN",
    "valid_from": "2026-01-28T...",
    "valid_until": "2028-01-28T...",
    "subject": "C=FR,ST=France,L=Paris,O=CESI,CN=client-admin-ADMIN",
    "issuer": "C=FR,ST=France,L=Paris,O=CESI,CN=CESI Temperature API CA"
  }
}
```

#### Étape 2 : Utiliser le JWT reçu

Même processus qu'avec les JWT normaux.

---

### Méthode 3: API Keys Statiques (Développement)

```bash
# Directement avec le header X-API-Key
curl -H "X-API-Key: admin-key-004" \
     http://localhost:8000/cities

# Ou passer la clé directement (moins sécurisé)
curl http://localhost:8000/cities?api_key=admin-key-004
```

**Clés disponibles :**
```
BASIC    : basic-key-001     (50 résultats max)
ANALYST  : analyst-key-002   (200 résultats max)
WINDY    : windy-key-003     (200 résultats max)
ADMIN    : admin-key-004     (1000 résultats max)
```

---

## 🛡️ Certificats - Détails techniques

### Structure du répertoire

```
certs/
├── ca/
│   ├── ca-cert.pem        ← Certificat CA (public)
│   └── ca-key.pem         ← Clé CA (GARDER SECRET)
├── server/
│   ├── server-cert.pem    ← Certificat serveur
│   └── server-key.pem     ← Clé serveur (GARDER SECRET)
└── clients/
    ├── client-basic-cert.pem
    ├── client-basic-key.pem
    ├── client-analyst-cert.pem
    ├── client-analyst-key.pem
    ├── client-windy-cert.pem
    ├── client-windy-key.pem
    ├── client-admin-cert.pem
    └── client-admin-key.pem
```

### Format des certificats

**Common Name (CN)** encode le rôle : `CN=<username>-<ROLE>`

Exemples :
- `CN=client-basic-BASIC` → Rôle BASIC
- `CN=client-admin-ADMIN` → Rôle ADMIN

L'API extrait automatiquement le rôle du CN.

### Validité

- **CA** : 10 ans
- **Serveur** : 1 an
- **Clients** : 2 ans

### Vérification d'un certificat

```bash
# Voir le contenu d'un certificat
openssl x509 -in certs/clients/client-admin-cert.pem -text

# Vérifier la validité
openssl x509 -in certs/clients/client-admin-cert.pem -noout -dates

# Vérifier la signature
openssl verify -CAfile certs/ca/ca-cert.pem certs/clients/client-admin-cert.pem
```

---

## 🔄 Flux d'authentification

```
┌─────────────────────────────────────┐
│      Requête HTTP entrante          │
└────────────┬────────────────────────┘
             │
             ▼
    ┌─────────────────────┐
    │ 1. Vérifier Cert X509│  Header: X-Client-Cert
    │   (si présent)      │
    └──────────┬──────────┘
               │ Non / Invalide
               ▼
    ┌─────────────────────┐
    │ 2. Vérifier JWT     │  Header: Authorization: Bearer <token>
    │   (si présent)      │
    └──────────┬──────────┘
               │ Non / Invalide
               ▼
    ┌─────────────────────┐
    │ 3. Vérifier API Key │  Header: X-API-Key
    │   (si présent)      │
    └──────────┬──────────┘
               │ Non / Invalide
               ▼
    ┌─────────────────────┐
    │   ❌ 401 Unauthorized│
    └─────────────────────┘

┌─────────────────────┐
│ ✅ Authentifié      │
│ {                   │
│   "name": "...",    │
│   "role": "ADMIN",  │
│   "auth_method": ...│
│ }                   │
└─────────────────────┘
```

---

## 📚 Endpoints d'authentification

### POST `/auth/token`

Génère un JWT depuis une clé API.

**Paramètres :**
- `api_key` (query) : Clé API statique
- `X-API-Key` (header) : Clé API statique

**Réponse :**
```json
{
  "access_token": "string (JWT)",
  "token_type": "bearer",
  "expires_in": 3600,
  "auth_method": "jwt"
}
```

### POST `/auth/certificate`

Valide un certificat X.509 et génère un JWT.

**Paramètres :**
- `cert_pem` (query) : Certificat au format PEM

**Réponse :**
```json
{
  "access_token": "string (JWT)",
  "token_type": "bearer",
  "expires_in": 3600,
  "auth_method": "certificate",
  "certificate_info": {
    "cn": "string",
    "role": "BASIC|ANALYST|WINDY|ADMIN",
    "valid_from": "ISO-8601",
    "valid_until": "ISO-8601",
    "subject": "string",
    "issuer": "string"
  }
}
```

---

## 🔧 Configuration

### Variables d'environnement (optionnel)

```bash
# .env
JWT_SECRET=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=1
CA_CERT_PATH=certs/ca/ca-cert.pem
```

### Code FastAPI

```python
from auth import HybridAuthManager, create_hybrid_auth_dependency

auth_manager = HybridAuthManager(
    jwt_secret="secret",
    jwt_algorithm="HS256",
    ca_cert_path="certs/ca/ca-cert.pem",
    valid_api_keys=VALID_API_KEYS
)

require_auth = create_hybrid_auth_dependency(auth_manager)

# Usage
@app.get("/endpoint")
async def endpoint(api_info: dict = Security(require_auth)):
    return api_info
```

---

## ⚠️ Bonnes pratiques sécurité

### ✅ À faire

- ✓ Garder les clés privées secrètes (`.gitignore`)
- ✓ Utiliser HTTPS en production
- ✓ Renouveler les certificats avant expiration
- ✓ Utiliser des JWT avec expiration courte (1-24h)
- ✓ Valider les certificats clients
- ✓ Logger les authentifications échouées

### ❌ À ne pas faire

- ✗ Committer les clés privées en git
- ✗ Utiliser des API Keys en production
- ✗ Ignorer les erreurs de validation
- ✗ Exposer les erreurs détaillées
- ✗ Réutiliser le même secret JWT
- ✗ Stocker les certificats en clair

---

## 🧪 Tests

### Test avec Python

```python
import requests

# 1. Obtenir un JWT
response = requests.post(
    "http://localhost:8000/auth/token",
    params={"api_key": "admin-key-004"}
)
token = response.json()["access_token"]

# 2. Utiliser le JWT
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(
    "http://localhost:8000/cities",
    headers=headers
)
print(response.json())
```

### Test avec curl

```bash
#!/bin/bash

# 1. Générer JWT
TOKEN=$(curl -X POST "http://localhost:8000/auth/token?api_key=admin-key-004" \
  | jq -r '.access_token')

# 2. Tester endpoint
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/cities

# 3. Tester certificat
CERT=$(cat certs/clients/client-admin-cert.pem)
TOKEN=$(curl -X POST "http://localhost:8000/auth/certificate?cert_pem=$CERT" \
  | jq -r '.access_token')

curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/health
```

---

## 📖 Références

- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [RFC 7519 - JWT](https://tools.ietf.org/html/rfc7519)
- [X.509 Certificates](https://en.wikipedia.org/wiki/X.509)
- [cryptography.io](https://cryptography.io/)
