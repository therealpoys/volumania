from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta,timezone
import jwt

SECRET_KEY = "your_secret_here"
ALGORITHM = "HS256"
security = HTTPBearer()

def create_token(k8s_token: str):
    """Encodes the Kubernetes token into a JWT with expiry."""
    expire = datetime.now(timezone.utc) + timedelta(hours=1)

    payload = {
        "k8s_token": k8s_token,
        "exp": expire
    }
    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": encoded_jwt}

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Decodes the JWT and extracts the Kubernetes token."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["k8s_token"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
