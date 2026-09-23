from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database import get_db
from models.chat_history import Chat
from models.chat_history import ChatMessage
from models.users import User
from schemas.chat import ChatCreate, ChatUpdate


router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


# ==========================================================
# CREATE CHAT
# ==========================================================

@router.post("/create")
def create_chat(
    data: ChatCreate,
    db: Session = Depends(get_db)
):

    # Check user one
    user_one = (
        db.query(User)
        .filter(User.id == data.user_one_id)
        .first()
    )

    if not user_one:
        return JSONResponse(
            status_code=404,
            content={
                "message": "User one not found",
                "user_id": data.user_one_id
            }
        )

    # Check user two
    user_two = (
        db.query(User)
        .filter(User.id == data.user_two_id)
        .first()
    )

    if not user_two:
        return JSONResponse(
            status_code=404,
            content={
                "message": "User two not found",
                "user_id": data.user_two_id
            }
        )

    # Prevent same user chatting with themselves
    if data.user_one_id == data.user_two_id:
        return JSONResponse(
            status_code=400,
            content={
                "message": "User cannot create chat with themselves"
            }
        )

    # Check existing chat
    existing_chat = (
        db.query(Chat)
        .filter(
            (
                (Chat.user_one_id == data.user_one_id) &
                (Chat.user_two_id == data.user_two_id)
            )
            |
            (
                (Chat.user_one_id == data.user_two_id) &
                (Chat.user_two_id == data.user_one_id)
            )
        )
        .first()
    )

    if existing_chat:
        return JSONResponse(
            status_code=200,
            content={
                "message": "Chat already exists",
                "chat_id": existing_chat.id
            }
        )

    # Create chat
    chat = Chat(
        user_one_id=data.user_one_id,
        user_two_id=data.user_two_id,
        unread_count_user1=0,
        unread_count_user2=0,
        status=True
    )

    db.add(chat)
    db.commit()
    db.refresh(chat)

    return JSONResponse(
        status_code=201,
        content={
            "message": "Chat created successfully",
            "data": {
                "id": chat.id,
                "user_one_id": chat.user_one_id,
                "user_two_id": chat.user_two_id,
                "status": chat.status
            }
        }
    )


# ==========================================================
# GET ALL CHATS
# ==========================================================

@router.get("/all")
def get_all_chats(
    db: Session = Depends(get_db)
):

    chats = db.query(Chat).order_by(
        Chat.created_at.desc()
    ).all()

    if not chats:
        return JSONResponse(
            status_code=404,
            content={
                "message": "No chats found"
            }
        )

    data = []

    for chat in chats:

        data.append({
            "id": chat.id,
            "user_one_id": chat.user_one_id,
            "user_two_id": chat.user_two_id,
            "last_message": chat.last_message,
            "last_message_at": (
                chat.last_message_at.isoformat()
                if chat.last_message_at
                else None
            ),
            "last_message_by": chat.last_message_by,
            "unread_count_user1": chat.unread_count_user1,
            "unread_count_user2": chat.unread_count_user2,
            "status": chat.status,
            "created_at": (
                chat.created_at.isoformat()
                if chat.created_at
                else None
            ),
            "updated_at": (
                chat.updated_at.isoformat()
                if chat.updated_at
                else None
            )
        })

    return JSONResponse(
        status_code=200,
        content={
            "message": "Chats retrieved successfully",
            "data": data
        }
    )




@router.get("/{chat_id}")
def get_chat_by_id(
    chat_id: int,
    db: Session = Depends(get_db)
):
    chat = db.query(Chat).filter(
        Chat.id == chat_id
    ).first()

    if not chat:
        return JSONResponse(
            status_code=404,
            content={
                "message": "Chat not found"
            }
        )

    return JSONResponse(
        status_code=200,
        content={
            "message": "Chat retrieved successfully",
            "data": {
                "id": chat.id,
                "user_one_id": chat.user_one_id,
                "user_two_id": chat.user_two_id,
                "last_message": chat.last_message,
                "last_message_at": (
                    chat.last_message_at.isoformat()
                    if chat.last_message_at
                    else None
                ),
                "last_message_by": chat.last_message_by,
                "unread_count_user1": chat.unread_count_user1,
                "unread_count_user2": chat.unread_count_user2,
                "status": chat.status,
                "created_at": (
                    chat.created_at.isoformat()
                    if chat.created_at
                    else None
                ),
                "updated_at": (
                    chat.updated_at.isoformat()
                    if chat.updated_at
                    else None
                )
            }
        }
    )
# ==========================================================
# UPDATE CHAT
# ==========================================================

@router.put("/{chat_id}")
def update_chat(
    chat_id: int,
    data: ChatUpdate,
    db: Session = Depends(get_db)
):

    chat = (
        db.query(Chat)
        .filter(Chat.id == chat_id)
        .first()
    )

    if not chat:
        return JSONResponse(
            status_code=404,
            content={
                "message": "Chat not found"
            }
        )

    if data.user_one_id is not None:
        chat.user_one_id = data.user_one_id

    if data.user_two_id is not None:
        chat.user_two_id = data.user_two_id

    if data.status is not None:
        chat.status = data.status

    db.commit()
    db.refresh(chat)

    return JSONResponse(
        status_code=200,
        content={
            "message": "Chat updated successfully",
            "data": {
                "id": chat.id,
                "user_one_id": chat.user_one_id,
                "user_two_id": chat.user_two_id,
                "status": chat.status
            }
        }
    )


# ==========================================================
# DELETE CHAT
# ==========================================================

@router.delete("/{chat_id}")
def delete_chat(
    chat_id: int,
    db: Session = Depends(get_db)
):

    chat = (
        db.query(Chat)
        .filter(Chat.id == chat_id)
        .first()
    )

    if not chat:
        return JSONResponse(
            status_code=404,
            content={
                "message": "Chat not found"
            }
        )

    db.delete(chat)
    db.commit()

    return JSONResponse(
        status_code=200,
        content={
            "message": "Chat deleted successfully"
        }
    )