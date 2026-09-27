import os
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
for _var in ("ALL_PROXY", "all_proxy", "HTTPS_PROXY", "https_proxy",
             "HTTP_PROXY", "http_proxy"):
    os.environ.pop(_var, None)

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.api.chat import router as chat_router
from backend.api.knowledge import router as kb_router
from backend.api.kb_manage import router as kb_manage_router
from backend.api.kb_selftest import router as kb_selftest_router
from backend.api.analytics import router as analytics_router
from backend.api.analytics_bi import router as analytics_bi_router
from backend.api.multimodal import router as mm_router
from backend.api.checkin import router as checkin_router
from backend.api.recommend import router as recommend_router
from backend.api.digital_human import router as dh_router
from backend.api.asr import router as asr_router
from backend.api.trip import router as trip_router
from backend.api.tour import router as tour_router
from backend.api.theme import router as theme_router
from backend.api.handoff import router as handoff_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 初始化 SQLite（建表，幂等）
    from backend.db.database import init_db
    init_db()

    from backend.core.config import settings
    if settings.deploy_mode == "local":
        print("预热嵌入模型（BGE-M3）...")
        from backend.rag.embedder import get_embedder
        get_embedder()
        print("预热重排模型（BGE-Reranker）...")
        from backend.rag.retriever import get_reranker
        get_reranker()
        print("本地模型预热完成，服务就绪")
    else:
        print("云端模式（DashScope），服务就绪")

    # 后台预热客流统计：读 14 万行 xlsx 约 10~20s（openpyxl 慢），
    # 不预热的话首个 navigation/recommend 请求会被这次冷加载冻住整整 20s。
    # 放后台线程，不阻塞启动，等首个用户提问时缓存已热。
    import threading
    def _prewarm_crowd():
        try:
            from backend.analytics.crowd import _stats
            _stats()
            print("客流统计预热完成")
        except Exception as e:  # 缺 xlsx/pandas 不致命，导游不带客流上下文即可
            print(f"客流统计预热跳过: {type(e).__name__}: {e}")
    threading.Thread(target=_prewarm_crowd, daemon=True).start()
    yield


app = FastAPI(title="景区导览AI数字人", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(mm_router)
app.include_router(checkin_router)
app.include_router(recommend_router)
# 注意注册顺序：kb_manage/kb_selftest 的字面路径（/kb/retrieval-config、/kb/self-test 等）
# 必须先于 kb_router 的通配 DELETE /kb/{scenic_id}，否则会被当成景区名误删知识库
app.include_router(kb_manage_router)
app.include_router(kb_selftest_router)
app.include_router(kb_router)
app.include_router(analytics_router)
app.include_router(analytics_bi_router)
app.include_router(dh_router)
app.include_router(asr_router)
app.include_router(trip_router)
app.include_router(tour_router)
app.include_router(theme_router)
app.include_router(handoff_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/test", include_in_schema=False)
def test_ui():
    """后端托管测试面板（PC 版），避免 file:// 跨域问题。"""
    p = Path(__file__).resolve().parent.parent / "test_ui.html"
    return FileResponse(p, media_type="text/html")


@app.get("/m", include_in_schema=False)
def mobile_ui():
    """移动优先的后端功能测试台（手机浏览器访问 /m）。"""
    p = Path(__file__).resolve().parent.parent / "test_mobile.html"
    return FileResponse(p, media_type="text/html")


@app.get("/talk", include_in_schema=False)
def talk_ui():
    """数字人交互页（WebRTC 数字人 + 问答走桥接 → 端到端语音问答演示）。"""
    p = Path(__file__).resolve().parent.parent / "talk.html"
    return FileResponse(p, media_type="text/html")


@app.get("/app", include_in_schema=False)
def guest_app():
    """游客端正式 UI（东方禅意主题）：全屏数字人 + 多模态(语音/拍照/文字) +
    主动迎宾 + 同行人格切换 + 个性化推荐 + 行程游记。赛题「游客交互端」交付页。"""
    p = Path(__file__).resolve().parent.parent / "app.html"
    return FileResponse(p, media_type="text/html")


@app.get("/dashboard", include_in_schema=False)
def dashboard_ui():
    """运营数据大屏（ECharts 可视化 analytics + 实时客流热度）。"""
    p = Path(__file__).resolve().parent.parent / "dashboard.html"
    return FileResponse(p, media_type="text/html")


@app.get("/echarts.min.js", include_in_schema=False)
def echarts_js():
    """本地服 ECharts（绕开浏览器代理对 CDN 的拦截）。"""
    p = Path(__file__).resolve().parent.parent / "echarts.min.js"
    return FileResponse(p, media_type="application/javascript")
