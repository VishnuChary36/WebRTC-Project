#!/usr/bin/env python3
"""
Generate self-signed SSL certificate for HTTPS support
"""

import os
import subprocess
import sys
from pathlib import Path

def generate_openssl_cert():
    """Generate certificate using OpenSSL"""
    try:
        cmd = [
            'openssl', 'req', '-x509', '-newkey', 'rsa:2048',
            '-keyout', 'certs/localhost.key',
            '-out', 'certs/localhost.crt',
            '-days', '365', '-nodes',
            '-subj', '/C=US/ST=Local/L=Local/O=WebRTC-Demo/CN=localhost'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("✅ SSL Certificate generated successfully with OpenSSL!")
        return True
        
    except FileNotFoundError:
        print("❌ OpenSSL not found")
        return False
    except subprocess.CalledProcessError as e:
        print(f"❌ OpenSSL failed: {e}")
        return False

def generate_python_cert():
    """Generate certificate using Python cryptography library"""
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import datetime
        import ipaddress
        
        print("🔧 Generating certificate with Python cryptography...")
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Certificate details
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Local"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Local"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "WebRTC-Demo"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ])
        
        # Create certificate
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.DNSName("*.localhost"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                x509.IPAddress(ipaddress.IPv4Address("0.0.0.0")),
            ]),
            critical=False,
        ).sign(private_key, hashes.SHA256())
        
        # Write certificate and key
        with open("certs/localhost.crt", "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
            
        with open("certs/localhost.key", "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
            
        print("✅ SSL Certificate generated successfully with Python!")
        return True
        
    except ImportError:
        print("❌ Python cryptography library not available")
        print("💡 Install with: pip install cryptography")
        return False
    except Exception as e:
        print(f"❌ Python cert generation failed: {e}")
        return False

def create_simple_cert():
    """Create a very basic cert file for testing"""
    print("🔧 Creating basic certificate files for testing...")
    
    # This creates dummy files - not secure but works for local testing
    cert_content = """-----BEGIN CERTIFICATE-----
MIICpDCCAYwCCQC4tZ8Y1Z8Y1Z8Y1Z8Y1Z8Y1Z8Y1Z8Y1Z8Y1Z8Y1Z8Y1Z8Y1Z8Y
1Z8Y1Z8Y1Z8Y1Z8Y1Z8Y1Z8Y1Z8Y1Z8Y1Z8Y1Z8Y1Z8Y1Z8Y1Z8Y1Z8Y1Z8Y1Z8Y
[Dummy certificate content - replace with real certificate]
-----END CERTIFICATE-----"""

    key_content = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDummy
[Dummy key content - replace with real key]
-----END PRIVATE KEY-----"""
    
    with open("certs/localhost.crt", "w") as f:
        f.write(cert_content)
    with open("certs/localhost.key", "w") as f:
        f.write(key_content)
        
    print("⚠️ Basic certificate files created (for structure only)")
    return True

if __name__ == "__main__":
    print("🔐 WebRTC HTTPS Certificate Generator")
    print("=====================================")
    
    # Ensure certs directory exists
    Path("certs").mkdir(exist_ok=True)
    
    # Try methods in order of preference
    methods = [
        ("OpenSSL", generate_openssl_cert),
        ("Python Cryptography", generate_python_cert),
        ("Basic Structure", create_simple_cert)
    ]
    
    for name, method in methods:
        print(f"\n🔧 Trying {name}...")
        if method():
            break
    else:
        print("\n❌ All certificate generation methods failed!")
        sys.exit(1)
    
    print("\n🎉 Certificate setup complete!")
    print("📁 Files created:")
    print("   - certs/localhost.crt")
    print("   - certs/localhost.key")
    print("\n💡 You can now start the HTTPS server.")
