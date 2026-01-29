"""
Module d'authentification hybride.
Supporte : Certificats X.509 > JWT > API Keys (par ordre de priorité)
"""
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader
import jwt
from .cert_validator import CertificateValidator
import os


class HybridAuthManager:
    """
    Gestionnaire d'authentification hybride.
    Priorité : Certificat X.509 > JWT Bearer > API Key statique
    """
    
    def __init__(
        self,
        jwt_secret: str,
        jwt_algorithm: str = "HS256",
        ca_cert_path: Optional[str] = None,
        valid_api_keys: Optional[Dict[str, Dict[str, Any]]] = None
    ):
        """
        Initialise le gestionnaire d'authentification.
        
        Args:
            jwt_secret: Secret pour la signature JWT
            jwt_algorithm: Algorithme JWT (HS256, etc.)
            ca_cert_path: Chemin vers le certificat CA
            valid_api_keys: Dict des API keys valides
        """
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm
        self.cert_validator = CertificateValidator(ca_cert_path)
        self.valid_api_keys = valid_api_keys or {}
    
    async def authenticate_hybrid(
        self,
        request: Request,
        api_key_header: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Authentifie une requête avec priorité certificat > JWT > API Key.
        
        Args:
            request: Requête FastAPI
            api_key_header: Clé API depuis le header X-API-Key
            
        Returns:
            Dict avec les informations d'authentification
            
        Raises:
            HTTPException: Si l'authentification échoue
        """
        
        # 1. Vérifier le certificat client (mTLS)
        auth_result = self._check_client_certificate(request)
        if auth_result:
            return auth_result
        
        # 2. Vérifier le JWT Bearer token
        auth_result = self._check_jwt_token(request)
        if auth_result:
            return auth_result
        
        # 3. Vérifier l'API Key statique
        if api_key_header:
            auth_result = self._check_api_key(api_key_header)
            if auth_result:
                return auth_result
        
        # Aucune méthode n'a fonctionné
        raise HTTPException(
            status_code=401,
            detail="Authentification requise. "
                   "Utilisez un certificat client, JWT Bearer token, ou API Key"
        )
    
    def _check_client_certificate(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Essaie de valider un certificat client.
        
        Returns:
            Dict d'auth si valide, None sinon
        """
        # Chercher le certificat client dans les headers
        # (certains proxies/reverse proxies passent le certificat)
        cert_header = request.headers.get("X-Client-Cert")
        
        if not cert_header:
            return None
        
        is_valid, cert_info, error_msg = self.cert_validator.validate_certificate_pem(cert_header)
        
        if not is_valid:
            print(f"❌ Certificat invalide: {error_msg}")
            return None
        
        # Certificat valide !
        return {
            "auth_method": "certificate",
            "name": cert_info.get("cn", "unknown"),
            "role": cert_info.get("role", "BASIC"),
            "max_results": self._get_max_results_for_role(cert_info.get("role", "BASIC")),
            "cert_info": cert_info
        }
    
    def _check_jwt_token(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Essaie de valider un JWT Bearer token.
        
        Returns:
            Dict d'auth si valide, None sinon
        """
        auth_header = request.headers.get("Authorization")
        
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header[7:]
        
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return {
                "auth_method": "jwt",
                "name": payload.get("name"),
                "role": payload.get("role", "BASIC"),
                "max_results": payload.get("max_results", 50),
            }
        except jwt.ExpiredSignatureError:
            print("❌ Token JWT expiré")
            return None
        except jwt.InvalidTokenError as e:
            print(f"❌ Token JWT invalide: {e}")
            return None
    
    def _check_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Essaie de valider une API Key statique.
        
        Returns:
            Dict d'auth si valide, None sinon
        """
        if api_key not in self.valid_api_keys:
            print(f"❌ API Key invalide: {api_key}")
            return None
        
        key_info = self.valid_api_keys[api_key]
        return {
            "auth_method": "api_key",
            "name": key_info.get("name"),
            "role": key_info.get("role", "BASIC"),
            "max_results": key_info.get("max_results", 50),
            "api_key": api_key
        }
    
    @staticmethod
    def _get_max_results_for_role(role: str) -> int:
        """Retourne le nombre max de résultats selon le rôle."""
        role_limits = {
            "BASIC": 50,
            "ANALYST": 200,
            "WINDY": 200,
            "ADMIN": 1000
        }
        return role_limits.get(role, 50)
    
    def generate_jwt_token(
        self,
        name: str,
        role: str,
        max_results: int,
        expiration_hours: int = 1
    ) -> Dict[str, Any]:
        """
        Génère un JWT token.
        
        Args:
            name: Nom de l'utilisateur
            role: Rôle (BASIC, ANALYST, WINDY, ADMIN)
            max_results: Nombre max de résultats
            expiration_hours: Durée de validité en heures
            
        Returns:
            Dict avec access_token, token_type, expires_in
        """
        from datetime import timedelta
        
        expiration = datetime.now(timezone.utc) + timedelta(hours=expiration_hours)
        
        payload = {
            "name": name,
            "role": role,
            "max_results": max_results,
            "exp": expiration
        }
        
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": expiration_hours * 3600,
            "auth_method": "jwt"
        }


def create_hybrid_auth_dependency(auth_manager: HybridAuthManager, api_key_header_name: str = "X-API-Key"):
    """
    Crée une dépendance FastAPI Security pour l'authentification hybride.
    """
    api_key_header = APIKeyHeader(name=api_key_header_name, auto_error=False)
    
    async def require_auth(
        request: Request,
        api_key: Optional[str] = Security(api_key_header)
    ) -> Dict[str, Any]:
        """Dépendance Security pour l'authentification hybride."""
        return await auth_manager.authenticate_hybrid(request, api_key)
    
    return require_auth
