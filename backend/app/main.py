from fastapi import FastAPI
from routers import pvcs, autoscaler, system

app = FastAPI()

app.include_router(pvcs.router)
app.include_router(autoscaler.router)
app.include_router(system.router)
