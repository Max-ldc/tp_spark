# 📜 CHANGELOG

## [1.0.0] - 2026-01-28

### 🎉 Release initiale - Authentification Hybride

#### ✨ Nouvelles fonctionnalités

- ✅ **Authentification Hybride**
  - Support des certificats X.509 (priorité haute)
  - Support JWT Bearer tokens (priorité moyenne)
  - Support API Keys statiques (priorité basse)
  
- ✅ **Endpoints d'authentification**
  - `POST /auth/token` : Génération de JWT depuis API Key
  - `POST /auth/certificate` : Validation de certificat X.509
  
- ✅ **Module d'authentification** (`src/auth/`)
  - `HybridAuthManager` : Gestionnaire principal
  - `CertificateValidator` : Validateur X.509
  - `create_hybrid_auth_dependency()` : Intégration FastAPI

- ✅ **Scripts utilitaires**
  - `generate_certificates.py` : Génération CA + certificats clients
  - `test_hybrid_auth.py` : Suite de tests complète
  - `add_client_certificate.py` : Ajout rapide de certificats
  - `auth_cli.py` : CLI pour les tests

- ✅ **Documentation**
  - `HYBRID_AUTH.md` : Guide complet (cas d'usage, endpoints, certificats)
  - `IMPLEMENTATION_SUMMARY.md` : Résumé technique
  - `src/auth/README.md` : Documentation du module

#### 🔧 Modifications

- **`src/api/main.py`**
  - Intégration du système hybride d'authentification
  - Remplacement de `require_api_key` par `require_auth`
  - Nouveaux endpoints `/auth/token` et `/auth/certificate`
  
- **`requirements.txt`**
  - Ajout de `cryptography` pour la gestion des certificats

- **`.gitignore`**
  - Ajout des certificats (`.pem`, `.key`, etc.)
  - Ajout du répertoire `certs/`

#### 🛡️ Sécurité

- Certificats X.509 avec validation de date d'expiration
- Extraction sécurisée du rôle depuis le CN du certificat
- Support optionnel du CA pour vérification de signature
- Gestion sécurisée des clés privées (`.gitignore`)

#### 📊 Architecture

```
Authentification hybride avec priorité :
1. Certificat X.509 (⭐⭐⭐ haute sécurité)
2. JWT Bearer Token (⭐⭐ moyen terme)
3. API Key statique (⭐ développement)
```

#### 🧪 Tests

- Suite complète de tests dans `test_hybrid_auth.py`
- Tests unitaires dans `tests/test_auth.py`
- CLI d'intégration avec `auth_cli.py`

#### ✅ Rétro-compatibilité

- 100% rétro-compatible avec le système précédent
- Les API Keys existantes continuent de fonctionner
- Migration transparente pour les clients JWT

#### 📚 Documentation

- Guide complet d'utilisation
- Exemples curl et Python
- Bonnes pratiques de sécurité
- Troubleshooting

#### 🚀 Prochaines étapes (v1.1+)

- [ ] mTLS complet (HTTPS client certificates)
- [ ] Révocation de certificats (CRL/OCSP)
- [ ] Base de données pour les API Keys
- [ ] Rotation automatique de JWT
- [ ] OAuth2 / OpenID Connect
- [ ] Rate limiting par client
- [ ] Audit logging
- [ ] Dashboard de gestion

---

## Format de versioning

- **MAJOR.MINOR.PATCH** (sémantic versioning)
- `1.0.0` : Authentification hybride complète
- `1.1.0` : mTLS et certificats avancés (prévu)
- `2.0.0` : OAuth2 complet (futur)

---

## 🎯 Objectifs réalisés

| Objectif | Statut |
|----------|--------|
| Certificats X.509 | ✅ Complété |
| Validation certificats | ✅ Complété |
| JWT Bearer tokens | ✅ Conservé |
| API Keys statiques | ✅ Conservé |
| Authentification hybride | ✅ Complété |
| Scripts de génération | ✅ Complété |
| Suite de tests | ✅ Complété |
| Documentation | ✅ Complété |
| Sécurité | ✅ Complété |
| Rétro-compatibilité | ✅ 100% |

---

**Version actuelle:** 1.0.0  
**Date de release:** 28 Janvier 2026  
**Statut:** Production Ready ✅
