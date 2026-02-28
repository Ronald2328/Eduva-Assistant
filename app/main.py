from pathlib import Path

import logfire
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from scalar_fastapi import get_scalar_api_reference  # type: ignore

from app.core.config import Environment, settings
from app.lifespan import lifespan
from app.router import router as api_router

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)

app.include_router(router=api_router)

# Serve admin UI
@app.get("/admin/upload", response_class=HTMLResponse, include_in_schema=False)
async def admin_upload_ui():
    """Serve admin document upload UI."""
    with open(BASE_DIR / "static" / "upload.html") as f:
        return f.read()

if settings.ENVIRONMENT == Environment.DEV:

    @app.get(path="/docs", include_in_schema=False)
    async def scalar_api_reference() -> HTMLResponse:
        if app.openapi_url is None:
            raise RuntimeError("OpenAPI URL is not set")

        return get_scalar_api_reference(
            openapi_url=app.openapi_url,
            title=app.title,
        )


@app.get(path="/ready")
async def readiness_check():
    """Readiness check endpoint."""
    return {
        "status": "ok",
    }


if settings.LOGFIRE_TOKEN:
    try:
        logfire.configure(
            service_name=settings.APP_NAME,
            environment=settings.ENVIRONMENT.value,
            token=settings.LOGFIRE_TOKEN,
        )

        logfire.instrument_fastapi(app)
        logfire.instrument_openai()

    except Exception as e:
        print(f"\nLogfire error: {e}\nContinuing without monitoring...\n")
else:
    print("\nLogfire not configured (add token to .env if you want monitoring)\n")
