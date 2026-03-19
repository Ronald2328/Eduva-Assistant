import os.path as _osp
from functools import lru_cache
from pathlib import Path
from types import CodeType

import aiofiles
import logfire
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from scalar_fastapi import get_scalar_api_reference  # type: ignore

from app.core.config import Environment, settings
from app.lifespan import lifespan
from app.router import router as api_router


# In Python 3.13, Path.absolute() always calls os.getcwd(), even for already-
# absolute paths.  Logfire's is_user_code() calls Path(co_filename).absolute()
# on every span/log call, which LangGraph's blocking-call detector intercepts
# and raises an exception.  We replace is_user_code with a version that avoids
# os.getcwd() entirely: co_filename is always absolute for real on-disk files.
def _patch_logfire_is_user_code() -> None:
    try:
        from logfire._internal import stack_info as _si

        _cwd = str(Path(".").resolve())  # same as logfire's _CWD, computed in sync ctx
        _prefixes = _si.NON_USER_CODE_PREFIXES

        @lru_cache(maxsize=8192)
        def _is_user_code(code: CodeType) -> bool:
            filename = code.co_filename
            if not _osp.isabs(filename):
                filename = _osp.normpath(_osp.join(_cwd, filename))
            return not (
                filename.startswith(_prefixes)
                or code.co_filename.startswith("<")
                or code.co_name in ("<listcomp>", "<dictcomp>", "<setcomp>")
            )

        _si.is_user_code = _is_user_code  # type: ignore[attr-defined]
    except Exception:
        pass


_patch_logfire_is_user_code()

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
    async with aiofiles.open(BASE_DIR / "static" / "upload.html") as f:
        return await f.read()

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
