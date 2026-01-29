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
    const apiKeyInput = document.getElementById('api-key');
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
    const authTabs = document.querySelector('.auth-tabs');
    const apikeySection = document.getElementById('apikey-section');
    const certSection = document.getElementById('cert-section');
    const userInfoDiv = document.getElementById('user-info');

    if (authTabs) authTabs.style.display = 'none';
    if (apikeySection) apikeySection.style.display = 'none';
    if (certSection) certSection.style.display = 'none';

    if (userInfoDiv) {
        document.getElementById('username').textContent = currentUser.name;
        document.getElementById('user-role').textContent = currentUser.role;
        userInfoDiv.style.display = 'block';
    }
}

// Aller au dashboard
function goToDashboard() {
    window.location.href = 'dashboard.html';
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

// --- Authentification par Certificat ---

function switchTab(tab) {
    const apikeyBtn = document.getElementById('tab-apikey');
    const certBtn = document.getElementById('tab-cert');
    const apikeySection = document.getElementById('apikey-section');
    const certSection = document.getElementById('cert-section');

    if (tab === 'apikey') {
        if (apikeyBtn) apikeyBtn.classList.add('active');
        if (certBtn) certBtn.classList.remove('active');
        if (apikeySection) apikeySection.classList.add('active');
        if (certSection) certSection.classList.remove('active');
    } else {
        if (apikeyBtn) apikeyBtn.classList.remove('active');
        if (certBtn) certBtn.classList.add('active');
        if (apikeySection) apikeySection.classList.remove('active');
        if (certSection) certSection.classList.add('active');
        setupDropZone();
    }
}

let selectedCertFile = null;

function setupDropZone() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('cert-file');

    if (!dropZone || dropZone.dataset.initialized) return;

    dropZone.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', (e) => {
        if (fileInput.files.length) {
            handleCertFile(fileInput.files[0]);
        }
    });

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drop-zone--over');
    });

    ['dragleave', 'dragend'].forEach(type => {
        dropZone.addEventListener(type, () => {
            dropZone.classList.remove('drop-zone--over');
        });
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        if (e.dataTransfer.files.length) {
            fileInput.files = e.dataTransfer.files;
            handleCertFile(e.dataTransfer.files[0]);
        }
        dropZone.classList.remove('drop-zone--over');
    });

    dropZone.dataset.initialized = "true";
}

function handleCertFile(file) {
    if (!file.name.endsWith('.pem')) {
        alert("Veuillez sélectionner un fichier .pem valide.");
        return;
    }
    selectedCertFile = file;
    document.getElementById('file-name').textContent = file.name;
    document.getElementById('file-info').style.display = 'flex';
    document.getElementById('drop-zone').style.display = 'none';

    const loginBtn = document.getElementById('login-cert-btn');
    if (loginBtn) {
        loginBtn.disabled = false;
        console.log('Cert button enabled');
    } else {
        console.error('Login cert button not found!');
    }
}

function removeCertFile() {
    selectedCertFile = null;
    document.getElementById('cert-file').value = "";
    document.getElementById('file-info').style.display = 'none';
    document.getElementById('drop-zone').style.display = 'flex';
    document.getElementById('login-cert-btn').disabled = true;
}

async function loginWithCertificate() {
    if (!selectedCertFile) return;

    const btn = document.getElementById('login-cert-btn');
    btn.disabled = true;
    btn.textContent = 'Connexion...';

    const reader = new FileReader();
    reader.onload = async (e) => {
        const certPem = e.target.result;

        try {
            const url = new URL(`${API_URL}/auth/certificate`);
            url.searchParams.append('cert_pem', certPem);

            const response = await fetch(url, {
                method: 'POST',
                mode: 'cors'
            });

            if (response.ok) {
                const data = await response.json();
                currentUser = {
                    name: data.name,
                    role: data.role,
                    authMethod: 'Certificat X.509',
                    maxResults: data.max_results
                };
                sessionStorage.setItem('jwt', data.access_token);
                sessionStorage.setItem('user', JSON.stringify(currentUser));
                showUserInfo();
            } else {
                const error = await response.json();
                alert(`Erreur Certificat: ${error.detail || 'Authentification échouée'}`);
                removeCertFile();
            }
        } catch (error) {
            console.error('Login error:', error);
            alert('Erreur technique lors de la connexion par certificat.');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Se connecter avec certificat';
        }
    };
    reader.readAsText(selectedCertFile);
}

// Initialisation au chargement
window.addEventListener('DOMContentLoaded', () => {
    // Vérifier si on est sur la page login
    if (document.getElementById('apikey-section')) {
        // Optionnel: charger le certificat si déjà en mémoire
    }
});

// Déconnexion
function logout() {
    // Nettoyer le sessionStorage
    sessionStorage.clear();
    currentUser = null;

    // Rediriger vers login
    window.location.href = 'login.html';
}
