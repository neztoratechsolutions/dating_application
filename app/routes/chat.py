
import logging
from typing import Dict, Set

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import get_db, SessionLocal
from models.users import User
from models.chat_history import Chat, ChatMessage
from services.chat_service import save_chat_message

import logging

from database import SessionLocal
from services.chat_service import save_chat_message


router = APIRouter(tags=["Chat"])
logger = logging.getLogger(__name__)


# ==================================================
# WEBSOCKET CONNECTION MANAGER
# ==================================================

class ChatConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, chat_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.setdefault(chat_id, set()).add(websocket)

    def disconnect(self, chat_id: int, websocket: WebSocket):
        connections = self.active_connections.get(chat_id)

        if connections is None:
            return

        connections.discard(websocket)

        if not connections:
            self.active_connections.pop(chat_id, None)

    async def broadcast(self, chat_id: int, data: dict):
        connections = list(self.active_connections.get(chat_id, set()))

        for connection in connections:
            try:
                await connection.send_json(data)
            except Exception:
                logger.warning(
                    "WebSocket broadcast failed: chat_id=%s",
                    chat_id,
                    exc_info=True,
                )

                self.disconnect(chat_id, connection)

                try:
                    await connection.close(
                        code=1011,
                        reason="WebSocket delivery failed",
                    )
                except Exception:
                    pass


manager = ChatConnectionManager()


# ==================================================
# COMMON HELPERS
# ==================================================

def get_existing_user(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user


def get_chat_for_user(
    db: Session,
    chat_id: int,
    user_id: int,
) -> Chat:
    chat = db.query(Chat).filter(Chat.id == chat_id).first()

    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")

    if user_id not in (chat.user_one_id, chat.user_two_id):
        raise HTTPException(
            status_code=403,
            detail="You are not a participant in this chat",
        )

    if not chat.status:
        raise HTTPException(
            status_code=400,
            detail="This chat is inactive",
        )

    return chat


def serialize_message(message: ChatMessage) -> dict:
    return {
        "message_id": message.id,
        "chat_id": message.chat_id,
        "sender_id": message.sender_id,
        "receiver_id": message.receiver_id,
        "content": message.message or "",
        "message_type": message.message_type or "text",
        "attachment": message.attachment,
        "is_read": bool(message.is_read),
        "is_delivered": bool(message.is_delivered),
        "created_at": (
            message.created_at.isoformat()
            if message.created_at
            else None
        ),
    }


def chat_response(chat: Chat, user_id: int, other_user: User = None):
    unread_count = (
        (chat.unread_count_user1 or 0)
        if chat.user_one_id == user_id
        else (chat.unread_count_user2 or 0)
    )

    return {
        "chat_id": chat.id,
        "user_one_id": chat.user_one_id,
        "user_two_id": chat.user_two_id,
        "other_user_id": (
            chat.user_two_id
            if chat.user_one_id == user_id
            else chat.user_one_id
        ),
        "other_user_email": other_user.email if other_user else None,
        "last_message": chat.last_message,
        "last_message_at": (
            chat.last_message_at.isoformat()
            if chat.last_message_at
            else None
        ),
        "unread_count": unread_count,
        "status": chat.status,
    }


# ==================================================
# CREATE OR RETRIEVE CONVERSATION
# POST /chats/with/{other_user_id}?user_id=3
# ==================================================

@router.post("/chats/with/{other_user_id}")
def create_or_get_chat(
    other_user_id: int,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    get_existing_user(db, user_id)
    get_existing_user(db, other_user_id)

    if user_id == other_user_id:
        raise HTTPException(
            status_code=400,
            detail="You cannot create a chat with yourself",
        )

    chat = (
        db.query(Chat)
        .filter(
            or_(
                (
                    (Chat.user_one_id == user_id)
                    & (Chat.user_two_id == other_user_id)
                ),
                (
                    (Chat.user_one_id == other_user_id)
                    & (Chat.user_two_id == user_id)
                ),
            )
        )
        .first()
    )

    if chat:
        if not chat.status:
            raise HTTPException(
                status_code=400,
                detail="This chat is inactive",
            )

        return {
            "message": "Conversation retrieved successfully",
            "chat_id": chat.id,
            "user_one_id": chat.user_one_id,
            "user_two_id": chat.user_two_id,
            "existing": True,
        }

    chat = Chat(
        user_one_id=user_id,
        user_two_id=other_user_id,
        status=True,
        unread_count_user1=0,
        unread_count_user2=0,
    )

    try:
        db.add(chat)
        db.commit()
        db.refresh(chat)

    except Exception:
        db.rollback()
        logger.exception(
            "Failed to create chat: user_id=%s other_user_id=%s",
            user_id,
            other_user_id,
        )
        raise HTTPException(
            status_code=500,
            detail="Unable to create conversation",
        )

    return {
        "message": "Conversation created successfully",
        "chat_id": chat.id,
        "user_one_id": chat.user_one_id,
        "user_two_id": chat.user_two_id,
        "existing": False,
    }


# ==================================================
# LIST CONVERSATIONS
# GET /chats/?user_id=3
# ==================================================

@router.get("/chats/")
def get_user_chats(
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    get_existing_user(db, user_id)

    chats = (
        db.query(Chat)
        .filter(
            or_(
                Chat.user_one_id == user_id,
                Chat.user_two_id == user_id,
            ),
            Chat.status.is_(True),
        )
        .order_by(Chat.updated_at.desc(), Chat.id.desc())
        .all()
    )

    results = []

    for chat in chats:
        other_user_id = (
            chat.user_two_id
            if chat.user_one_id == user_id
            else chat.user_one_id
        )

        other_user = (
            db.query(User)
            .filter(User.id == other_user_id)
            .first()
        )

        results.append(chat_response(chat, user_id, other_user))

    return results


# ==================================================
# GET MESSAGE HISTORY
# GET /chats/1/messages?user_id=3
# ==================================================

@router.get("/chats/{chat_id}/messages")
def get_chat_messages(
    chat_id: int,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    get_existing_user(db, user_id)
    get_chat_for_user(db, chat_id, user_id)

    messages = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.chat_id == chat_id,
            or_(
                ChatMessage.is_deleted.is_(False),
                ChatMessage.is_deleted.is_(None),
            ),
        )
        .order_by(
            ChatMessage.created_at.asc(),
            ChatMessage.id.asc(),
        )
        .all()
    )

    return [serialize_message(message) for message in messages]


# ==================================================
# SEND MESSAGE THROUGH REST
# POST /chats/1/messages?user_id=3
# JSON: {"content": "Hello"}
# ==================================================

@router.post("/chats/{chat_id}/messages")
def send_chat_message(
    chat_id: int,
    payload: dict,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    get_existing_user(db, user_id)
    get_chat_for_user(db, chat_id, user_id)

    content = payload.get("content") or payload.get("message")

    if not isinstance(content, str) or not content.strip():
        raise HTTPException(
            status_code=400,
            detail="Message content is required",
        )

    try:
        message = save_chat_message(
            db=db,
            chat_id=chat_id,
            sender_id=user_id,
            content=content.strip(),
        )

        return serialize_message(message)

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    except Exception:
        db.rollback()
        logger.exception(
            "REST message save failed: chat_id=%s user_id=%s",
            chat_id,
            user_id,
        )

        raise HTTPException(
            status_code=500,
            detail="Message could not be saved",
        )


# ==================================================
# MARK MESSAGES AS READ
# POST /chats/1/read?user_id=3
# ==================================================

@router.post("/chats/{chat_id}/read")
def mark_messages_read(
    chat_id: int,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    get_existing_user(db, user_id)
    chat = get_chat_for_user(db, chat_id, user_id)

    try:
        db.query(ChatMessage).filter(
            ChatMessage.chat_id == chat_id,
            ChatMessage.receiver_id == user_id,
            ChatMessage.is_read.is_(False),
        ).update(
            {ChatMessage.is_read: True},
            synchronize_session=False,
        )

        if chat.user_one_id == user_id:
            chat.unread_count_user1 = 0
        else:
            chat.unread_count_user2 = 0

        db.commit()

    except Exception:
        db.rollback()
        logger.exception(
            "Mark-as-read failed: chat_id=%s user_id=%s",
            chat_id,
            user_id,
        )
        raise HTTPException(
            status_code=500,
            detail="Unable to mark messages as read",
        )

    return {
        "message": "Messages marked as read",
        "chat_id": chat_id,
        "user_id": user_id,
    }


# ==================================================
# MARK MESSAGES AS DELIVERED
# POST /chats/1/delivered?user_id=3
# ==================================================

@router.post("/chats/{chat_id}/delivered")
def mark_messages_delivered(
    chat_id: int,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    get_existing_user(db, user_id)
    get_chat_for_user(db, chat_id, user_id)

    try:
        db.query(ChatMessage).filter(
            ChatMessage.chat_id == chat_id,
            ChatMessage.receiver_id == user_id,
            ChatMessage.is_delivered.is_(False),
        ).update(
            {ChatMessage.is_delivered: True},
            synchronize_session=False,
        )

        db.commit()

    except Exception:
        db.rollback()
        logger.exception(
            "Mark-as-delivered failed: chat_id=%s user_id=%s",
            chat_id,
            user_id,
        )
        raise HTTPException(
            status_code=500,
            detail="Unable to mark messages as delivered",
        )

    return {
        "message": "Messages marked as delivered",
        "chat_id": chat_id,
        "user_id": user_id,
    }


# ==================================================
# DELETE MESSAGE
# DELETE /chats/1/messages/10?user_id=3
# ==================================================

@router.delete("/chats/{chat_id}/messages/{message_id}")
def delete_chat_message(
    chat_id: int,
    message_id: int,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    get_existing_user(db, user_id)
    get_chat_for_user(db, chat_id, user_id)

    message = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.id == message_id,
            ChatMessage.chat_id == chat_id,
        )
        .first()
    )

    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")

    if message.sender_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Only the sender can delete this message",
        )

    try:
        message.is_deleted = True
        db.commit()

    except Exception:
        db.rollback()
        logger.exception(
            "Message deletion failed: message_id=%s user_id=%s",
            message_id,
            user_id,
        )
        raise HTTPException(
            status_code=500,
            detail="Unable to delete message",
        )

    return {
        "message": "Message deleted",
        "message_id": message_id,
    }


# ==================================================
# WEBSOCKET CHAT
# ws://host/ws/chat/1?user_id=3
# ==================================================

@router.websocket("/ws/chat/{chat_id}")
async def websocket_chat(
    websocket: WebSocket,
    chat_id: int,
    user_id: int,
):
    db = SessionLocal()
    connected = False

    try:
        # Validate before accepting the connection.
        get_existing_user(db, user_id)
        get_chat_for_user(db, chat_id, user_id)

        await manager.connect(chat_id, websocket)
        connected = True

        await websocket.send_json({
            "type": "connected",
            "chat_id": chat_id,
            "user_id": user_id,
        })

        while True:
            data = await websocket.receive_json()

            if not isinstance(data, dict):
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid message payload",
                })
                continue

            event_type = data.get("type")

            # SEND MESSAGE
            if event_type == "message":
                content = data.get("content") or data.get("message")

                if not isinstance(content, str) or not content.strip():
                    await websocket.send_json({
                        "type": "error",
                        "message": "Message content is required",
                    })
                    continue

                try:
                    # Recheck chat membership and status.
                    get_chat_for_user(db, chat_id, user_id)

                    message = save_chat_message(
                        db=db,
                        chat_id=chat_id,
                        sender_id=user_id,
                        content=content.strip(),
                    )

                    # The service must commit before this point.
                    serialized = serialize_message(message)

                    await manager.broadcast(
                        chat_id,
                        {
                            "type": "message",
                            **serialized,
                        },
                    )

                    await websocket.send_json({
                        "type": "message_sent",
                        "chat_id": chat_id,
                        "message_id": message.id,
                    })

                except ValueError as exc:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(exc),
                    })

                except Exception:
                    db.rollback()
                    logger.exception(
                        "WebSocket message save failed: "
                        "chat_id=%s user_id=%s",
                        chat_id,
                        user_id,
                    )

                    try:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Message could not be saved",
                        })
                    except Exception:
                        break

            # TYPING INDICATOR
            elif event_type == "typing":
                await manager.broadcast(
                    chat_id,
                    {
                        "type": "typing",
                        "chat_id": chat_id,
                        "user_id": user_id,
                    },
                )

            elif event_type == "stop_typing":
                await manager.broadcast(
                    chat_id,
                    {
                        "type": "stop_typing",
                        "chat_id": chat_id,
                        "user_id": user_id,
                    },
                )

            # HEARTBEAT
            elif event_type == "ping":
                await websocket.send_json({"type": "pong"})

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": "Unsupported WebSocket event type",
                })

    except WebSocketDisconnect:
        logger.info(
            "WebSocket disconnected: chat_id=%s user_id=%s",
            chat_id,
            user_id,
        )

    except HTTPException as exc:
        logger.warning(
            "WebSocket rejected: chat_id=%s user_id=%s detail=%s",
            chat_id,
            user_id,
            exc.detail,
        )

        if not connected:
            try:
                await websocket.close(
                    code=1008,
                    reason=str(exc.detail)[:120],
                )
            except Exception:
                pass

    except Exception:
        logger.exception(
            "Unexpected WebSocket error: chat_id=%s user_id=%s",
            chat_id,
            user_id,
        )

        if connected:
            try:
                await websocket.close(
                    code=1011,
                    reason="Internal server error",
                )
            except Exception:
                pass

    finally:
        if connected:
            manager.disconnect(chat_id, websocket)

        db.close()




async def process_websocket_message(
    websocket,
    manager,
    chat_id: int,
    user_id: int,
    data: dict,
):
    content = (
        data.get("content")
        or data.get("message")
        or ""
    ).strip()

    attachment = data.get("attachment")
    message_type = data.get("message_type", "text")
    message_metadata = data.get("metadata")
    reply_message_id = data.get("reply_message_id")

    if not content and not attachment:
        await websocket.send_json({
            "type": "error",
            "message": "Message content or attachment is required",
        })
        return

    db = SessionLocal()

    try:
        message = save_chat_message(
            db=db,
            chat_id=chat_id,
            sender_id=user_id,
            content=content,
            message_type=message_type,
            attachment=attachment,
            message_metadata=message_metadata,
            reply_message_id=reply_message_id,
        )

        # The service commits before this payload is broadcast.
        payload = {
            "type": "message",
            "message_id": message.id,
            "chat_id": message.chat_id,
            "sender_id": message.sender_id,
            "receiver_id": message.receiver_id,
            "content": message.message,
            "message_type": message.message_type,
            "attachment": message.attachment,
            "metadata": message.message_metadata,
            "reply_message_id": message.reply_message_id,
            "is_read": message.is_read,
            "is_delivered": message.is_delivered,
            "created_at": (
                message.created_at.isoformat()
                if message.created_at
                else None
            ),
        }

    except ValueError as exc:
        await websocket.send_json({
            "type": "error",
            "message": str(exc),
        })
        return

    except Exception:
        logger.exception(
            "Failed to process WebSocket message "
            "for chat_id=%s user_id=%s",
            chat_id,
            user_id,
        )
        await websocket.send_json({
            "type": "error",
            "message": "Message could not be saved. Please try again.",
        })
        return

    finally:
        db.close()

    await manager.broadcast(chat_id, payload)

    await websocket.send_json({
        "type": "message_sent",
        "chat_id": chat_id,
        "message_id": payload["message_id"],
    })


import os
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    status,
)

router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)

# =========================================
# IMAGE UPLOAD CONFIGURATION
# =========================================

UPLOAD_DIR = Path("uploads/chat_images")

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True
)

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB


# =========================================
# SEND IMAGE MESSAGE
# =========================================

@router.post(
    "/{chat_id}/send-image",
    status_code=status.HTTP_201_CREATED
)
async def send_image_message(
    chat_id: int,

    sender_id: int = Form(...),

    image: UploadFile = File(...),

    db: Session = Depends(get_db),
):

    # =====================================
    # 1. VALIDATE CHAT
    # =====================================

    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.status == True
    ).first()

    if not chat:

        raise HTTPException(
            status_code=404,
            detail="Chat not found"
        )

    # =====================================
    # 2. VALIDATE CHAT PARTICIPANT
    # =====================================

    if sender_id not in [
        chat.user_one_id,
        chat.user_two_id
    ]:

        raise HTTPException(
            status_code=403,
            detail="You are not a participant in this chat"
        )

    # =====================================
    # 3. DETERMINE RECEIVER
    # =====================================

    if sender_id == chat.user_one_id:

        receiver_id = chat.user_two_id

    else:

        receiver_id = chat.user_one_id

    # =====================================
    # 4. VALIDATE USERS
    # =====================================

    sender = db.query(User).filter(
        User.id == sender_id
    ).first()

    receiver = db.query(User).filter(
        User.id == receiver_id
    ).first()

    if not sender or not receiver:

        raise HTTPException(
            status_code=404,
            detail="Sender or receiver not found"
        )

    # =====================================
    # 5. VALIDATE IMAGE TYPE
    # =====================================

    content_type = image.content_type

    if content_type not in ALLOWED_IMAGE_TYPES:

        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG and WEBP images are allowed"
        )

    # =====================================
    # 6. READ IMAGE
    # =====================================

    image_data = await image.read(
        MAX_IMAGE_SIZE + 1
    )

    if not image_data:

        raise HTTPException(
            status_code=400,
            detail="Image is empty"
        )

    if len(image_data) > MAX_IMAGE_SIZE:

        raise HTTPException(
            status_code=413,
            detail="Image size must not exceed 5 MB"
        )

    # =====================================
    # 7. GENERATE UNIQUE IMAGE NAME
    # =====================================

    extension = ALLOWED_IMAGE_TYPES[content_type]

    image_name = (
        f"chat_{chat_id}_{uuid.uuid4().hex}{extension}"
    )

    image_path = UPLOAD_DIR / image_name

    # =====================================
    # 8. SAVE IMAGE
    # =====================================

    try:

        with open(image_path, "wb") as file:

            file.write(image_data)

        # =================================
        # 9. SAVE CHAT MESSAGE
        # =================================

        message = ChatMessage(

            chat_id=chat_id,

            sender_id=sender_id,

            receiver_id=receiver_id,

            message=None,

            attachment=f"/uploads/chat_images/{image_name}",

            message_type="image",

            is_read=False,

            is_delivered=False,

        )

        db.add(message)

        # =================================
        # 10. UPDATE CHAT LAST MESSAGE
        # =================================

        chat.last_message = "📷 Image"

        chat.last_message_by = sender_id

        # SQLAlchemy server default timestamps
        # will be applied when inserting.

        # =================================
        # 11. UPDATE UNREAD COUNT
        # =================================

        if receiver_id == chat.user_one_id:

            chat.unread_count_user1 = (
                (chat.unread_count_user1 or 0) + 1
            )

        else:

            chat.unread_count_user2 = (
                (chat.unread_count_user2 or 0) + 1
            )

        db.commit()

        db.refresh(message)

        # =================================
        # 12. RESPONSE
        # =================================

        return {

            "success": True,

            "message": "Image sent successfully",

            "data": {

                "id": message.id,

                "chat_id": message.chat_id,

                "sender_id": message.sender_id,

                "receiver_id": message.receiver_id,

                "message": message.message,

                "attachment": message.attachment,

                "message_type": message.message_type,

                "is_read": message.is_read,

                "is_delivered": message.is_delivered,

                "created_at": message.created_at,

            }

        }

    except Exception:

        db.rollback()

        # Remove uploaded image if database operation fails.

        if image_path.exists():

            image_path.unlink()

        raise HTTPException(
            status_code=500,
            detail="Failed to send image message"
        )