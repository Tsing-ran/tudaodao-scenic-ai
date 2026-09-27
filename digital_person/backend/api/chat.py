import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.rag.pipeline import answer, answer_stream

router = APIRouter(prefix="/chat", tags=["chat"])


class Situation(BaseModel):
    """游客自身情况标签（与 group_type 正交）。默认值=中性，与前端 SIT_DEFAULTS 一致；
    全默认时不改变 prompt、缓存键与现状逐字节一致（零准确率影响）。"""
    age: str = "youth"          # teen / youth / middle / elder
    pace: str = "day"           # half / day / deep
    mobility: str = "normal"    # stroller / wheelchair / normal / hiker
    purpose: str = "relax"      # photo / kids_fun / pray / relax / study
    first_time: str = "first"   # first / return


class ChatRequest(BaseModel):
    session_id: str = "anonymous"
    message: str
    scenic_id: str = "lingshan"
    history: list[dict] = []
    stream: bool = False
    fast: bool = False      # True → qwen-turbo，首 token 更快
    lang: str = "auto"      # auto=跟随提问语言；或 en/ja/ko/fr… 强制指定
    group_type: str = "adult"  # 同行关系，切换叙事人格：adult/family_kids/senior/couple
    situation: Situation | None = None  # 自身情况标签（年龄/节奏/出行/目的/初访），按非默认值调讲解
    interests: list[str] = []  # 静态兴趣（开场快选）；仅入游中画像，不直接进 qa prompt


class ChatResponse(BaseModel):
    reply: str
    emotion: str            # happy / excited / neutral / curious / empathetic / apologetic
    sources: list[str]
    context_used: bool
    intent: str = "qa"      # qa / navigation / recommend / empathy / chitchat（Orchestrator 分派结果）
    from_cache: bool = False


@router.post("", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    if req.stream:
        async def event_stream():
            """
            标准 SSE 格式，带命名事件类型，供数字人驱动端订阅：

              event: intent
              data: {"type":"intent","value":"navigation","label":"路线规划"}

              event: emotion
              data: {"type":"emotion","value":"happy"}

              event: sentence
              data: {"type":"sentence","text":"你好！欢迎来到灵山胜境～","index":0}

              event: end
              data: {"type":"end","full_text":"..."}

            事件顺序：intent（最早，LLM 调用前）→ emotion（首 token 后）→ sentence… → end
            intent 为 Orchestrator 分派结果，前端可用于展示"当前意图"或忽略。

            前端示例（JS）：
              const es = new EventSource('/chat?stream=1')
              es.addEventListener('intent',   e => showIntent(JSON.parse(e.data).label))
              es.addEventListener('emotion',  e => setExpression(JSON.parse(e.data).value))
              es.addEventListener('sentence', e => sendToTTS(JSON.parse(e.data).text))
              es.addEventListener('end',      e => es.close())
            """
            async for event in answer_stream(
                req.message, req.scenic_id, req.history, req.session_id,
                req.fast, req.lang, req.group_type, situation=req.situation,
                interests=req.interests,
            ):
                event_type = event["type"]
                data = json.dumps(event, ensure_ascii=False)
                yield f"event: {event_type}\ndata: {data}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    result = answer(
        req.message, req.scenic_id, req.history, req.session_id,
        req.fast, req.lang, req.group_type, situation=req.situation,
        interests=req.interests,
    )
    return ChatResponse(**result)
