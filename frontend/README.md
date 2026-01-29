# Frontend - Page de Connexion Keycloak

Interface web moderne pour l'authentification à l'API CESI Temperature.

## 🎨 Fonctionnalités

- **Authentification Keycloak SSO** : Connexion sécurisée avec OAuth2/OIDC
- **Authentification API Key** : Pour les développeurs
- **Dashboard interactif** : Test des endpoints de l'API
- **Design moderne** : Glassmorphism, animations fluides, responsive

## 🚀 Démarrage Rapide

### 1. Démarrer Keycloak

```bash
docker compose up -d keycloak
```

Keycloak sera disponible sur http://localhost:8080

**Console Admin** :
- URL : http://localhost:8080/admin
- Utilisateur : `admin`
- Mot de passe : `admin`

### 2. Ouvrir la page de connexion

Ouvrez `frontend/login.html` dans votre navigateur ou utilisez Live Server.

### 3. Se connecter

**Utilisateurs de test disponibles** :

| Utilisateur | Mot de passe | Rôle | Accès |
|-------------|--------------|------|-------|
| `basic-user` | `basic123` | BASIC | Données de base |
| `analyst-user` | `analyst123` | ANALYST | Analyses historiques |
| `windy-user` | `windy123` | WINDY | Données temps réel |
| `admin` | `admin123` | ADMIN | Accès complet |

**Ou utilisez une clé API** :
- `basic-key-001`
- `analyst-key-002`
- `windy-key-003`
- `admin-key-004`

## 📁 Structure

```
frontend/
├── login.html              # Page de connexion
├── dashboard.html          # Dashboard avec tests API
├── app.js                  # Logique Keycloak et auth
├── styles.css              # Styles modernes
└── silent-check-sso.html   # SSO check (Keycloak)
```

## 🔧 Configuration

### Keycloak

Le realm `temperature-api` est automatiquement importé au démarrage de Keycloak.

Configuration dans `keycloak/temperature-api-realm.json` :
- Realm : `temperature-api`
- Client : `temperature-frontend`
- Rôles : BASIC, ANALYST, WINDY, ADMIN

### API

CORS est configuré pour accepter :
- `http://localhost:*`
- `http://127.0.0.1:*`
- `file://` (fichiers locaux)

## 🧪 Test

1. Ouvrez `login.html`
2. Cliquez sur "Keycloak SSO"
3. Connectez-vous avec `admin` / `admin123`
4. Accédez au dashboard
5. Testez les endpoints de l'API

## 🎨 Captures d'écran

La page de connexion propose :
- Choix entre Keycloak SSO et API Key
- Design moderne avec dégradés et animations
- Affichage des informations utilisateur après connexion
- Redirection vers le dashboard

Le dashboard permet de :
- Voir le profil utilisateur
- Tester les endpoints de l'API
- Voir les réponses JSON en temps réel
- Se déconnecter

## 🔐 Sécurité

- Tokens JWT avec expiration (1h)
- Rafraîchissement automatique des tokens
- Validation côté serveur
- CORS configuré pour limiter les origines

## 📖 Documentation

Pour plus d'informations sur l'authentification hybride, consultez [HYBRID_AUTH.md](../HYBRID_AUTH.md).
