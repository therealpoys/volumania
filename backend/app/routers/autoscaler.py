from fastapi import APIRouter, Depends
import auth
from services import k8s_service


router = APIRouter()

@router.get("/autoscalers")
def get_autoscalers(token: str = Depends(auth.verify_token)):
    return k8s_service.list_autoscalers(token)

@router.post("/autoscalers")
def create_autoscaler(
    namespace: str,
    pvcName: str,
    stepSize: str,
    maxSize: str,
    threshold: int,
    cooldown: int,
    token: str = Depends(auth.verify_token)
):
    return k8s_service.create_autoscaler(
        token, namespace, pvcName, stepSize, maxSize, threshold, cooldown
    )

@router.put("/autoscalers/{name}")
def update_autoscaler(
    name: str,
    namespace: str,
    stepSize: str,
    maxSize: str,
    threshold: int,
    cooldown: int,
    token: str = Depends(auth.verify_token)
):
    return k8s_service.update_autoscaler(
        token, name, namespace, stepSize, maxSize, threshold, cooldown
    )

@router.delete("/autoscalers/{name}")
def delete_autoscaler(
    name: str,
    namespace: str,
    token: str = Depends(auth.verify_token)
):
    return k8s_service.delete_autoscaler(token, name, namespace)
