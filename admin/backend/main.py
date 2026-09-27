"""
Production entry point for AutoDL deployment.
Serves the built frontend SPA + proxies /cloud/* to the RAG service.
No business routers needed — admin panel is purely frontend.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, Response, StreamingResponse
import httpx
import os

app = FastAPI(title="Digital Human Admin", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

from routers.auth_router       import router as auth_router
from routers.knowledge_router  import router as knowledge_router
from routers.admin_chat_router import router as admin_chat_router
from routers.image_router      import router as image_router
from routers.avatar_router     import router as avatar_router
from routers.tts_router        import router as tts_router
app.include_router(auth_router)
app.include_router(knowledge_router)
app.include_router(admin_chat_router)
app.include_router(image_router)
app.include_router(avatar_router)
app.include_router(tts_router)

_PROXY_SKIP_HEADERS = {"host", "connection", "transfer-encoding", "content-length"}

# /cloud/* → transparent proxy to RAG service
_RAG_BASE = "http://127.0.0.1:6006/rag"

@app.api_route("/cloud/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def cloud_proxy(path: str, request: Request):
    target = f"{_RAG_BASE}/{path}"
    if request.url.query:
        target += f"?{request.url.query}"
    body = await request.body()
    fwd_headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in _PROXY_SKIP_HEADERS
    }
    if request.headers.get("accept") == "text/event-stream" or "stream" in path:
        async def _stream():
            async with httpx.AsyncClient(verify=False, timeout=None) as c:
                async with c.stream(
                    request.method, target, content=body, headers=fwd_headers
                ) as r:
                    async for chunk in r.aiter_bytes():
                        yield chunk
        return StreamingResponse(
            _stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    async with httpx.AsyncClient(verify=False, timeout=30) as c:
        r = await c.request(request.method, target, content=body, headers=fwd_headers)
    return Response(
        content=r.content,
        status_code=r.status_code,
        media_type=r.headers.get("content-type", "application/json"),
    )

# Static file serving
_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
_dist = os.path.abspath(_dist)

if os.path.isdir(_dist):
    _assets = os.path.join(_dist, "assets")
    if os.path.isdir(_assets):
        app.mount("/assets", StaticFiles(directory=_assets), name="assets")
    _live2d = os.path.join(_dist, "live2d")
    if os.path.isdir(_live2d):
        app.mount("/live2d", StaticFiles(directory=_live2d), name="live2d")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        # /admin/* → admin SPA
        if full_path.startswith("admin"):
            admin_html = os.path.join(_dist, "admin", "index.html")
            if os.path.isfile(admin_html):
                return FileResponse(admin_html)
        # Direct file (favicon, etc.)
        candidate = os.path.join(_dist, full_path)
        if os.path.isfile(candidate):
            return FileResponse(candidate)
        # Fallback → tourist SPA (no longer built; admin-only deployment)
        tourist_html = os.path.join(_dist, "index.html")
        if os.path.isfile(tourist_html):
            return FileResponse(tourist_html)
        return RedirectResponse("/admin/")
