from fastapi import FastAPI
from app.api.forecast import router as forecast_router

app = FastAPI(
    title="Transit AI System",
    version="1.0.0"
)

app.include_router(
    forecast_router,
    prefix="/forecast",
    tags=["Forecast"]
)

@app.get("/")
def root():
    return {"message": "Transit AI Backend Running"}

@app.get("/health")
def health():
    return {"status": "healthy"}