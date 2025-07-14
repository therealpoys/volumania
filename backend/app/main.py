from fastapi import FastAPI
from app.routers import autoscaler, system
from app.routers import pvc

app = FastAPI()

app.include_router(pvc.router)
app.include_router(autoscaler.router)
app.include_router(system.router)
