"""
Module de validation des certificats X.509.
Valide les certificats clients et extrait les informations d'authentification.
"""
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
import ssl
import socket
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes


class CertificateValidator:
    """Valide et analyse les certificats X.509."""
    
    def __init__(self, ca_cert_path: Optional[str] = None):
        """
        Initialise le validateur.
        
        Args:
            ca_cert_path: Chemin vers le certificat de l'autorité de certification (CA)
        """
        self.ca_cert_path = ca_cert_path
        self.ca_cert = None
        
        if ca_cert_path and os.path.exists(ca_cert_path):
            try:
                with open(ca_cert_path, "rb") as f:
                    self.ca_cert = x509.load_pem_x509_certificate(
                        f.read(), 
                        default_backend()
                    )
            except Exception as e:
                print(f"⚠️  Impossible de charger le CA: {e}")
    
    def validate_certificate_pem(self, cert_pem: str) -> tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Valide un certificat au format PEM (chaîne).
        
        Args:
            cert_pem: Certificat au format PEM
            
        Returns:
            (is_valid, cert_info, error_message)
        """
        try:
            cert_bytes = cert_pem.encode() if isinstance(cert_pem, str) else cert_pem
            cert = x509.load_pem_x509_certificate(cert_bytes, default_backend())
            return self._validate_certificate_object(cert)
        except Exception as e:
            return False, None, f"Impossible de charger le certificat: {str(e)}"
    
    def validate_certificate_file(self, cert_path: str) -> tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Valide un certificat depuis un fichier.
        
        Args:
            cert_path: Chemin vers le fichier certificat
            
        Returns:
            (is_valid, cert_info, error_message)
        """
        try:
            if not os.path.exists(cert_path):
                return False, None, f"Fichier certificat non trouvé: {cert_path}"
            
            with open(cert_path, "rb") as f:
                cert = x509.load_pem_x509_certificate(f.read(), default_backend())
            
            return self._validate_certificate_object(cert)
        except Exception as e:
            return False, None, f"Erreur lors de la validation du fichier: {str(e)}"
    
    def _validate_certificate_object(self, cert: x509.Certificate) -> tuple[bool, Optional[Dict[str, Any]], str]:
        """Valide un objet certificat X.509."""
        
        # 1. Vérifier la date d'expiration
        now = datetime.now(timezone.utc)
        if cert.not_valid_before_utc > now:
            return False, None, "Certificat pas encore valide"
        
        if cert.not_valid_after_utc < now:
            return False, None, "Certificat expiré"
        
        # 2. Vérifier la signature du CA (optionnel)
        # Note: Vérification simplifiée - en production, utiliser pyOpenSSL ou cryptography avancée
        if self.ca_cert:
            try:
                # Vérifié via le fichier CA - comparaison de l'issuer
                if cert.issuer != self.ca_cert.subject:
                    return False, None, "Certificat non signé par ce CA"
            except Exception as e:
                return False, None, f"Erreur lors de la vérification du CA: {str(e)}"
        
        # 3. Extraire les informations
        cert_info = self._extract_certificate_info(cert)
        
        return True, cert_info, ""
    
    def _extract_certificate_info(self, cert: x509.Certificate) -> Dict[str, Any]:
        """Extrait les informations du certificat."""
        info = {
            "subject": cert.subject.rfc4514_string(),
            "issuer": cert.issuer.rfc4514_string(),
            "valid_from": cert.not_valid_before_utc,
            "valid_until": cert.not_valid_after_utc,
            "serial_number": cert.serial_number,
            "version": cert.version.name,
        }
        
        # Extraire le CN (Common Name) - identité du client
        try:
            cn_attr = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
            if cn_attr:
                info["cn"] = cn_attr[0].value
        except Exception:
            pass
        
        # Extraire les Subject Alternative Names (SAN)
        try:
            san_ext = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
            info["san"] = [name.value for name in san_ext.value]
        except Exception:
            pass
        
        # Extraire les rôles depuis les extensions personnalisées ou attributs
        # Format: CN=username-ROLE ou comme extension personnalisée
        info["role"] = self._extract_role_from_cert(cert)
        
        return info
    
    def _extract_role_from_cert(self, cert: x509.Certificate) -> str:
        """
        Extrait le rôle du certificat.
        Convention: CN=username-ROLE (ex: CN=client1-ANALYST)
        """
        try:
            cn_attr = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
            if cn_attr:
                cn_value = cn_attr[0].value
                # Format: "username-ROLE"
                if "-" in cn_value:
                    role = cn_value.split("-")[-1].upper()
                    if role in ["BASIC", "ANALYST", "WINDY", "ADMIN"]:
                        return role
        except Exception:
            pass
        
        # Par défaut : BASIC
        return "BASIC"
    
    def get_certificate_fingerprint(self, cert: x509.Certificate, hash_algo: str = "sha256") -> str:
        """Calcule l'empreinte du certificat."""
        hash_obj = getattr(hashes, hash_algo.upper())()
        fingerprint = cert.fingerprint(hash_obj)
        return fingerprint.hex()


class ClientCertificateExtractor:
    """Extrait le certificat client depuis la requête HTTPS."""
    
    @staticmethod
    def get_client_cert_from_ssl_context(ssl_sock: ssl.SSLSocket) -> Optional[str]:
        """
        Extrait le certificat client depuis un socket SSL.
        
        Args:
            ssl_sock: Socket SSL avec certificat client
            
        Returns:
            Certificat au format PEM ou None
        """
        try:
            cert_der = ssl_sock.getpeercert(binary_form=True)
            if not cert_der:
                return None
            
            from cryptography.hazmat.primitives import serialization
            cert = x509.load_der_x509_certificate(cert_der, default_backend())
            return cert.public_bytes(serialization.Encoding.PEM).decode()
        except Exception:
            return None
    
    @staticmethod
    def parse_client_cert_header(cert_header: str) -> Optional[str]:
        """
        Parse un certificat passé en header HTTP (base64).
        
        Args:
            cert_header: Certificat encodé en base64
            
        Returns:
            Certificat au format PEM ou None
        """
        import base64
        
        try:
            cert_der = base64.b64decode(cert_header)
            cert = x509.load_der_x509_certificate(cert_der, default_backend())
            from cryptography.hazmat.primitives import serialization
            return cert.public_bytes(serialization.Encoding.PEM).decode()
        except Exception:
            return None
