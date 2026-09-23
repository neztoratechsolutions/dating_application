from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from database import get_db
from models.chat_history import ChatMessage, Chat
from models.users import User
from schemas.chatmessage import ChatMessageCreate, ChatMessageUpdate


router = APIRouter(
    prefix="/chat-message",
    tags=["Chat Message"]
)


# =========================================================
# CREATE CHAT MESSAGE
# =========================================================

@router.post("/message")
def create_chat_message(
    data: ChatMessageCreate,
    db: Session = Depends(get_db)
):

    # Check Chat
    chat = db.query(Chat).filter(
        Chat.id == data.chat_id
    ).first()

    if not chat:
        return JSONResponse(
            status_code=404,
            content={
                "message": "Chat not found"
            }
        )

    # Check Sender
    sender = db.query(User).filter(
        User.id == data.sender_id
    ).first()

    if not sender:
        return JSONResponse(
            status_code=404,
            content={
                "message": "Sender not found"
            }
        )

    # Check Receiver
    receiver = db.query(User).filter(
        User.id == data.receiver_id
    ).first()

    if not receiver:
        return JSONResponse(
            status_code=404,
            content={
                "message": "Receiver not found"
            }
        )

    # Check users belong to this chat
    if not (
        (
            chat.user_one_id == data.sender_id
            and
            chat.user_two_id == data.receiver_id
        )
        or
        (
            chat.user_one_id == data.receiver_id
            and
            chat.user_two_id == data.sender_id
        )
    ):
        return JSONResponse(
            status_code=400,
            content={
                "message": "Users do not belong to this chat"
            }
        )

    # Create message
    chat_message = ChatMessage(
        chat_id=data.chat_id,
        sender_id=data.sender_id,
        receiver_id=data.receiver_id,
        message=data.message,
        attachment=getattr(data, "attachment", None),
        message_type=data.message_type,
        is_read=False,
        is_delivered=True,
        is_deleted=False,
        reply_message_id=getattr(data, "reply_message_id", None)
    )

    db.add(chat_message)

    # Update Chat information
    chat.last_message = data.message
    chat.last_message_at = func.now()
    chat.last_message_by = data.sender_id

    # Update unread count
    if data.sender_id == chat.user_one_id:
        chat.unread_count_user2 += 1
    else:
        chat.unread_count_user1 += 1

    db.commit()
    db.refresh(chat_message)

    return JSONResponse(
        status_code=201,
        content={
            "message": "Chat message created successfully",
            "data": {
                "id": chat_message.id,
                "chat_id": chat_message.chat_id,
                "sender_id": chat_message.sender_id,
                "receiver_id": chat_message.receiver_id,
                "message": chat_message.message,
                "attachment": chat_message.attachment,
                "message_type": chat_message.message_type,
                "is_read": chat_message.is_read,
                "is_delivered": chat_message.is_delivered,
                "is_deleted": chat_message.is_deleted,
                "reply_message_id": chat_message.reply_message_id,
                "created_at": (
                    chat_message.created_at.isoformat()
                    if chat_message.created_at
                    else None
                )
            }
        }
    )


# =========================================================
# GET ALL CHAT MESSAGES
# =========================================================

@router.get("/messages")
def get_all_chat_messages(
    db: Session = Depends(get_db)
):

    messages = db.query(ChatMessage).order_by(
        ChatMessage.created_at.desc()
    ).all()

    if not messages:
        return JSONResponse(
            status_code=404,
            content={
                "message": "No chat messages found"
            }
        )

    data = []

    for msg in messages:

        data.append({
            "id": msg.id,
            "chat_id": msg.chat_id,
            "sender_id": msg.sender_id,
            "receiver_id": msg.receiver_id,
            "message": msg.message,
            "attachment": msg.attachment,
            "message_type": msg.message_type,
            "is_read": msg.is_read,
            "is_delivered": msg.is_delivered,
            "is_deleted": msg.is_deleted,
            "reply_message_id": msg.reply_message_id,
            "created_at": (
                msg.created_at.isoformat()
                if msg.created_at
                else None
            )
        })

    return JSONResponse(
        status_code=200,
        content={
            "message": "Chat messages retrieved successfully",
            "data": data
        }
    )


# =========================================================
# GET CHAT MESSAGE BY ID
# =========================================================

@router.get("/message/{message_id}")
def get_chat_message_by_id(
    message_id: int,
    db: Session = Depends(get_db)
):

    msg = db.query(ChatMessage).filter(
        ChatMessage.id == message_id
    ).first()

    if not msg:
        return JSONResponse(
            status_code=404,
            content={
                "message": "Chat message not found"
            }
        )

    return JSONResponse(
        status_code=200,
        content={
            "message": "Chat message retrieved successfully",
            "data": {
                "id": msg.id,
                "chat_id": msg.chat_id,
                "sender_id": msg.sender_id,
                "receiver_id": msg.receiver_id,
                "message": msg.message,
                "attachment": msg.attachment,
                "message_type": msg.message_type,
                "is_read": msg.is_read,
                "is_delivered": msg.is_delivered,
                "is_deleted": msg.is_deleted,
                "reply_message_id": msg.reply_message_id,
                "created_at": (
                    msg.created_at.isoformat()
                    if msg.created_at
                    else None
                )
            }
        }
    )


# =========================================================
# UPDATE CHAT MESSAGE
# =========================================================

@router.put("/message/{message_id}")
def update_chat_message(
    message_id: int,
    data: ChatMessageUpdate,
    db: Session = Depends(get_db)
):

    msg = db.query(ChatMessage).filter(
        ChatMessage.id == message_id
    ).first()

    if not msg:
        return JSONResponse(
            status_code=404,
            content={
                "message": "Chat message not found"
            }
        )

    # Update message
    if data.message is not None:

        msg.message = data.message

        # Update last message in Chat
        chat = db.query(Chat).filter(
            Chat.id == msg.chat_id
        ).first()

        if chat and chat.last_message_by == msg.sender_id:
            chat.last_message = data.message

    # Update message type
    if data.message_type is not None:
        msg.message_type = data.message_type

    # Update attachment
    if hasattr(data, "attachment") and data.attachment is not None:
        msg.attachment = data.attachment

    # Update read status
    if data.is_read is not None:
        msg.is_read = data.is_read

    # Update delivered status
    if data.is_delivered is not None:
        msg.is_delivered = data.is_delivered

    # Update deleted status
    if hasattr(data, "is_deleted") and data.is_deleted is not None:
        msg.is_deleted = data.is_deleted

    # Update reply message
    if hasattr(data, "reply_message_id") and data.reply_message_id is not None:
        msg.reply_message_id = data.reply_message_id

    db.commit()
    db.refresh(msg)

    return JSONResponse(
        status_code=200,
        content={
            "message": "Chat message updated successfully",
            "data": {
                "id": msg.id,
                "chat_id": msg.chat_id,
                "sender_id": msg.sender_id,
                "receiver_id": msg.receiver_id,
                "message": msg.message,
                "attachment": msg.attachment,
                "message_type": msg.message_type,
                "is_read": msg.is_read,
                "is_delivered": msg.is_delivered,
                "is_deleted": msg.is_deleted,
                "reply_message_id": msg.reply_message_id,
                "created_at": (
                    msg.created_at.isoformat()
                    if msg.created_at
                    else None
                )
            }
        }
    )


# =========================================================
# DELETE CHAT MESSAGE
# =========================================================

@router.delete("/message/{message_id}")
def delete_chat_message(
    message_id: int,
    db: Session = Depends(get_db)
):

    msg = db.query(ChatMessage).filter(
        ChatMessage.id == message_id
    ).first()

    if not msg:
        return JSONResponse(
            status_code=404,
            content={
                "message": "Chat message not found"
            }
        )

    db.delete(msg)
    db.commit()

    return JSONResponse(
        status_code=200,
        content={
            "message": "Chat message deleted successfully"
        }
    )