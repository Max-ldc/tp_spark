# 🔐 Module d'Authentification Hybride

Ce module implémente un système d'authentification **hybride** pour l'API FastAPI.

## 📦 Contenu

- **`hybrid_auth.py`** : Gestionnaire principal d'authentification
  - `HybridAuthManager` : Classe principale
  - `create_hybrid_auth_dependency()` : Dépendance FastAPI Security
  
- **`cert_validator.py`** : Validation des certificats X.509
  - `CertificateValidator` : Validateur de certificats
  - `ClientCertificateExtractor` : Extraction depuis requête HTTP

- **`__init__.py`** : Package initialization

## 🎯 Utilisation

### Dans FastAPI

```python
from auth import HybridAuthManager, create_hybrid_auth_dependency

# Initialiser
auth_manager = HybridAuthManager(
    jwt_secret="your-secret",
    jwt_algorithm="HS256",
    ca_cert_path="certs/ca/ca-cert.pem",
    valid_api_keys={...}
)

# Créer la dépendance
require_auth = create_hybrid_auth_dependency(auth_manager)

# Utiliser
@app.get("/endpoint")
async def endpoint(api_info: dict = Security(require_auth)):
    return api_info
```

## 🔄 Flux d'authentification

```
Requête entrante
    ↓
[1] Vérifier Certificat X.509
    ├─ Valide → Extraire rôle
    └─ Non → Continuer
    ↓
[2] Vérifier JWT Bearer Token
    ├─ Valide → Extraire payload
    └─ Non → Continuer
    ↓
[3] Vérifier API Key
    ├─ Valide → Retourner info
    └─ Non → 401 Unauthorized
```

## 📊 Retour d'authentification

Structure du dict retourné :

```python
{
    "auth_method": "jwt",  # "certificate", "jwt", ou "api_key"
    "name": "John Doe",
    "role": "ADMIN",
    "max_results": 1000,
    "cert_info": {...}  # Optionnel, si certificat utilisé
}
```

## 🔑 Clés disponibles

- `BASIC` : Accès de base
- `ANALYST` : Analyses + historique
- `WINDY` : Données temps réel
- `ADMIN` : Accès complet

## 📚 Documentation

- [HYBRID_AUTH.md](../HYBRID_AUTH.md) : Guide complet
- [IMPLEMENTATION_SUMMARY.md](../IMPLEMENTATION_SUMMARY.md) : Résumé technique
