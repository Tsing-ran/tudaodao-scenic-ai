"""
阿里云虚拟数字人开放平台（DVH）服务
接口文档：https://help.aliyun.com/zh/avatar/
Endpoint: avatar.cn-zhangjiakou.aliyuncs.com
"""
import uuid
from alibabacloud_avatar20220130.client import Client
from alibabacloud_avatar20220130 import models as avatar_models
from alibabacloud_tea_openapi import models as open_api_models
from config import settings


def _build_client() -> Client:
    config = open_api_models.Config(
        access_key_id=settings.ALIYUN_ACCESS_KEY_ID,
        access_key_secret=settings.ALIYUN_ACCESS_KEY_SECRET,
        endpoint=settings.AVATAR_ENDPOINT,
    )
    return Client(config)


def start_avatar_session(user_id: str = None) -> dict:
    """
    启动数字人实时流媒体实例（StartInstance）
    返回 session_id 和前端渲染所需的 channel 凭证

    Returns:
        {
            "session_id": "...",
            "channel_token": "...",
            "channel_type": "RTC",
            "app_id": "...",
            "user_id": "...",
            "nonce": "...",
            "timestamp": "...",
        }
    """
    client = _build_client()
    uid = user_id or f"tourist_{uuid.uuid4().hex[:8]}"

    request = avatar_models.StartInstanceRequest(
        app=avatar_models.StartInstanceRequestApp(
            app_id=settings.AVATAR_APP_ID,
            tenant_id=int(settings.AVATAR_TENANT_ID),
        ),
        user=avatar_models.StartInstanceRequestUser(
            user_id=uid,
            user_name=uid,
        ),
        channel=avatar_models.StartInstanceRequestChannel(
            type="RTC",
        ),
    )

    response = client.start_instance(request)
    data = response.body.data

    return {
        "session_id": data.session_id,
        "channel_token": data.channel.channel_token,
        "channel_type": data.channel.type,
        "app_id": data.channel.app_id,
        "user_id": data.channel.user_id,
        "nonce": data.channel.nonce,
        "timestamp": str(data.channel.timestamp),
    }


def send_text_to_avatar(session_id: str, text: str) -> bool:
    """
    向数字人发送文本，驱动数字人播报（SendText）

    Args:
        session_id: 会话ID
        text: 要播报的文本内容
    """
    client = _build_client()

    request = avatar_models.SendTextRequest(
        session_id=session_id,
        text=avatar_models.SendTextRequestText(
            content=text,
            content_type="TEXT",
        ),
    )

    response = client.send_text(request)
    return response.body.success


def stop_avatar_session(session_id: str) -> bool:
    """
    停止数字人会话（StopInstance）
    """
    client = _build_client()

    request = avatar_models.StopInstanceRequest(
        session_id=session_id,
    )

    response = client.stop_instance(request)
    return response.body.success


def query_avatar_list() -> list:
    """
    查询账号下可用的数字人形象列表（QueryAvatarList）
    用于管理端选择形象
    """
    client = _build_client()

    request = avatar_models.QueryAvatarListRequest(
        tenant_id=int(settings.AVATAR_TENANT_ID),
    )

    response = client.query_avatar_list(request)
    avatars = []
    if response.body.data and response.body.data.avatar_list:
        for a in response.body.data.avatar_list:
            avatars.append({
                "avatar_id": a.avatar_id,
                "avatar_name": a.avatar_name,
                "avatar_type": a.avatar_type,
                "cover_url": a.cover_url,
                "status": a.status,
            })
    return avatars


def submit_text_to_video(avatar_id: str, text: str, title: str = "景区导览视频") -> dict:
    """
    离线文字转数字人视频（SubmitTextTo2DAvatarVideoTask）
    用于提前生成固定讲解视频

    Returns:
        {"task_id": "..."}
    """
    client = _build_client()

    request = avatar_models.SubmitTextTo2DAvatarVideoTaskRequest(
        tenant_id=int(settings.AVATAR_TENANT_ID),
        avatar_id=avatar_id,
        title=title,
        text=avatar_models.SubmitTextTo2DAvatarVideoTaskRequestText(
            content=text,
        ),
    )

    response = client.submit_text_to_2_davatar_video_task(request)
    return {"task_id": response.body.data.task_id}


def get_video_task_info(task_id: str) -> dict:
    """
    查询视频合成任务状态（GetVideoTaskInfo）
    """
    client = _build_client()

    request = avatar_models.GetVideoTaskInfoRequest(
        task_uuid=task_id,
        tenant_id=int(settings.AVATAR_TENANT_ID),
    )

    response = client.get_video_task_info(request)
    data = response.body.data
    return {
        "task_id": task_id,
        "status": data.status,
        "video_url": data.video_url if hasattr(data, "video_url") else None,
        "duration": data.duration if hasattr(data, "duration") else None,
    }
