from fastapi import FastAPI, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from . import k8s, auth

app = FastAPI()
security = HTTPBearer()

@app.post("/login")
def login(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Login endpoint.
    Accepts a Kubernetes token via HTTP Bearer and returns a JWT.
    """
    token = credentials.credentials
    return auth.create_token(token)

@app.get("/pvcs")
def get_pvcs(token: str = Depends(auth.verify_token)):
    """
    Lists PVCs accessible to the user represented by the token.
    """
    return k8s.get_user_pvcs(token)

@app.post("/manualresize")
def manual_resize(
    namespace: str,
    pvc_name: str,
    new_size: str,
    token: str = Depends(auth.verify_token)
):
    """
    Manually patches the size of a PVC using the user's token.
    """
    k8s.patch_user_pvc_size(token, namespace, pvc_name, new_size)
    return {"status": "success", "message": f"{pvc_name} resized to {new_size}"}
