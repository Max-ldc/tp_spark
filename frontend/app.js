// Configuration Keycloak
const keycloakConfig = {
    url: 'http://localhost:8080/',
    realm: 'temperature-api',
    clientId: 'temperature-frontend'
};

let keycloak = null;
let currentToken = null;
let currentUser = null;

// Initialisation au chargement de la page
document.addEventListener('DOMContentLoaded', () => {
    initKeycloak();
});

// Initialiser Keycloak
async function initKeycloak() {
    try {
        // Timeout de 5 secondes pour l'initialisation Keycloak
        const timeoutPromise = new Promise((_, reject) =>
            setTimeout(() => reject(new Error('Timeout Keycloak')), 5000)
        );

        const initPromise = (async () => {
            keycloak = new Keycloak(keycloakConfig);

            const authenticated = await keycloak.init({
                onLoad: 'check-sso',
                silentCheckSsoRedirectUri: window.location.origin + '/silent-check-sso.html',
                checkLoginIframe: false
            });

            if (authenticated) {
                await handleAuthenticated();
            } else {
                showAuthMethods();
            }
        })();

        await Promise.race([initPromise, timeoutPromise]);

    } catch (error) {
        console.error('Erreur initialisation Keycloak:', error);
        // Si Keycloak n'est pas disponible, afficher quand même les méthodes d'auth
        showAuthMethods();
    }
}

// Afficher les méthodes d'authentification
function showAuthMethods() {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('auth-methods').style.display = 'block';
}

// Connexion avec Keycloak
async function loginWithKeycloak() {
    if (!keycloak) {
        alert('Keycloak n\'est pas disponible. Veuillez vérifier que le serveur Keycloak est démarré sur http://localhost:8080');
        return;
    }

    try {
        await keycloak.login({
            redirectUri: window.location.origin + '/frontend/login.html'
        });
    } catch (error) {
        console.error('Erreur connexion Keycloak:', error);
        alert('Erreur lors de la connexion avec Keycloak');
    }
}

// Afficher le formulaire API Key
function showApiKeyForm() {
    document.getElementById('api-key-form').style.display = 'block';
}

// Masquer le formulaire API Key
function hideApiKeyForm() {
    document.getElementById('api-key-form').style.display = 'none';
    document.getElementById('api-key-input').value = '';
}

// Connexion avec API Key
async function loginWithApiKey() {
    const apiKey = document.getElementById('api-key-input').value.trim();

    if (!apiKey) {
        alert('Veuillez entrer une clé API');
        return;
    }

    try {
        // Tester la clé API avec l'endpoint /auth/test
        const response = await fetch('http://127.0.0.1:8000/auth/test', {
            mode: 'cors',
            headers: {
                'X-API-Key': apiKey
            }
        });

        if (response.ok) {
            const data = await response.json();
            currentUser = {
                name: data.name,
                role: data.role,
                authMethod: 'API Key',
                maxResults: data.max_results
            };
            currentToken = apiKey;

            // Sauvegarder dans sessionStorage
            sessionStorage.setItem('authMethod', 'api-key');
            sessionStorage.setItem('apiKey', apiKey);
            sessionStorage.setItem('user', JSON.stringify(currentUser));

            showUserInfo();
        } else {
            const error = await response.json();
            alert('Clé API invalide: ' + (error.detail || 'Erreur inconnue'));
        }
    } catch (error) {
        console.error('Erreur connexion API Key:', error);
        alert('Erreur lors de la connexion.\n\nDétails: ' + error.message + '\n\nAssurez-vous que:\n1. L\'API est démarrée sur http://127.0.0.1:8000\n2. Vous ouvrez cette page via un serveur HTTP (pas file://)\n\nUtilisez: python -m http.server 5500 dans le dossier frontend');
    }
}

// Gérer l'authentification réussie avec Keycloak
async function handleAuthenticated() {
    try {
        await keycloak.loadUserProfile();

        // Extraire les rôles
        const roles = keycloak.tokenParsed.realm_access?.roles || [];
        const apiRole = roles.find(r => ['BASIC', 'ANALYST', 'WINDY', 'ADMIN'].includes(r.toUpperCase())) || 'BASIC';

        currentUser = {
            name: keycloak.tokenParsed.preferred_username || keycloak.tokenParsed.name || 'Utilisateur',
            role: apiRole.toUpperCase(),
            authMethod: 'Keycloak SSO',
            email: keycloak.tokenParsed.email
        };
        currentToken = keycloak.token;

        // Sauvegarder dans sessionStorage
        sessionStorage.setItem('authMethod', 'keycloak');
        sessionStorage.setItem('token', keycloak.token);
        sessionStorage.setItem('refreshToken', keycloak.refreshToken);
        sessionStorage.setItem('user', JSON.stringify(currentUser));

        showUserInfo();

        // Rafraîchir le token automatiquement
        setInterval(async () => {
            try {
                const refreshed = await keycloak.updateToken(30);
                if (refreshed) {
                    currentToken = keycloak.token;
                    sessionStorage.setItem('token', keycloak.token);
                }
            } catch (error) {
                console.error('Erreur rafraîchissement token:', error);
            }
        }, 60000); // Toutes les minutes

    } catch (error) {
        console.error('Erreur chargement profil:', error);
        showAuthMethods();
    }
}

// Afficher les informations utilisateur
function showUserInfo() {
    document.getElementById('auth-methods').style.display = 'none';
    document.getElementById('loading').style.display = 'none';

    const userInfoDiv = document.getElementById('user-info');
    document.getElementById('username').textContent = currentUser.name;
    document.getElementById('user-role').textContent = currentUser.role;
    document.getElementById('auth-method').textContent = currentUser.authMethod;

    userInfoDiv.style.display = 'block';
}

// Aller au dashboard
function goToDashboard() {
    window.location.href = 'dashboard.html';
}

// Déconnexion
async function logout() {
    const authMethod = sessionStorage.getItem('authMethod');

    if (authMethod === 'keycloak' && keycloak) {
        await keycloak.logout({
            redirectUri: window.location.origin + '/frontend/login.html'
        });
    }

    // Nettoyer le sessionStorage
    sessionStorage.clear();
    currentToken = null;
    currentUser = null;

    // Recharger la page
    window.location.reload();
}
