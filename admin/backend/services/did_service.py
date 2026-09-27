"""
D-ID Streaming API 服务
官网：https://www.d-id.com  文档：https://docs.d-id.com
免费账号有约 20 credits（≈ 5 分钟视频），够比赛演示用
"""
import base64
import httpx
from config import settings

BASE_URL = "https://api.d-id.com"


def _headers() -> dict:
    # D-ID 使用 Basic Auth：base64(email:api_key)
    # 免费注册后 API Key 格式类似 "Basic xxxx"，直接用即可
    return {
        "Authorization": f"Basic {settings.DID_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


async def create_stream(avatar_url: str) -> dict:
    """
    创建 D-ID 实时流会话
    返回：{ id, offer(WebRTC SDP), ice_servers, session_id }
    """
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{BASE_URL}/talks/streams",
            headers=_headers(),
            json={"source_url": avatar_url},
        )
        r.raise_for_status()
        return r.json()


async def send_sdp_answer(stream_id: str, answer: dict, session_id: str) -> dict:
    """浏览器 WebRTC Answer SDP 转发给 D-ID"""
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"{BASE_URL}/talks/streams/{stream_id}/sdp",
            headers=_headers(),
            json={"answer": answer, "session_id": session_id},
        )
        r.raise_for_status()
        return r.json()


async def send_ice_candidate(stream_id: str, candidate: dict, session_id: str) -> dict:
    """转发 ICE Candidate"""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"{BASE_URL}/talks/streams/{stream_id}/ice",
            headers=_headers(),
            json={**candidate, "session_id": session_id},
        )
        r.raise_for_status()
        return r.json()


async def send_talk(stream_id: str, text: str, session_id: str) -> dict:
    """
    向数字人发送说话内容（D-ID 内置中文 TTS）
    voice_id 使用微软 Azure 中文女声
    """
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"{BASE_URL}/talks/streams/{stream_id}",
            headers=_headers(),
            json={
                "script": {
                    "type": "text",
                    "input": text,
                    "provider": {
                        "type": "microsoft",
                        "voice_id": "zh-CN-XiaoXiaoNeural",
                    },
                },
                "session_id": session_id,
                "config": {"fluent": True, "pad_audio": 0.0},
            },
        )
        r.raise_for_status()
        return r.json()


async def upload_image(file_path: str) -> str:
    """把本地图片上传到 D-ID，返回可公开访问的 URL"""
    async with httpx.AsyncClient(timeout=30) as client:
        with open(file_path, "rb") as f:
            r = await client.post(
                f"{BASE_URL}/images",
                headers={"Authorization": f"Basic {settings.DID_API_KEY}"},
                files={"image": (file_path.split("/")[-1].split("\\")[-1], f, "image/jpeg")},
            )
        r.raise_for_status()
        return r.json()["url"]


async def list_presenters() -> list:
    """查询 D-ID 可用主播列表"""
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{BASE_URL}/presenters", headers=_headers())
        r.raise_for_status()
        return r.json().get("presenters", [])


async def close_stream(stream_id: str, session_id: str):
    """关闭流会话，释放 credits"""
    async with httpx.AsyncClient(timeout=10) as client:
        await client.delete(
            f"{BASE_URL}/talks/streams/{stream_id}",
            headers=_headers(),
            json={"session_id": session_id},
        )
