"""
Utilitaire pour ajouter rapidement des certificats clients.
Usage: python add_client_certificate.py <username> <role>

Exemple:
  python add_client_certificate.py john-doe ANALYST
  python add_client_certificate.py bot-service WINDY
"""
import sys
import os
from pathlib import Path

# Ajouter le path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.jobs.generate_certificates import (
    generate_client_certificate,
    load_ca_certificate_and_key
)


def load_ca_certificate_and_key(cert_dir: str = "certs"):
    """Charge le CA existant."""
    from cryptography.hazmat.backends import default_backend
    from cryptography import x509
    
    ca_cert_path = f"{cert_dir}/ca/ca-cert.pem"
    ca_key_path = f"{cert_dir}/ca/ca-key.pem"
    
    if not os.path.exists(ca_cert_path) or not os.path.exists(ca_key_path):
        raise FileNotFoundError(
            f"CA non trouvé à {cert_dir}/ca/\n"
            "Générez les certificats d'abord: python src/jobs/generate_certificates.py"
        )
    
    with open(ca_cert_path, "rb") as f:
        ca_cert = x509.load_pem_x509_certificate(f.read(), default_backend())
    
    from cryptography.hazmat.primitives import serialization
    with open(ca_key_path, "rb") as f:
        ca_key = serialization.load_pem_private_key(
            f.read(),
            password=None,
            backend=default_backend()
        )
    
    return ca_cert, ca_key


def main():
    """Crée un nouveau certificat client."""
    if len(sys.argv) < 3:
        print(__doc__)
        print("\nRôles disponibles: BASIC, ANALYST, WINDY, ADMIN")
        sys.exit(1)
    
    username = sys.argv[1]
    role = sys.argv[2].upper()
    
    # Valider le rôle
    valid_roles = ["BASIC", "ANALYST", "WINDY", "ADMIN"]
    if role not in valid_roles:
        print(f"❌ Rôle invalide: {role}")
        print(f"Rôles valides: {', '.join(valid_roles)}")
        sys.exit(1)
    
    cert_dir = "certs"
    
    print("\n" + "="*70)
    print(f"➕ Ajout d'un certificat client")
    print("="*70)
    print(f"\n👤 Utilisateur: {username}")
    print(f"🔐 Rôle: {role}")
    print(f"📁 Répertoire: {cert_dir}")
    
    try:
        # Charger le CA
        print("\n📖 Chargement du CA...")
        ca_cert, ca_key = load_ca_certificate_and_key(cert_dir)
        print("✅ CA chargé")
        
        # Générer le certificat client
        print(f"\n📋 Génération du certificat client...")
        cert, key = generate_client_certificate(
            client_name=username,
            client_role=role,
            ca_cert=ca_cert,
            ca_key=ca_key,
            cert_dir=cert_dir
        )
        
        print("\n" + "="*70)
        print("✅ Certificat créé avec succès!")
        print("="*70)
        print(f"\n📄 Fichiers créés:")
        print(f"   • {cert_dir}/clients/{username}-cert.pem")
        print(f"   • {cert_dir}/clients/{username}-key.pem")
        
        print(f"\n💡 Utilisation:")
        print(f"   CERT=$(cat {cert_dir}/clients/{username}-cert.pem)")
        print(f"   curl -X POST \"http://localhost:8000/auth/certificate?cert_pem=$CERT\"")
        
    except FileNotFoundError as e:
        print(f"\n❌ Erreur: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur lors de la création: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
