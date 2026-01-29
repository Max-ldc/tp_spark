// Configuration API - détection automatique
const getApiUrl = () => {
    // Si on accède via localhost, utiliser localhost
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        return 'http://127.0.0.1:8000';
    }
    // Sinon, utiliser l'IP du serveur sur le port 8000
    return `http://${window.location.hostname}:8000`;
};

const API_URL = getApiUrl();
console.log('API URL:', API_URL);

let currentUser = null;

// Initialisation au chargement de la page
document.addEventListener('DOMContentLoaded', () => {
    // Vérification de l'authentification si on est sur le dashboard
    if (window.location.href.includes('dashboard.html')) {
        checkAuth();
    } else {
        // Rediriger vers le dashboard si déjà connecté
        const user = sessionStorage.getItem('user');
        if (user) {
            window.location.href = 'dashboard.html';
        }
    }
});

// Connexion avec API Key
async function loginWithApiKey() {
    const apiKeyInput = document.getElementById('api-key-input');
    const apiKey = apiKeyInput ? apiKeyInput.value.trim() : '';

    if (!apiKey) {
        alert('Veuillez entrer une clé API');
        return;
    }

    try {
        // Tester la clé API avec l'endpoint /auth/test
        const response = await fetch(`${API_URL}/auth/test`, {
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
        alert('Erreur lors de la connexion.\n\nDétails: ' + error.message + '\n\nURL API: ' + API_URL + '\n\nVérifiez que l\'API est accessible depuis votre navigateur.');
    }
}

// Afficher les informations utilisateur sur la page de login après succès
function showUserInfo() {
    const apiKeyForm = document.getElementById('api-key-form');
    const userInfoDiv = document.getElementById('user-info');

    if (apiKeyForm) apiKeyForm.style.display = 'none';

    if (userInfoDiv) {
        document.getElementById('username').textContent = currentUser.name;
        document.getElementById('user-role').textContent = currentUser.role;
        // document.getElementById('auth-method').textContent = currentUser.authMethod; // Élément supprimé du HTML
        userInfoDiv.style.display = 'block';
    }
}

// Vérifier l'authentification sur le dashboard
function checkAuth() {
    const user = sessionStorage.getItem('user');
    if (!user) {
        window.location.href = 'login.html';
        return;
    }

    const userData = JSON.parse(user);
    currentUser = userData;

    // Mise à jour de l'UI du dashboard
    const nameEl = document.getElementById('dashboard-username');
    const roleEl = document.getElementById('dashboard-role');
    const methodEl = document.getElementById('dashboard-method');
    const avatarEl = document.getElementById('avatar');

    if (nameEl) nameEl.textContent = userData.name;
    if (roleEl) roleEl.textContent = userData.role;
    if (methodEl) methodEl.textContent = '• ' + userData.authMethod;
    if (avatarEl) avatarEl.textContent = userData.name.charAt(0).toUpperCase();

    // Gestion de l'affichage RBAC (Role-Based Access Control)
    updateDashboardUI(userData.role);
}

// Mettre à jour l'interface selon le rôle
function updateDashboardUI(role) {
    const sections = {
        basic: document.getElementById('section-basic'),
        analyst: document.getElementById('section-analyst'),
        windy: document.getElementById('section-windy'),
        admin: document.getElementById('section-admin')
    };

    // Masquer tout par défaut (sauf basic qui est toujours là)
    if (sections.analyst) sections.analyst.style.display = 'none';
    if (sections.windy) sections.windy.style.display = 'none';
    if (sections.admin) sections.admin.style.display = 'none';

    // Logique cumulative des rôles
    // ADMIN voit tout
    if (role === 'ADMIN') {
        if (sections.analyst) sections.analyst.style.display = 'block';
        if (sections.windy) sections.windy.style.display = 'block';
        if (sections.admin) sections.admin.style.display = 'block';
    }
    // ANALYST voit BASIC + ANALYST
    else if (role === 'ANALYST') {
        if (sections.analyst) sections.analyst.style.display = 'block';
    }
    // WINDY voit BASIC + WINDY
    else if (role === 'WINDY') {
        if (sections.windy) sections.windy.style.display = 'block';
    }
    // BASIC ne voit que BASIC (déjà affiché par défaut)
}

// Aller au dashboard
function goToDashboard() {
    window.location.href = 'dashboard.html';
}

// Déconnexion
function logout() {
    // Nettoyer le sessionStorage
    sessionStorage.clear();
    currentUser = null;

    // Rediriger vers login
    window.location.href = 'login.html';
}
