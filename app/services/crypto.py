import base64
import hashlib
from cryptography.fernet import Fernet
from flask import current_app


def get_fernet():
    """Get Fernet instance using app's SECRET_KEY."""
    key = current_app.config['SECRET_KEY'].encode('utf-8')
    # Derive a 32-byte key from SECRET_KEY using SHA256
    derived_key = hashlib.sha256(key).digest()
    fernet_key = base64.urlsafe_b64encode(derived_key)
    return Fernet(fernet_key)


def encrypt_data(data: str) -> str:
    """Encrypt string data and return base64 encoded result."""
    fernet = get_fernet()
    encrypted = fernet.encrypt(data.encode('utf-8'))
    return base64.urlsafe_b64encode(encrypted).decode('utf-8')


def decrypt_data(encrypted_data: str) -> str:
    """Decrypt base64 encoded encrypted data."""
    fernet = get_fernet()
    decoded = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
    decrypted = fernet.decrypt(decoded)
    return decrypted.decode('utf-8')
