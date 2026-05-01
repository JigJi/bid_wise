from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1 import router as v1_router

app = FastAPI(
    title="BidWise API",
    description="Thai gov procurement vendor copilot",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5800", "http://127.0.0.1:5800"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)


@app.get("/")
def root():
    return {
        "service": "bid_wise",
        "env": settings.APP_ENV,
        "status": "ok",
        "api_docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
