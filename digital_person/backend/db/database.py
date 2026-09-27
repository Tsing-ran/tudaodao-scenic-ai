"""
SQLite 会话存储。

表结构：
  conversations - 每轮问答一行，存 session_id / scenic_id / 用户问 / AI答 / 情绪 / 时间戳（服务端自动埋点）
  events        - 客户端主动上报的行为事件（画像/功能使用/到访/满意度等服务端看不到的信号）
  scenic_theme  - 景区主题色覆盖（管理端 PUT 覆盖默认；客户端切景区时套用）
"""

import datetime as _dt
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from backend.core.config import settings

DB_PATH: Path = settings.vector_store_dir.parent / "conversations.db"


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id   TEXT    NOT NULL,
                scenic_id    TEXT    NOT NULL DEFAULT 'lingshan',
                user_message TEXT    NOT NULL,
                ai_reply     TEXT    NOT NULL,
                emotion      TEXT    NOT NULL DEFAULT 'neutral',
                context_used INTEGER NOT NULL DEFAULT 1,
                created_at   TEXT    NOT NULL
                             DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_scenic_time ON conversations(scenic_id, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_session      ON conversations(session_id)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT NOT NULL,
                scenic_id   TEXT NOT NULL DEFAULT 'lingshan',
                type        TEXT NOT NULL,
                group_type  TEXT,
                lang        TEXT,
                payload     TEXT,
                created_at  TEXT NOT NULL
                            DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_evt_type_time ON events(type, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_evt_scenic    ON events(scenic_id, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_evt_session   ON events(session_id)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scenic_theme (
                scenic_id     TEXT PRIMARY KEY,
                name          TEXT,
                primary_color TEXT,
                sweet_color   TEXT,
                updated_at    TEXT NOT NULL
                              DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS digital_human_config (
                scenic_id    TEXT PRIMARY KEY,
                avatar_id    TEXT NOT NULL DEFAULT 'female_elegant',
                avatar_name  TEXT NOT NULL DEFAULT '素雅女性',
                voice_id     TEXT NOT NULL DEFAULT 'voice_gentle_f',
                voice_name   TEXT NOT NULL DEFAULT '温柔女声',
                updated_at   TEXT NOT NULL
                             DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
            )
        """)
        # 数字人场景背景（'' = 原始灰底，兼容旧库/旧行为）
        _ensure_columns(conn, "digital_human_config", {
            "background_id":   "TEXT NOT NULL DEFAULT ''",
            "background_name": "TEXT NOT NULL DEFAULT ''",
        })
        # 管理端上传的自定义背景登记（合成由本地脚本 gen_avatar_background.py sync 拉取执行）
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dh_background (
                bg_id      TEXT PRIMARY KEY,
                name       TEXT NOT NULL,
                scenic_id  TEXT,
                source     TEXT NOT NULL DEFAULT 'upload',
                status     TEXT NOT NULL DEFAULT 'pending',
                file_path  TEXT NOT NULL,
                created_at TEXT NOT NULL
                           DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
            )
        """)
        # 管理端可编辑的 FAQ 知识条目（新增/编辑即同步进 RAG 向量库，id 稳定→可增量 upsert）
        conn.execute("""
            CREATE TABLE IF NOT EXISTS faq_items (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                scenic_id  TEXT NOT NULL DEFAULT 'lingshan',
                question   TEXT NOT NULL,
                answer     TEXT NOT NULL,
                category   TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime')),
                updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime'))
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_faq_scenic ON faq_items(scenic_id)")
        # 管理端可编辑的文本段落（同样同步进 RAG）
        conn.execute("""
            CREATE TABLE IF NOT EXISTS text_items (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                scenic_id  TEXT NOT NULL DEFAULT 'lingshan',
                title      TEXT NOT NULL DEFAULT '',
                content    TEXT NOT NULL,
                category   TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime')),
                updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime'))
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_text_scenic ON text_items(scenic_id)")
        # 上传文档登记（真实记录文件名/大小/时间/状态，前端文档列表从此查，告别假文件名）
        conn.execute("""
            CREATE TABLE IF NOT EXISTS uploaded_docs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                scenic_id  TEXT NOT NULL DEFAULT 'lingshan',
                filename   TEXT NOT NULL,
                size_bytes INTEGER NOT NULL DEFAULT 0,
                chunks     INTEGER NOT NULL DEFAULT 0,
                status     TEXT NOT NULL DEFAULT 'indexed',
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime'))
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_scenic ON uploaded_docs(scenic_id)")
        # 管理端「检索设置」：按景区覆盖检索参数。无行 = 用 settings 默认值（保准确率基线）。
        conn.execute("""
            CREATE TABLE IF NOT EXISTS kb_retrieval_config (
                scenic_id  TEXT PRIMARY KEY,
                strategy   TEXT NOT NULL DEFAULT 'hybrid',
                top_k      INTEGER,
                threshold  REAL,
                updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime'))
            )
        """)
        # 扫码接力 / 同游：大屏(或手机)把"对话+个性化"打成快照存一行，另一设备扫码 claim 即带走。
        # 短时效(默认 5min)、不透明 token、过期即焚——快照本体不进 URL，只凭 token 取。
        conn.execute("""
            CREATE TABLE IF NOT EXISTS session_handoffs (
                token      TEXT PRIMARY KEY,
                scenic_id  TEXT NOT NULL DEFAULT 'lingshan',
                snapshot   TEXT NOT NULL,
                source     TEXT NOT NULL DEFAULT 'kiosk',
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime')),
                expires_at TEXT NOT NULL,
                claimed_at TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_handoff_exp ON session_handoffs(expires_at)")
        # 形象「艺名 + 欢迎语」全局元数据（每个 avatar_id 一行，跨景区共享；游客端显示艺名）
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dh_avatar_meta (
                avatar_id    TEXT PRIMARY KEY,
                stage_name   TEXT NOT NULL,
                welcome_text TEXT NOT NULL DEFAULT '',
                updated_at   TEXT NOT NULL
                             DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
            )
        """)
        # 形象「按景区发布」表（生产者/消费者分离）：enabled 控制游客端可见性、sort 排序、
        # stage_name_override 允许某景区用不同艺名。无行 = 走默认可见规则（本景区专属+通用推荐可见）。
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dh_avatar_publish (
                scenic_id           TEXT NOT NULL,
                avatar_id           TEXT NOT NULL,
                enabled             INTEGER NOT NULL DEFAULT 1,
                sort                INTEGER NOT NULL DEFAULT 0,
                stage_name_override TEXT,
                updated_at          TEXT NOT NULL
                                    DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                PRIMARY KEY (scenic_id, avatar_id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_publish_scenic ON dh_avatar_publish(scenic_id)")
        # 游中画像（per-session）：从对话/轨迹里在线积累游客兴趣与关心点，供推荐/导航链路"懂他"。
        # 匿名 session 级、短命（48h 惰性自清）——人走画像消。绝不进 qa 事实问答链路（守准确率红线）。
        conn.execute("""
            CREATE TABLE IF NOT EXISTS visitor_profile (
                session_id   TEXT PRIMARY KEY,
                scenic_id    TEXT    NOT NULL DEFAULT 'lingshan',
                interests    TEXT    NOT NULL DEFAULT '[]',   -- JSON list：静态(开场快选)∪动态(对话推断)
                visited      TEXT    NOT NULL DEFAULT '[]',   -- JSON list：到访 POI（P3 轨迹填）
                asked_pois   TEXT    NOT NULL DEFAULT '[]',   -- JSON list：对话中问过的 POI 名
                intent_stats TEXT    NOT NULL DEFAULT '{}',   -- JSON dict：intent -> count
                traits       TEXT    NOT NULL DEFAULT '{}',   -- JSON dict：LLM 摘要 {style,needs,wishes,avoid} / 轨迹
                summary      TEXT    NOT NULL DEFAULT '',     -- LLM 一句话画像
                turn_count   INTEGER NOT NULL DEFAULT 0,
                updated_at   TEXT    NOT NULL
                             DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_vp_scenic ON visitor_profile(scenic_id, updated_at)")
        conn.commit()


def _ensure_columns(conn, table: str, cols: dict[str, str]) -> None:
    """幂等补列：SQLite 无 ADD COLUMN IF NOT EXISTS，先查 PRAGMA 再 ALTER。"""
    existing = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    for name, ddl in cols.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def save_conversation(
    session_id: str,
    scenic_id: str,
    user_message: str,
    ai_reply: str,
    emotion: str,
    context_used: bool,
) -> None:
    with get_db() as conn:
        conn.execute(
            """INSERT INTO conversations
               (session_id, scenic_id, user_message, ai_reply, emotion, context_used)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (session_id, scenic_id, user_message, ai_reply, emotion, int(context_used)),
        )


def save_event(
    session_id: str,
    scenic_id: str,
    type: str,
    group_type: str | None = None,
    lang: str | None = None,
    payload: dict | None = None,
) -> None:
    """落库一条客户端上报事件。payload 存 JSON 字符串，容错（坏 payload 不抛）。"""
    try:
        payload_str = json.dumps(payload, ensure_ascii=False) if payload else None
    except (TypeError, ValueError):
        payload_str = None
    with get_db() as conn:
        conn.execute(
            """INSERT INTO events (session_id, scenic_id, type, group_type, lang, payload)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (session_id, scenic_id, type, group_type, lang, payload_str),
        )


def load_theme_override(scenic_id: str) -> dict | None:
    """读某景区的主题覆盖；无则 None。只返回非空字段。"""
    with get_db() as conn:
        row = conn.execute(
            "SELECT name, primary_color, sweet_color FROM scenic_theme WHERE scenic_id=?",
            (scenic_id,),
        ).fetchone()
    if not row:
        return None
    out = {}
    if row["name"]:          out["name"] = row["name"]
    if row["primary_color"]: out["primary"] = row["primary_color"]
    if row["sweet_color"]:   out["sweet"] = row["sweet_color"]
    return out or None


def save_theme(scenic_id: str, name: str | None, primary: str | None, sweet: str | None) -> None:
    """管理端覆盖某景区主题（部分字段：保留已有、只更新传入的非空项）。"""
    with get_db() as conn:
        conn.execute(
            """INSERT INTO scenic_theme (scenic_id, name, primary_color, sweet_color, updated_at)
               VALUES (?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S','now','localtime'))
               ON CONFLICT(scenic_id) DO UPDATE SET
                 name          = COALESCE(excluded.name, scenic_theme.name),
                 primary_color = COALESCE(excluded.primary_color, scenic_theme.primary_color),
                 sweet_color   = COALESCE(excluded.sweet_color, scenic_theme.sweet_color),
                 updated_at    = excluded.updated_at""",
            (scenic_id, name, primary, sweet),
        )


# ─────────────────────────── 扫码接力 / 同游 ───────────────────────────
# 时间戳统一 '%Y-%m-%d %H:%M:%S' 本地格式（与全表一致）→ 字符串字典序即时间序，可直接比较。
_TS = "%Y-%m-%d %H:%M:%S"


def save_handoff(token: str, scenic_id: str, snapshot: dict, source: str = "kiosk",
                 ttl_seconds: int = 300) -> str:
    """存一条接力快照，返回过期时刻。顺手清掉所有已过期行（惰性 GC，免后台任务）。"""
    now = _dt.datetime.now()
    expires = (now + _dt.timedelta(seconds=ttl_seconds)).strftime(_TS)
    payload = json.dumps(snapshot, ensure_ascii=False)
    with get_db() as conn:
        conn.execute("DELETE FROM session_handoffs WHERE expires_at < ?", (now.strftime(_TS),))
        conn.execute(
            """INSERT OR REPLACE INTO session_handoffs
               (token, scenic_id, snapshot, source, expires_at)
               VALUES (?, ?, ?, ?, ?)""",
            (token, scenic_id, payload, source, expires),
        )
    return expires


def claim_handoff(token: str, single_use: bool = False) -> dict | None:
    """凭 token 取接力快照。返回：
       None               → token 不存在
       {'expired': True}  → 已过期（顺手删除）
       {'claimed': True}  → single_use 且已被领取过
       {'snapshot':..., 'scenic_id':..., 'source':...} → 成功（标记 claimed_at）
    """
    now = _dt.datetime.now().strftime(_TS)
    with get_db() as conn:
        row = conn.execute(
            "SELECT scenic_id, snapshot, source, expires_at, claimed_at "
            "FROM session_handoffs WHERE token=?",
            (token,),
        ).fetchone()
        if not row:
            return None
        if row["expires_at"] < now:
            conn.execute("DELETE FROM session_handoffs WHERE token=?", (token,))
            return {"expired": True}
        if single_use and row["claimed_at"]:
            return {"claimed": True}
        conn.execute("UPDATE session_handoffs SET claimed_at=? WHERE token=?", (now, token))
        try:
            snap = json.loads(row["snapshot"])
        except (TypeError, ValueError):
            snap = {}
        return {"snapshot": snap, "scenic_id": row["scenic_id"], "source": row["source"]}
