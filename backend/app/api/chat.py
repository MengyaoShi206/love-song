# backend/app/api/chat.py
from typing import Dict, List, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    UploadFile,
    File,
    Form,
)
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from app.database import SessionLocal
from app.models.user import UserAccount, ChatMessage
from app.utils.multi_writer import MultiWriter

from datetime import datetime
import os, uuid

router = APIRouter()


# ========== DB Session 工具 ==========
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ========== 会话 key 工具 ==========
def make_session_key(a: int, b: int) -> str:
    """把两个 user_id 规范成 '小-大' 的 key，保证两边一致"""
    x, y = sorted([int(a), int(b)])
    return f"{x}-{y}"


# ========== REST：发送 & 历史记录 ==========
class SendMessageIn(BaseModel):
    from_user_id: int
    to_user_id: int
    content: str
    msg_type: str = "text"


@router.post("/send")
def send_message(payload: SendMessageIn, db: Session = Depends(get_db)):
    """普通 HTTP 发送消息（给不支持 WS 的情况作兜底）"""
    if not payload.content.strip():
        raise HTTPException(400, "内容不能为空")

    # 校验用户存在
    a = db.query(UserAccount).filter(UserAccount.id == payload.from_user_id).first()
    b = db.query(UserAccount).filter(UserAccount.id == payload.to_user_id).first()
    if not a or not b:
        raise HTTPException(404, "用户不存在")

    sk = make_session_key(payload.from_user_id, payload.to_user_id)
    now = datetime.utcnow()

    msg = ChatMessage(
        from_user_id=payload.from_user_id,
        to_user_id=payload.to_user_id,
        session_key=sk,
        msg_type=payload.msg_type or "text",
        content=payload.content.strip(),
        created_at=now,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    # 写 Doris
    MultiWriter.write(msg, db=db, mirror=True)

    return {
        "id": msg.id,
        "from_user_id": msg.from_user_id,
        "to_user_id": msg.to_user_id,
        "session_key": msg.session_key,
        "msg_type": msg.msg_type,
        "content": msg.content,
        "created_at": msg.created_at.isoformat(),
    }


@router.get("/history")
def get_history(
    me_id: int,
    other_id: int,
    limit: int = 50,
    before_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """按会话拉取两个人之间的历史消息"""
    if limit <= 0 or limit > 200:
        limit = 50

    sk = make_session_key(me_id, other_id)
    q = db.query(ChatMessage).filter(ChatMessage.session_key == sk)

    if before_id is not None:
        q = q.filter(ChatMessage.id < before_id)

    rows = q.order_by(desc(ChatMessage.id)).limit(limit).all()

    # 返回时再倒序，保证前端看到是从旧到新
    rows = list(reversed(rows))

    items = [
        {
            "id": r.id,
            "from_user_id": r.from_user_id,
            "to_user_id": r.to_user_id,
            "session_key": r.session_key,
            "msg_type": r.msg_type,
            "content": r.content,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
    return {"items": items}


# ========== 文件上传：图片 / 视频 / 文件 ==========
# 这里假设你的静态文件根目录是 STATIC_ROOT，和 main.py 里挂载 StaticFiles 对齐：
#   app.mount("/static", StaticFiles(directory=STATIC_ROOT), name="static")
STATIC_ROOT = os.getenv("STATIC_ROOT", "static")
CHAT_UPLOAD_SUBDIR = "chat"
UPLOAD_ROOT = os.path.join(STATIC_ROOT, CHAT_UPLOAD_SUBDIR)

os.makedirs(UPLOAD_ROOT, exist_ok=True)


@router.post("/upload")
async def upload_chat_file(
    from_user_id: int = Form(...),
    to_user_id: int = Form(...),
    kind: str = Form("file"),  # image / video / file
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """聊天附件上传：返回可访问 URL，并写一条消息记录再通过 WS 推送"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    # 校验用户存在
    a = db.query(UserAccount).filter(UserAccount.id == from_user_id).first()
    b = db.query(UserAccount).filter(UserAccount.id == to_user_id).first()
    if not a or not b:
        raise HTTPException(status_code=404, detail="用户不存在")

    kind = (kind or "file").lower()
    if kind not in {"image", "video", "file"}:
        kind = "file"

    today = datetime.utcnow().strftime("%Y%m%d")
    save_dir = os.path.join(UPLOAD_ROOT, today)
    os.makedirs(save_dir, exist_ok=True)

    _, ext = os.path.splitext(file.filename)
    ext = ext or ""
    filename = f"{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(save_dir, filename)

    content_bytes = await file.read()
    with open(save_path, "wb") as f:
        f.write(content_bytes)

    # 构造对外 URL：/static/chat/20251118/xxx.png 这种
    url_path = f"/static/{CHAT_UPLOAD_SUBDIR}/{today}/{filename}"

    # 注意：这里需要保证 ChatMessage.msg_type Enum 里包含 image / file / video
    msg_type = "image" if kind == "image" else ("video" if kind == "video" else "file")
    sk = make_session_key(from_user_id, to_user_id)
    now = datetime.utcnow()

    msg = ChatMessage(
        from_user_id=from_user_id,
        to_user_id=to_user_id,
        session_key=sk,
        msg_type=msg_type,
        content=url_path,
        created_at=now,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    # 写 Doris
    MultiWriter.write(msg, db=db, mirror=True)

    payload = {
        "type": "chat",
        "id": msg.id,
        "from_user_id": msg.from_user_id,
        "to_user_id": msg.to_user_id,
        "session_key": msg.session_key,
        "msg_type": msg.msg_type,
        "content": msg.content,
        "created_at": msg.created_at.isoformat(),
    }

    # 通过 WS 推送给双方在线连接（下面的 manager）
    await manager.broadcast_chat(payload, [from_user_id, to_user_id])

    return {"url": url_path, "message": payload}


# ========== WebSocket 实时聊天 ==========
class ConnectionManager:
    def __init__(self):
        # user_id -> [WebSocket, ...]
        self.active: Dict[int, List[WebSocket]] = {}

    async def connect(self, uid: int, websocket: WebSocket):
        await websocket.accept()
        self.active.setdefault(uid, []).append(websocket)
        print(f"[WS] user {uid} connected, total={len(self.active.get(uid, []))}")

    def disconnect(self, uid: int, websocket: WebSocket):
        arr = self.active.get(uid)
        if not arr:
            return
        try:
            arr.remove(websocket)
        except ValueError:
            pass
        if not arr:
            self.active.pop(uid, None)
        print(f"[WS] user {uid} disconnected")

    async def send_to_user(self, uid: int, data: dict):
        """给某个用户所有连接发消息"""
        arr = self.active.get(uid, [])
        dead: List[WebSocket] = []
        for ws in arr:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(uid, ws)

    async def broadcast_chat(self, msg: dict, uids: List[int]):
        for uid in set(uids):
            await self.send_to_user(uid, msg)


manager = ConnectionManager()


@router.websocket("/ws/{uid}")
async def chat_ws(websocket: WebSocket, uid: int):
    """
    WebSocket：/api/chat/ws/{uid}
    前端连上后，发送 JSON：
        {
          "type": "chat",
          "to_user_id": 123,
          "content": "你好 或者 文件URL",
          "msg_type": "text|image|file|video|location"
        }
    其中 msg_type 支持：
        - text：文本（含表情）
        - image：图片
        - file：文件
        - video：视频
        - location：位置（URL 链接）
    服务端会：
        1) 写入 MySQL
        2) MultiWriter 写 Doris
        3) 推给双方在线连接
    """
    await manager.connect(uid, websocket)
    db = SessionLocal()

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = str(data.get("type") or "chat").lower()

            # 心跳包
            if msg_type in ("ping", "heartbeat"):
                await websocket.send_json(
                    {"type": "pong", "ts": datetime.utcnow().isoformat()}
                )
                continue

            if msg_type != "chat":
                continue

            to_user_id = int(data.get("to_user_id") or 0)
            content = str(data.get("content") or "").strip()
            raw_msg_type = str(data.get("msg_type") or "text")

            if not to_user_id or not content:
                await websocket.send_json(
                    {
                        "type": "error",
                        "error": "to_user_id 或 content 缺失",
                    }
                )
                continue

            # 校验对端存在
            other = db.query(UserAccount).filter(UserAccount.id == to_user_id).first()
            if not other:
                await websocket.send_json(
                    {
                        "type": "error",
                        "error": "对方用户不存在",
                    }
                )
                continue

            # 写入 DB
            sk = make_session_key(uid, to_user_id)
            now = datetime.utcnow()
            msg = ChatMessage(
                from_user_id=uid,
                to_user_id=to_user_id,
                session_key=sk,
                msg_type=raw_msg_type,
                content=content,
                created_at=now,
            )
            db.add(msg)
            db.commit()
            db.refresh(msg)

            # 写 Doris
            MultiWriter.write(msg, db=db, mirror=True)

            # 推给双方
            payload = {
                "type": "chat",
                "id": msg.id,
                "from_user_id": msg.from_user_id,
                "to_user_id": msg.to_user_id,
                "session_key": msg.session_key,
                "msg_type": msg.msg_type,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
            }
            await manager.broadcast_chat(payload, [uid, to_user_id])

    except WebSocketDisconnect:
        manager.disconnect(uid, websocket)
    finally:
        db.close()
