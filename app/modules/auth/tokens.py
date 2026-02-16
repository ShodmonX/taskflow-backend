import hashlib
import secrets

def generate_refresh_token() -> str:
    """
    Generates a secure, URL-safe refresh token.

    Returns:
        str: A randomly generated refresh token suitable for use in authentication systems.
    """
    return secrets.token_urlsafe(48)

def hash_refresh_token(token: str) -> str:
    """
    Hashes a refresh token using SHA-256.

    Args:
        token (str): The refresh token to be hashed.

    Returns:
        str: The SHA-256 hexadecimal digest of the token.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()