from fastapi import HTTPException, status
from fastapi.security import HTTPBasicCredentials
import bcrypt
import secrets
import os

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password verification failed: {str(e)}"
        )

def verify_admin(credentials: HTTPBasicCredentials) -> bool:
    # Verify username (constant-time comparison)
    username_ok = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    
    # Verify password
    password_ok = verify_password(credentials.password, ADMIN_PASSWORD_HASH)
    
    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True