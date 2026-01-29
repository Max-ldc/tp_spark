"""
Scripts de génération de certificats X.509 pour l'API.
Génère CA, certificats serveur et certificats clients.

Usage:
    python generate_certificates.py
"""
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_private_key(key_size: int = 2048) -> rsa.RSAPrivateKey:
    """Génère une clé privée RSA."""
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
        backend=default_backend()
    )


def save_private_key(key, path: str, password: str = None):
    """Sauvegarde une clé privée."""
    if password:
        encryption = serialization.BestAvailableEncryption(password.encode())
    else:
        encryption = serialization.NoEncryption()
    
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption
    )
    
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(pem)
    
    os.chmod(path, 0o600)  # Permissions restrictives
    print(f"✓ Clé privée sauvegardée: {path}")


def save_certificate(cert, path: str):
    """Sauvegarde un certificat."""
    pem = cert.public_bytes(serialization.Encoding.PEM)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(pem)
    print(f"✓ Certificat sauvegardé: {path}")


def generate_ca_certificate(
    cert_dir: str = "certs",
    validity_days: int = 3650  # 10 ans
) -> tuple:
    """
    Génère l'autorité de certification (CA) root.
    
    Returns:
        (ca_cert, ca_key)
    """
    print("\n" + "="*70)
    print("📋 Génération de l'Autorité de Certification (CA)")
    print("="*70)
    
    ca_key = generate_private_key(key_size=4096)
    
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "FR"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "France"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Paris"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "CESI"),
        x509.NameAttribute(NameOID.COMMON_NAME, "CESI Temperature API CA"),
    ])
    
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=validity_days))
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_cert_sign=True,
                crl_sign=True,
                key_encipherment=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(ca_key, hashes.SHA256(), default_backend())
    )
    
    # Sauvegarder
    save_private_key(ca_key, f"{cert_dir}/ca/ca-key.pem")
    save_certificate(ca_cert, f"{cert_dir}/ca/ca-cert.pem")
    
    return ca_cert, ca_key


def generate_server_certificate(
    ca_cert: x509.Certificate,
    ca_key: rsa.RSAPrivateKey,
    cert_dir: str = "certs",
    validity_days: int = 365
) -> tuple:
    """Génère le certificat serveur."""
    print("\n" + "="*70)
    print("🖥️  Génération du Certificat Serveur")
    print("="*70)
    
    server_key = generate_private_key()
    
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "FR"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "France"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Paris"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "CESI"),
        x509.NameAttribute(NameOID.COMMON_NAME, "api.cesi-temperature.local"),
    ])
    
    server_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.issuer)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=validity_days))
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.DNSName("api.cesi-temperature.local"),
                x509.DNSName("*.cesi-temperature.local"),
            ]),
            critical=False,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=True,
        )
        .sign(ca_key, hashes.SHA256(), default_backend())
    )
    
    save_private_key(server_key, f"{cert_dir}/server/server-key.pem")
    save_certificate(server_cert, f"{cert_dir}/server/server-cert.pem")
    
    return server_cert, server_key


def generate_client_certificate(
    client_name: str,
    client_role: str,
    ca_cert: x509.Certificate,
    ca_key: rsa.RSAPrivateKey,
    cert_dir: str = "certs",
    validity_days: int = 730  # 2 ans
) -> tuple:
    """
    Génère un certificat client.
    
    Args:
        client_name: Nom du client (ex: "client1")
        client_role: Rôle (BASIC, ANALYST, WINDY, ADMIN)
        ca_cert: Certificat CA
        ca_key: Clé privée CA
        cert_dir: Répertoire de sortie
        validity_days: Durée de validité
        
    Returns:
        (client_cert, client_key)
    """
    print(f"\n👤 Génération du certificat client: {client_name} ({client_role})")
    
    client_key = generate_private_key()
    
    # Convention: CN inclut le rôle (ex: CN=client1-ANALYST)
    cn = f"{client_name}-{client_role}"
    
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "FR"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "France"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Paris"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "CESI"),
        x509.NameAttribute(NameOID.COMMON_NAME, cn),
    ])
    
    client_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.issuer)
        .public_key(client_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=validity_days))
        .add_extension(
            x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH]),
            critical=True,
        )
        .sign(ca_key, hashes.SHA256(), default_backend())
    )
    
    # Créer le répertoire clients
    clients_dir = f"{cert_dir}/clients"
    Path(clients_dir).mkdir(parents=True, exist_ok=True)
    
    save_private_key(client_key, f"{clients_dir}/{client_name}-key.pem")
    save_certificate(client_cert, f"{clients_dir}/{client_name}-cert.pem")
    
    return client_cert, client_key


def main():
    """Génère tous les certificats."""
    cert_dir = "certs"
    
    print("\n" + "🔐 "*20)
    print("🔐  GÉNÉRATEUR DE CERTIFICATS X.509 - CESI Temperature API")
    print("🔐 "*20)
    
    # 1. Générer le CA
    ca_cert, ca_key = generate_ca_certificate(cert_dir)
    
    # 2. Générer le certificat serveur
    generate_server_certificate(ca_cert, ca_key, cert_dir)
    
    # 3. Générer les certificats clients
    clients = [
        ("client-basic", "BASIC"),
        ("client-analyst", "ANALYST"),
        ("client-windy", "WINDY"),
        ("client-admin", "ADMIN"),
    ]
    
    print("\n" + "="*70)
    print("📋 Génération des Certificats Clients")
    print("="*70)
    
    for client_name, client_role in clients:
        generate_client_certificate(client_name, client_role, ca_cert, ca_key, cert_dir)
    
    # 4. Afficher le résumé
    print("\n" + "="*70)
    print("✅ Certificats générés avec succès!")
    print("="*70)
    print(f"\n📁 Répertoire: {os.path.abspath(cert_dir)}")
    print(f"   ├── ca/")
    print(f"   │   ├── ca-cert.pem          (Certificat CA)")
    print(f"   │   └── ca-key.pem           (Clé CA - GARDER SECRET)")
    print(f"   ├── server/")
    print(f"   │   ├── server-cert.pem      (Certificat serveur)")
    print(f"   │   └── server-key.pem       (Clé serveur - GARDER SECRET)")
    print(f"   └── clients/")
    for client_name, _ in clients:
        print(f"       ├── {client_name}-cert.pem")
        print(f"       └── {client_name}-key.pem")
    
    print("\n🔑 Rôles des clients générés:")
    for client_name, role in clients:
        print(f"   • {client_name}: {role}")
    
    print("\n📝 Configuration pour FastAPI:")
    print(f"   CA_CERT_PATH = '{cert_dir}/ca/ca-cert.pem'")
    print(f"   SERVER_CERT_PATH = '{cert_dir}/server/server-cert.pem'")
    print(f"   SERVER_KEY_PATH = '{cert_dir}/server/server-key.pem'")


if __name__ == "__main__":
    main()
