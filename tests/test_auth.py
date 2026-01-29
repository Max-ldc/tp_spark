"""
Tests unitaires pour le module d'authentification hybride.
Utilise pytest.

Exécution: pytest tests/test_auth.py -v
"""
import pytest
import sys
import os
from datetime import datetime, timedelta, timezone

# Ajouter le path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.auth import HybridAuthManager, CertificateValidator


class TestHybridAuthManager:
    """Tests du gestionnaire d'authentification hybride."""
    
    @pytest.fixture
    def auth_manager(self):
        """Crée un gestionnaire pour les tests."""
        return HybridAuthManager(
            jwt_secret="test-secret",
            jwt_algorithm="HS256",
            ca_cert_path=None,  # Pas de CA pour les tests
            valid_api_keys={
                "test-key": {"name": "Test User", "role": "ADMIN", "max_results": 1000}
            }
        )
    
    def test_api_key_validation(self, auth_manager):
        """Test la validation d'une API Key valide."""
        result = auth_manager._check_api_key("test-key")
        
        assert result is not None
        assert result["name"] == "Test User"
        assert result["role"] == "ADMIN"
        assert result["auth_method"] == "api_key"
    
    def test_invalid_api_key(self, auth_manager):
        """Test le rejet d'une API Key invalide."""
        result = auth_manager._check_api_key("invalid-key")
        
        assert result is None
    
    def test_jwt_generation(self, auth_manager):
        """Test la génération d'un JWT."""
        token_response = auth_manager.generate_jwt_token(
            name="Test User",
            role="ADMIN",
            max_results=1000,
            expiration_hours=1
        )
        
        assert "access_token" in token_response
        assert token_response["token_type"] == "bearer"
        assert token_response["expires_in"] == 3600
        assert token_response["auth_method"] == "jwt"
    
    def test_role_limits(self, auth_manager):
        """Test les limites de résultats par rôle."""
        limits = {
            "BASIC": 50,
            "ANALYST": 200,
            "WINDY": 200,
            "ADMIN": 1000
        }
        
        for role, expected_limit in limits.items():
            actual_limit = auth_manager._get_max_results_for_role(role)
            assert actual_limit == expected_limit


class TestCertificateValidator:
    """Tests du validateur de certificats."""
    
    @pytest.fixture
    def validator(self):
        """Crée un validateur pour les tests."""
        return CertificateValidator(ca_cert_path=None)
    
    def test_validator_initialization(self, validator):
        """Test l'initialisation du validateur."""
        assert validator is not None
        assert validator.ca_cert is None
    
    def test_extract_role_from_cn(self, validator):
        """Test l'extraction du rôle depuis le CN."""
        # Mock d'un certificat avec CN
        class MockCert:
            class MockSubject:
                def get_attributes_for_oid(self, oid):
                    class MockAttr:
                        value = "client-test-ADMIN"
                    return [MockAttr()]
            
            subject = MockSubject()
        
        cert = MockCert()
        role = validator._extract_role_from_cert(cert)
        
        assert role == "ADMIN"
    
    def test_extract_invalid_role(self, validator):
        """Test l'extraction d'un rôle invalide."""
        class MockCert:
            class MockSubject:
                def get_attributes_for_oid(self, oid):
                    class MockAttr:
                        value = "client-test-INVALID"
                    return [MockAttr()]
            
            subject = MockSubject()
        
        cert = MockCert()
        role = validator._extract_role_from_cert(cert)
        
        # Doit retourner le rôle par défaut
        assert role == "BASIC"


class TestIntegration:
    """Tests d'intégration."""
    
    def test_authentication_priority(self):
        """Test la priorité d'authentification : Cert > JWT > API Key."""
        # Ce test vérifie que la priorité est bien respectée
        # (Doit être testé avec une requête HTTP réelle)
        pass
    
    def test_error_handling(self):
        """Test la gestion des erreurs."""
        auth_manager = HybridAuthManager(
            jwt_secret="test",
            jwt_algorithm="HS256",
            valid_api_keys={}
        )
        
        # Tester avec une clé invalide
        result = auth_manager._check_api_key("non-existent")
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
