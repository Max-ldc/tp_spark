"""
Script de test pour l'authentification hybride.
Teste : JWT, Certificats, et API Keys.
"""
import os
import sys
import subprocess
import time
import requests
from pathlib import Path

# Ajouter le path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://localhost:8000"
CERTS_DIR = Path(__file__).parent.parent / "certs"


def test_api_key_authentication():
    """Test l'authentification par API Key."""
    print("\n" + "="*70)
    print("🔑 TEST 1 : Authentification par API Key")
    print("="*70)
    
    try:
        response = requests.get(
            f"{BASE_URL}/cities",
            headers={"X-API-Key": "admin-key-004"},
            timeout=5
        )
        
        if response.status_code == 200:
            print("✅ API Key fonctionnelle")
            print(f"   Réponse: {len(response.json().get('cities', []))} villes")
            return True
        else:
            print(f"❌ Erreur: {response.status_code}")
            print(f"   {response.json()}")
            return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def test_jwt_generation():
    """Test la génération de JWT."""
    print("\n" + "="*70)
    print("🔐 TEST 2 : Génération de JWT")
    print("="*70)
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/token",
            params={"api_key": "admin-key-004"},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            
            if token:
                print("✅ JWT généré avec succès")
                print(f"   Token: {token[:50]}...")
                print(f"   Type: {data.get('token_type')}")
                print(f"   Expiration: {data.get('expires_in')}s")
                return token
            else:
                print("❌ Pas de token dans la réponse")
                return None
        else:
            print(f"❌ Erreur: {response.status_code}")
            print(f"   {response.json()}")
            return None
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None


def test_jwt_usage(token: str):
    """Test l'utilisation d'un JWT."""
    print("\n" + "="*70)
    print("🎯 TEST 3 : Utilisation du JWT")
    print("="*70)
    
    try:
        response = requests.get(
            f"{BASE_URL}/cities",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5
        )
        
        if response.status_code == 200:
            print("✅ JWT fonctionnel")
            print(f"   Réponse: {len(response.json().get('cities', []))} villes")
            return True
        else:
            print(f"❌ Erreur: {response.status_code}")
            print(f"   {response.json()}")
            return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def test_health_check():
    """Test l'endpoint /health."""
    print("\n" + "="*70)
    print("❤️  TEST 4 : Health Check")
    print("="*70)
    
    try:
        response = requests.get(
            f"{BASE_URL}/health",
            headers={"X-API-Key": "admin-key-004"},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API en bonne santé")
            print(f"   Status: {data.get('status')}")
            print(f"   Spark: {data.get('spark')}")
            return True
        else:
            print(f"❌ Erreur: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def test_certificate_endpoint():
    """Test l'endpoint de validation de certificat."""
    print("\n" + "="*70)
    print("📜 TEST 5 : Validation de Certificat")
    print("="*70)
    
    cert_file = CERTS_DIR / "clients" / "client-admin-cert.pem"
    
    if not cert_file.exists():
        print(f"⚠️  Certificat non trouvé: {cert_file}")
        print("   Générez les certificats d'abord:")
        print("   python src/jobs/generate_certificates.py")
        return False
    
    try:
        with open(cert_file, "r") as f:
            cert_pem = f.read()
        
        response = requests.post(
            f"{BASE_URL}/auth/certificate",
            params={"cert_pem": cert_pem},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Certificat valide")
            
            cert_info = data.get("certificate_info", {})
            print(f"   CN: {cert_info.get('cn')}")
            print(f"   Rôle: {cert_info.get('role')}")
            print(f"   Valid from: {cert_info.get('valid_from', '?')[:19]}")
            print(f"   Valid until: {cert_info.get('valid_until', '?')[:19]}")
            
            return True
        else:
            print(f"❌ Erreur: {response.status_code}")
            print(f"   {response.json()}")
            return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def test_invalid_credentials():
    """Test avec des credentials invalides."""
    print("\n" + "="*70)
    print("🚫 TEST 6 : Credentials Invalides")
    print("="*70)
    
    try:
        response = requests.get(
            f"{BASE_URL}/cities",
            headers={"X-API-Key": "invalid-key"},
            timeout=5
        )
        
        if response.status_code in [401, 403]:
            print("✅ Requête correctement rejetée")
            print(f"   Status: {response.status_code}")
            print(f"   Message: {response.json().get('detail', '?')}")
            return True
        else:
            print(f"❌ Devrait être 401/403, reçu: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def main():
    """Lance tous les tests."""
    print("\n" + "🧪 "*35)
    print("🧪  TESTS D'AUTHENTIFICATION HYBRIDE - CESI Temperature API")
    print("🧪 "*35)
    
    print("\n⏳ Vérification de la connexion à l'API...")
    time.sleep(1)
    
    try:
        requests.get(f"{BASE_URL}/health", headers={"X-API-Key": "admin-key-004"}, timeout=2)
        print("✅ API accessible")
    except Exception as e:
        print(f"❌ API non accessible: {e}")
        print("\n   Lancez l'API d'abord:")
        print("   python src/api/main.py")
        return False
    
    # Lancer les tests
    results = []
    
    results.append(("API Key", test_api_key_authentication()))
    
    token = test_jwt_generation()
    results.append(("JWT Generation", token is not None))
    
    if token:
        results.append(("JWT Usage", test_jwt_usage(token)))
    
    results.append(("Health Check", test_health_check()))
    results.append(("Certificate Endpoint", test_certificate_endpoint()))
    results.append(("Invalid Credentials", test_invalid_credentials()))
    
    # Résumé
    print("\n" + "="*70)
    print("📊 RÉSUMÉ DES TESTS")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} : {test_name}")
    
    print(f"\n📈 Résultat: {passed}/{total} tests réussis")
    
    if passed == total:
        print("\n🎉 Tous les tests sont passés!")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) échoué(s)")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
