import hashlib
import hmac
import os

SALT = os.getenv("ANONYMIZATION_SALT", "dpdp-salt-2024")

def hash_id(value: str, tenant_id: str) -> str:
    """
    Generates an HMAC-SHA256 token for a given string value to pseudonymize 
    identifiers while keeping them joinable across the system.
    
    Evidence: NIST SP 800-107 Section 5.3 — keyed hash for pseudonymization 
    of identifiers that must remain joinable.
    
    Gate 1/2: Applied to identifiers passing the necessity gates that are 
    transformed to prevent direct identification while maintaining referential integrity.
    
    Args:
        value (str): The raw identifier to be hashed.
        tenant_id (str): The tenant ID used as part of the key for tenant isolation.
        
    Returns:
        str: A 12-character hex digest matching the database schema's character(12) requirement.
    """
    key = f"{SALT}:{tenant_id}".encode()
    msg = str(value).encode()
    return hmac.new(key, msg, hashlib.sha256).hexdigest()[:12]
