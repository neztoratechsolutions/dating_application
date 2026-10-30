
import logging
from datetime import datetime, timezone
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

# This service must contain the wallet deduction and message-saving logic.
from services.chat_service import save_chat_message


router = APIRouter(tags=["Chat"])
logger = logging.getLogger(__name__)


# ==========================================================
# WEBSOCKET CONNECTION MANAGER
# ==========================================================

class ChatConnectionManager:

    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, chat_id: int, websocket: WebSocket):
        # Accept before registering or sending messages.
        await websocket.accept()

        self.active_connections.setdefault(chat_id, set()).add(websocket)

        logger.info(
            "WebSocket connected: chat_id=%s",
            chat_id,
        )

    async def disconnect(self, chat_id: int, websocket: WebSocket):

        connections = self.active_connections.get(chat_id, set())

        connections.discard(websocket)

        if not connections:
            self.active_connections.pop(chat_id, None)

        logger.info(
            "WebSocket disconnected: chat_id=%s",
            chat_id,
        )

    async def broadcast(self, chat_id: int, data: dict):

        connections = list(
            self.active_connections.get(chat_id, set())
        )

        for connection in connections:

            try:
                await connection.send_json(data)

            except Exception:

                logger.exception(
                    "WebSocket broadcast failed: chat_id=%s",
                    chat_id,
                )

                await self.disconnect(chat_id, connection)

                try:
                    await connection.close(
                        code=1011,
                        reason="Message delivery failed",
                    )
                except Exception:
                    pass


manager = ChatConnectionManager()


# ==========================================================
# COMMON HELPERS
# ==========================================================

def get_existing_user(db: Session, user_id: int) -> User:

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    return user


def get_chat_for_user(
    db: Session,
    chat_id: int,
    user_id: int,
) -> Chat:

    chat = (
        db.query(Chat)
        .filter(
            Chat.id == chat_id,
            or_(
                Chat.user_one_id == user_id,
                Chat.user_two_id == user_id,
            ),
            Chat.status.is_(True),
        )
        .first()
    )

    if not chat:
        raise HTTPException(
            status_code=404,
            detail="Chat not found or access denied",
        )

    return chat


def serialize_message(message: ChatMessage) -> dict:

    return {
        "message_id": message.id,
        "id": message.id,
        "chat_id": message.chat_id,
        "sender_id": message.sender_id,
        "receiver_id": message.receiver_id,
        "content": message.message or "",
        "message": message.message or "",
        "message_type": message.message_type or "text",
        "attachment": message.attachment,
        "metadata": message.message_metadata,
        "is_read": message.is_read,
        "is_delivered": message.is_delivered,
        "is_deleted": message.is_deleted,
        "reply_message_id": message.reply_message_id,
        "created_at": (
            message.created_at.isoformat()
            if message.created_at
            else None
        ),
    }


def save_message(
    db: Session,
    chat_id: int,
    sender_id: int,
    content: str = "",
    message_type: str = "text",
    attachment: str = None,
    message_metadata: dict = None,
    reply_message_id: int = None,
):
    """
    All message creation goes through chat_service.

    Customer -> Creator:
        Deduct configured chat coins from customer wallet.

    Creator -> Customer:
        No wallet deduction.

    Wallet transaction and message must be committed
    atomically inside save_chat_message().
    """

    return save_chat_message(
        db=db,
        chat_id=chat_id,
        sender_id=sender_id,
        content=content,
        message_type=message_type,
        attachment=attachment,
        message_metadata=message_metadata,
        reply_message_id=reply_message_id,
    )


# ==========================================================
# CREATE OR RETRIEVE EXISTING CONVERSATION
# POST /chats/with/{other_user_id}?user_id=3
# ==========================================================

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
    )

    try:
        db.add(chat)
        db.commit()
        db.refresh(chat)

    except Exception:

        db.rollback()
        logger.exception("Failed to create chat")

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


# ==========================================================
# LIST CONVERSATIONS
# GET /chats/?user_id=3
# ==========================================================

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
        .order_by(
            Chat.updated_at.desc(),
            Chat.id.desc(),
        )
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

        unread_count = (
            (chat.unread_count_user1 or 0)
            if chat.user_one_id == user_id
            else (chat.unread_count_user2 or 0)
        )

        results.append({
            "chat_id": chat.id,
            "user_one_id": chat.user_one_id,
            "user_two_id": chat.user_two_id,
            "other_user_id": other_user_id,
            "other_user_email": (
                other_user.email if other_user else None
            ),
            "last_message": chat.last_message,
            "last_message_at": (
                chat.last_message_at.isoformat()
                if chat.last_message_at
                else None
            ),
            "unread_count": unread_count,
            "status": chat.status,
        })

    return results


# ==========================================================
# GET MESSAGE HISTORY
# GET /chats/1/messages?user_id=3
# ==========================================================

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

    return [
        serialize_message(message)
        for message in messages
    ]


# ==========================================================
# SEND MESSAGE THROUGH REST
# POST /chats/1/messages?user_id=3
# ==========================================================

@router.post("/chats/{chat_id}/messages")
def send_chat_message(
    chat_id: int,
    payload: dict,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):

    get_existing_user(db, user_id)
    get_chat_for_user(db, chat_id, user_id)

    content = payload.get("content", "")
    attachment = payload.get("attachment")
    message_type = payload.get("message_type", "text")
    metadata = payload.get("metadata")
    reply_message_id = payload.get("reply_message_id")

    if not isinstance(content, str):
        raise HTTPException(
            status_code=400,
            detail="Invalid message content",
        )

    content = content.strip()

    if not content and not attachment:
        raise HTTPException(
            status_code=400,
            detail="Message content is required",
        )

    try:

        message = save_message(
            db=db,
            chat_id=chat_id,
            sender_id=user_id,
            content=content,
            message_type=message_type,
            attachment=attachment,
            message_metadata=metadata,
            reply_message_id=reply_message_id,
        )

        return serialize_message(message)

    except ValueError as exc:

        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception:

        db.rollback()
        logger.exception("REST message send failed")

        raise HTTPException(
            status_code=500,
            detail="Message could not be saved",
        )


# ==========================================================
# MARK MESSAGES AS READ
# POST /chats/1/read?user_id=3
# ==========================================================

@router.post("/chats/{chat_id}/read")
def mark_messages_read(
    chat_id: int,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):

    get_existing_user(db, user_id)

    chat = get_chat_for_user(
        db,
        chat_id,
        user_id,
    )

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

    return {
        "message": "Messages marked as read",
        "chat_id": chat_id,
        "user_id": user_id,
    }


# ==========================================================
# MARK MESSAGES AS DELIVERED
# POST /chats/1/delivered?user_id=3
# ==========================================================

@router.post("/chats/{chat_id}/delivered")
def mark_messages_delivered(
    chat_id: int,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):

    get_existing_user(db, user_id)

    get_chat_for_user(
        db,
        chat_id,
        user_id,
    )

    db.query(ChatMessage).filter(
        ChatMessage.chat_id == chat_id,
        ChatMessage.receiver_id == user_id,
        ChatMessage.is_delivered.is_(False),
    ).update(
        {ChatMessage.is_delivered: True},
        synchronize_session=False,
    )

    db.commit()

    return {
        "message": "Messages marked as delivered",
        "chat_id": chat_id,
    }


# ==========================================================
# DELETE MESSAGE FOR EVERYONE
# DELETE /chats/1/messages/10?user_id=3
# ==========================================================

@router.delete("/chats/{chat_id}/messages/{message_id}")
def delete_chat_message(
    chat_id: int,
    message_id: int,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):

    get_existing_user(db, user_id)

    get_chat_for_user(
        db,
        chat_id,
        user_id,
    )

    message = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.id == message_id,
            ChatMessage.chat_id == chat_id,
        )
        .first()
    )

    if not message:
        raise HTTPException(
            status_code=404,
            detail="Message not found",
        )

    if message.sender_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Only the sender can delete this message",
        )

    message.is_deleted = True

    db.commit()

    return {
        "message": "Message deleted",
        "message_id": message_id,
    }


# ==========================================================
# WEBSOCKET CHAT
# /ws/chat/1?user_id=3
# ==========================================================

@router.websocket("/ws/chat/{chat_id}")
async def websocket_chat(
    websocket: WebSocket,
    chat_id: int,
    user_id: int,
):

    db = SessionLocal()
    connected = False

    try:

        # --------------------------------------------------
        # VALIDATE USER AND CHAT BEFORE ACCEPTING
        # --------------------------------------------------

        get_existing_user(db, user_id)

        get_chat_for_user(
            db,
            chat_id,
            user_id,
        )

        # manager.connect() calls websocket.accept()
        await manager.connect(
            chat_id,
            websocket,
        )

        connected = True

        # --------------------------------------------------
        # CONNECTION ACKNOWLEDGEMENT
        # --------------------------------------------------

        await websocket.send_json({
            "type": "connected",
            "chat_id": chat_id,
            "user_id": user_id,
            "message": "Connected successfully",
        })

        logger.info(
            "WebSocket ready: chat_id=%s user_id=%s",
            chat_id,
            user_id,
        )

        # --------------------------------------------------
        # RECEIVE EVENTS
        # --------------------------------------------------

        while True:

            data = await websocket.receive_json()

            if not isinstance(data, dict):

                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid message payload",
                })

                continue

            event_type = data.get("type")

            # ==================================================
            # MESSAGE EVENT
            # ==================================================

            if event_type == "message":

                content = (
                    data.get("content")
                    or data.get("message")
                    or ""
                )

                if not isinstance(content, str):
                    content = ""

                content = content.strip()

                attachment = data.get("attachment")

                message_type = data.get(
                    "message_type",
                    "text",
                )

                metadata = data.get("metadata")

                reply_message_id = data.get(
                    "reply_message_id"
                )

                if not content and not attachment:

                    await websocket.send_json({
                        "type": "error",
                        "message": "Message content is required",
                    })

                    continue

                try:

                    # Check participant access again.
                    get_chat_for_user(
                        db,
                        chat_id,
                        user_id,
                    )

                    # Customer wallet deduction and message save
                    # happen inside this service.
                    message = save_message(
                        db=db,
                        chat_id=chat_id,
                        sender_id=user_id,
                        content=content,
                        message_type=message_type,
                        attachment=attachment,
                        message_metadata=metadata,
                        reply_message_id=reply_message_id,
                    )

                    message_data = serialize_message(message)

                    # Broadcast to both participants.
                    await manager.broadcast(
                        chat_id,
                        {
                            "type": "message",
                            **message_data,
                        },
                    )

                    # Acknowledge the sender.
                    await websocket.send_json({
                        "type": "message_sent",
                        **message_data,
                    })

                except ValueError as exc:

                    db.rollback()

                    # For example: insufficient customer coins.
                    await websocket.send_json({
                        "type": "error",
                        "message": str(exc),
                    })

                except HTTPException as exc:

                    db.rollback()

                    await websocket.send_json({
                        "type": "error",
                        "message": exc.detail,
                    })

                except Exception:

                    db.rollback()

                    logger.exception(
                        "Failed to save WebSocket message: "
                        "chat_id=%s user_id=%s",
                        chat_id,
                        user_id,
                    )

                    await websocket.send_json({
                        "type": "error",
                        "message": (
                            "Message could not be saved. "
                            "Please try again."
                        ),
                    })

            # ==================================================
            # TYPING EVENT
            # ==================================================

            elif event_type == "typing":

                await manager.broadcast(
                    chat_id,
                    {
                        "type": "typing",
                        "user_id": user_id,
                        "chat_id": chat_id,
                        "is_typing": True,
                    },
                )

            # ==================================================
            # STOP TYPING EVENT
            # ==================================================

            elif event_type == "stop_typing":

                await manager.broadcast(
                    chat_id,
                    {
                        "type": "stop_typing",
                        "user_id": user_id,
                        "chat_id": chat_id,
                        "is_typing": False,
                    },
                )

            # ==================================================
            # PING / PONG
            # ==================================================

            elif event_type == "ping":

                await websocket.send_json({
                    "type": "pong",
                })

            # ==================================================
            # UNKNOWN EVENT
            # ==================================================

            else:

                await websocket.send_json({
                    "type": "error",
                    "message": "Unsupported WebSocket event type",
                })

    except WebSocketDisconnect:

        logger.info(
            "WebSocket disconnected normally: "
            "chat_id=%s user_id=%s",
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

        # The connection has not been accepted yet.
        if not connected:

            try:
                await websocket.close(
                    code=1008,
                    reason=str(exc.detail)[:120],
                )
            except Exception:
                pass

        else:

            try:
                await websocket.send_json({
                    "type": "error",
                    "message": exc.detail,
                })
            except Exception:
                pass

    except Exception:

        logger.exception(
            "Unexpected WebSocket failure: "
            "chat_id=%s user_id=%s",
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

        # Disconnect is async, so always await it.
        if connected:

            await manager.disconnect(
                chat_id,
                websocket,
            )

        db.close()
