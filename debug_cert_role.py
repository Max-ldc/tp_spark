
import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from auth.cert_validator import CertificateValidator

def test_admin_cert():
    cert_path = "certs/clients/client-admin-cert.pem"
    if not os.path.exists(cert_path):
        print(f"File not found: {cert_path}")
        return

    validator = CertificateValidator()
    is_valid, cert_info, error = validator.validate_certificate_file(cert_path)
    
    if is_valid:
        print(f"Certification info: {cert_info}")
        print(f"Extracted Role: {cert_info.get('role')}")
        print(f"CN: {cert_info.get('cn')}")
    else:
        print(f"Validation failed: {error}")

if __name__ == "__main__":
    test_admin_cert()
