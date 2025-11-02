import logfire
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from scalar_fastapi import get_scalar_api_reference  # type: ignore

from app.core.config import Environment, settings
from app.lifespan import lifespan
from app.router import router as api_router

app = FastAPI(
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)

app.include_router(router=api_router)

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
    logfire.configure(
        service_name=settings.APP_NAME,
        environment=settings.ENVIRONMENT.value,
        token=settings.LOGFIRE_TOKEN,
    )

    logfire.instrument_fastapi(app)
    logfire.instrument_httpx()
    logfire.instrument_openai()
