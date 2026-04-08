from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router


app = FastAPI(title="Contract Review Agent MVP", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)

repo_root = Path(__file__).resolve().parent.parent
frontend_dist_dir = repo_root / "frontend" / "dist"
frontend_assets_dir = frontend_dist_dir / "assets"
uploads_dir = repo_root / "uploads"
uploads_dir.mkdir(parents=True, exist_ok=True)

if frontend_assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=frontend_assets_dir), name="frontend-assets")

app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")


@app.get("/", include_in_schema=False, response_model=None)
def demo_page() -> FileResponse | HTMLResponse:
    index_file = frontend_dist_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)

    return HTMLResponse(
        """
        <!doctype html>
        <html lang="zh-CN">
          <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>AI 合同校审工作台</title>
            <style>
              body { font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif; margin: 0; background: #eef4fb; color: #10233f; }
              main { max-width: 760px; margin: 72px auto; padding: 32px; border-radius: 24px; background: white; box-shadow: 0 24px 60px rgba(15, 23, 42, 0.12); }
              h1 { margin: 0 0 12px; }
              code { padding: 2px 6px; border-radius: 8px; background: #eff6ff; }
            </style>
          </head>
          <body>
            <main id="root">
              <h1>AI 合同校审工作台</h1>
              <p>新的 React 前端工程已经创建在 <code>frontend/</code> 目录下。</p>
              <p>开发模式请运行 <code>cd frontend && npm install && npm run dev</code>，生产模式请先执行 <code>npm run build</code> 后再访问本页。</p>
            </main>
          </body>
        </html>
        """
    )
