import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s | %(message)s")

app = FastAPI(
    title="CIMET QA Gate",
    description="No sale ships unscored. Every score resolves to a transcript line, "
                "an audio timestamp and the check version live on the call date.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)
app.include_router(api_router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {
        "status": "ok",
        "llm_enabled": settings.llm_available,
        "model": settings.openrouter_model if settings.llm_available else None,
        "confidence_threshold": settings.confidence_threshold,
        "human_sample_rate": settings.human_sample_rate,
    }
