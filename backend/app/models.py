from pydantic import BaseModel

class PVCUsage(BaseModel):
    namespace: str
    pvc: str
    usage_percent: float
