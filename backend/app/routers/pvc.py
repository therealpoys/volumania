from fastapi import APIRouter, Depends
from app import auth
from app.services import k8s_service

router = APIRouter()

@router.get("/pvcs")
def get_pvcs(token: str = Depends(auth.verify_token)):
    return k8s_service.get_all_pvcs(token)

@router.get("/pvcs/usage")
def get_pvc_usages(token: str = Depends(auth.verify_token)):
    return k8s_service.get_all_pvc_usages(token)

@router.post("/manualresize")
def manual_resize(namespace: str, pvc_name: str, new_size: str, token: str = Depends(auth.verify_token)):
    k8s_service.manual_resize(token, namespace, pvc_name, new_size)
    return {"status": "success", "message": f"{pvc_name} resized to {new_size}"}
