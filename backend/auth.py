import bcrypt
import logging
import os
import secrets
from datetime import datetime, timedelta
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

# Prefer JWT_SECRET_KEY from the environment (backend/.env). If it is not
# configured, generate an ephemeral random key so the application still
# starts; tokens are then invalidated on restart. Never ship a hardcoded
# production secret.
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)
    logger.warning(
        "JWT_SECRET_KEY not set — using a temporary random signing key. "
        "Sessions will be invalidated on restart. Set JWT_SECRET_KEY in backend/.env."
    )
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
