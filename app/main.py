from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router


app = FastAPI(title="Contract Review Agent MVP", version="0.1.0")
app.include_router(router)

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
def demo_page() -> FileResponse:
    return FileResponse(static_dir / "index.html")
