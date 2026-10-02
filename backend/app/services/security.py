import hashlib
import secrets
from typing import Optional

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000
    )
    return f"{salt}${key.hex()}"


def verify_password(stored_hash: Optional[str], provided_password: str) -> bool:
    if not stored_hash or "$" not in stored_hash:
        return False
    try:
        salt, expected_key = stored_hash.split("$", 1)
        calculated_key = hashlib.pbkdf2_hmac(
            "sha256",
            provided_password.encode("utf-8"),
            salt.encode("utf-8"),
            100000
        )
        return secrets.compare_digest(calculated_key.hex(), expected_key)
    except Exception:
        return False
