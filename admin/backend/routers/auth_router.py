from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
import hashlib, secrets, json, time, re
from pathlib import Path
from typing import Optional

router = APIRouter(prefix="/api/auth", tags=["auth"])

USERS_FILE = Path(__file__).parent.parent / "data" / "users.json"
SESSIONS: dict[str, str] = {}  # session_token → username（内存存储，重启后清空）

_PHONE_RE = re.compile(r"^1[3-9]\d{9}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _load_users() -> dict:
    if not USERS_FILE.exists():
        USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        USERS_FILE.write_text("{}")
    return json.loads(USERS_FILE.read_text(encoding="utf-8"))


def _save_users(users: dict):
    USERS_FILE.write_text(
        json.dumps(users, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _get_user(users: dict, username: str) -> dict | None:
    val = users.get(username)
    if val is None:
        return None
    # 兼容旧格式（值为字符串密码哈希）
    if isinstance(val, str):
        return {"password": val, "scene_type": "historical"}
    return val


def _public(username: str, user: dict) -> dict:
    """返回给前端的安全用户信息（不含密码哈希）。"""
    return {
        "username":       username,
        "scene_type":     user.get("scene_type", "historical"),
        "scenic_spot_id": user.get("scenic_spot_id"),
        "real_name":      user.get("real_name", ""),
        "phone":          user.get("phone", ""),
        "email":          user.get("email", ""),
        "department":     user.get("department", ""),
        "position":       user.get("position", ""),
    }


class AuthBody(BaseModel):
    username: str
    password: str
    scene_type: Optional[str] = "historical"
    scenic_spot_id: Optional[str] = None
    # 管理人员信息（注册时采集，便于景区协同管理）
    real_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None


@router.post("/register")
def register(body: AuthBody, response: Response):
    users = _load_users()
    if body.username in users:
        raise HTTPException(status_code=409, detail="用户名已被注册")

    real_name = (body.real_name or "").strip()
    phone     = (body.phone or "").strip()
    email     = (body.email or "").strip()
    # 服务端二次校验（防绕过前端直接调用）
    if not real_name:
        raise HTTPException(status_code=400, detail="请填写真实姓名")
    if not _PHONE_RE.match(phone):
        raise HTTPException(status_code=400, detail="请输入正确的 11 位手机号")
    if email and not _EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")
    if not (body.department or "").strip():
        raise HTTPException(status_code=400, detail="请选择所属部门")

    users[body.username] = {
        "password":       _hash_pw(body.password),
        "scene_type":     body.scene_type or "historical",
        "scenic_spot_id": body.scenic_spot_id,
        "real_name":      real_name,
        "phone":          phone,
        "email":          email,
        "department":     (body.department or "").strip(),
        "position":       (body.position or "").strip(),
        "created_at":     int(time.time()),
    }
    _save_users(users)
    token = secrets.token_hex(32)
    SESSIONS[token] = body.username
    response.set_cookie("session", token, httponly=True, samesite="lax", max_age=86400 * 7)
    return _public(body.username, users[body.username])


@router.post("/login")
def login(body: AuthBody, response: Response):
    users = _load_users()
    user = _get_user(users, body.username)
    if not user or user["password"] != _hash_pw(body.password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = secrets.token_hex(32)
    SESSIONS[token] = body.username
    response.set_cookie("session", token, httponly=True, samesite="lax", max_age=86400 * 7)
    return _public(body.username, user)


@router.get("/me")
def me(request: Request):
    token = request.cookies.get("session")
    username = SESSIONS.get(token) if token else None
    if not username:
        raise HTTPException(status_code=401, detail="未登录")
    users = _load_users()
    user = _get_user(users, username)
    if not user:
        raise HTTPException(status_code=401, detail="未登录")
    return _public(username, user)


@router.post("/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get("session")
    if token:
        SESSIONS.pop(token, None)
    response.delete_cookie("session")
    return {"ok": True}
