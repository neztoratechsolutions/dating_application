
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from database import SessionLocal
from models.chat_history import Chat
from services.chat_service import save_chat_message

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatConnectionManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, chat_id: int, websocket: WebSocket):
        # The route accepts the WebSocket before calling this method.
        self.active_connections.setdefault(chat_id, set()).add(websocket)

    async def disconnect(self, chat_id: int, websocket: WebSocket):
        connections = self.active_connections.get(chat_id, set())
        connections.discard(websocket)

        if not connections:
            self.active_connections.pop(chat_id, None)

    async def broadcast(self, chat_id: int, payload: dict):
        connections = list(self.active_connections.get(chat_id, set()))

        for connection in connections:
            try:
                await connection.send_json(payload)
            except Exception:
                logger.exception(
                    "Failed to broadcast to chat_id=%s",
                    chat_id,
                )
                await self.disconnect(chat_id, connection)


manager = ChatConnectionManager()


@router.websocket("/ws/chat/{chat_id}")
async def websocket_chat(
    websocket: WebSocket,
    chat_id: int,
    user_id: int,
):
    # Validate chat membership before accepting the connection.
    db: Session = SessionLocal()

    try:
        chat = (
            db.query(Chat)
            .filter(
                Chat.id == chat_id,
                Chat.status.is_(True),
            )
            .first()
        )

        if chat is None:
            await websocket.close(
                code=1008,
                reason="Chat not found or inactive",
            )
            return

        if user_id not in (chat.user_one_id, chat.user_two_id):
            await websocket.close(
                code=1008,
                reason="User is not a participant in this chat",
            )
            return

    except Exception:
        logger.exception("Chat WebSocket validation failed")
        await websocket.close(
            code=1011,
            reason="Unable to validate chat",
        )
        return
    finally:
        db.close()

    # IMPORTANT: Accept before sending JSON.
    await websocket.accept()
    await manager.connect(chat_id, websocket)

    try:
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
                    "message": "Invalid WebSocket payload",
                })
                continue

            event_type = data.get("type")

            if event_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if event_type in ("typing", "stop_typing"):
                await manager.broadcast(chat_id, {
                    "type": event_type,
                    "chat_id": chat_id,
                    "user_id": user_id,
                })
                continue

            if event_type != "message":
                await websocket.send_json({
                    "type": "error",
                    "message": "Unsupported event type",
                })
                continue

            content = (
                data.get("content") or data.get("message") or ""
            ).strip()
            attachment = data.get("attachment") or None
            message_type = data.get("message_type", "text")

            if not content and not attachment:
                await websocket.send_json({
                    "type": "error",
                    "message": "Message content is required",
                })
                continue

            db_message: Session = SessionLocal()

            try:
                message = save_chat_message(
                    db=db_message,
                    chat_id=chat_id,
                    sender_id=user_id,
                    content=content,
                    message_type=message_type,
                    attachment=attachment,
                    message_metadata=data.get("metadata"),
                    reply_message_id=data.get("reply_message_id"),
                )

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
                continue
            except Exception:
                logger.exception(
                    "Failed to save message: chat_id=%s user_id=%s",
                    chat_id,
                    user_id,
                )
                await websocket.send_json({
                    "type": "error",
                    "message": "Message could not be saved",
                })
                continue
            finally:
                db_message.close()

            # Only broadcast after the database service commits.
            await manager.broadcast(chat_id, payload)

            await websocket.send_json({
                "type": "message_sent",
                "chat_id": chat_id,
                "message_id": payload["message_id"],
            })

    except WebSocketDisconnect:
        logger.info(
            "WebSocket disconnected: chat_id=%s user_id=%s",
            chat_id,
            user_id,
        )
    except Exception:
        logger.exception(
            "WebSocket runtime error: chat_id=%s user_id=%s",
            chat_id,
            user_id,
        )
    finally:
        await manager.disconnect(chat_id, websocket)
