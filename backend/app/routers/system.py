from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import auth



router = APIRouter()
security = HTTPBearer()

@router.post("/login")
def login(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    return auth.create_token(token)

@router.get("/health")
def health():
    return {"status": "ok"}
