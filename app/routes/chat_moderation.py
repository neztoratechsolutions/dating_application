from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from database import get_db
from models.users import User
from models.chat_history import Chat, ChatMessage
from models.chat_report import ChatReport, ChatModerationAction


router = APIRouter(
    prefix="/admin/chat-moderation",
    tags=["Admin Chat Moderation"],
)
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# ---------------------------------------------------------
# CHAT IMAGE UPLOAD DIRECTORY
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

UPLOAD_DIR = BASE_DIR / "uploads"

CHAT_IMAGE_DIR = UPLOAD_DIR / "chat_images"

CHAT_IMAGE_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# ---------------------------------------------------------
# SERVE CHAT IMAGES
# ---------------------------------------------------------

app.mount(
    "/uploads",
    StaticFiles(directory=str(UPLOAD_DIR)),
    name="uploads"
)

# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def user_name(user):
    if not user:
        return "Unknown User"

    for field in ("display_name", "full_name", "username", "name", "email"):
        value = getattr(user, field, None)
        if value:
            return str(value)

    return f"User {user.id}"


def user_data(user):
    if not user:
        return None

    return {
        "id": user.id,
        "name": user_name(user),
        "email": getattr(user, "email", None),
    }


def get_chat(db: Session, chat_id: int):
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return chat


def get_report(db: Session, report_id: int):
    report = db.query(ChatReport).filter(ChatReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


def get_chat_users(db: Session, chat: Chat):
    user_one = db.query(User).filter(User.id == chat.user_one_id).first()
    user_two = db.query(User).filter(User.id == chat.user_two_id).first()
    return user_one, user_two


def report_data(report):
    return {
        "id": report.id,
        "chat_id": report.chat_id,
        "message_id": report.message_id,
        "reported_by": report.reported_by,
        "reason": report.reason,
        "description": report.description,
        "status": report.status,
        "is_resolved": report.is_resolved,
        "created_at": report.created_at,
        "updated_at": report.updated_at,
    }


def message_data(db: Session, message: ChatMessage):
    sender = db.query(User).filter(User.id == message.sender_id).first()
    receiver = db.query(User).filter(User.id == message.receiver_id).first()

    reports = db.query(ChatReport).filter(
        ChatReport.message_id == message.id
    ).order_by(ChatReport.created_at.desc()).all()

    message_type = message.message_type
    if hasattr(message_type, "value"):
        message_type = message_type.value

    return {
        "message_id": message.id,
        "chat_id": message.chat_id,
        "sender_id": message.sender_id,
        "sender": user_data(sender),
        "receiver_id": message.receiver_id,
        "receiver": user_data(receiver),
        "message": message.message,
        "message_type": message_type,
        "attachment": message.attachment,
        "is_read": message.is_read,
        "is_delivered": message.is_delivered,
        "is_deleted": message.is_deleted,
        "created_at": message.created_at,
        "report_count": len(reports),
        "reports": [report_data(r) for r in reports],
    }


def chat_data(db: Session, chat: Chat):
    user_one, user_two = get_chat_users(db, chat)

    message_count = db.query(func.count(ChatMessage.id)).filter(
        ChatMessage.chat_id == chat.id
    ).scalar() or 0

    pending_reports = db.query(func.count(ChatReport.id)).filter(
        ChatReport.chat_id == chat.id,
        ChatReport.is_resolved.is_(False),
    ).scalar() or 0

    last_message = db.query(ChatMessage).filter(
        ChatMessage.chat_id == chat.id
    ).order_by(
        ChatMessage.created_at.desc(),
        ChatMessage.id.desc(),
    ).first()

    return {
        "chat_id": chat.id,
        "user_one_id": chat.user_one_id,
        "user_one": user_data(user_one),
        "user_two_id": chat.user_two_id,
        "user_two": user_data(user_two),
        "last_message": chat.last_message,
        "last_message_at": chat.last_message_at,
        "last_message_by": chat.last_message_by,
        "message_count": message_count,
        "pending_report_count": pending_reports,
        "status": chat.status,
        "created_at": chat.created_at,
        "updated_at": chat.updated_at,
        "last_message_details": message_data(db, last_message) if last_message else None,
    }


def apply_search(query, db: Session, search: Optional[str]):
    if not search or not search.strip():
        return query

    term = f"%{search.strip()}%"

    # Search user email and commonly-used name columns only when present.
    user_conditions = []
    for field in ("email", "display_name", "full_name", "username", "name"):
        column = getattr(User, field, None)
        if column is not None:
            user_conditions.append(column.ilike(term))

    matching_user_ids = db.query(User.id)
    if user_conditions:
        matching_user_ids = matching_user_ids.filter(or_(*user_conditions))
    else:
        matching_user_ids = matching_user_ids.filter(User.id == -1)

    matching_chat_ids = db.query(Chat.id).filter(
        or_(
            Chat.user_one_id.in_(matching_user_ids),
            Chat.user_two_id.in_(matching_user_ids),
        )
    )

    matching_message_chat_ids = db.query(ChatMessage.chat_id).filter(
        ChatMessage.message.ilike(term)
    )

    # Chat id exact/partial numeric search.
    if search.strip().isdigit():
        matching_chat_ids = matching_chat_ids.union(
            db.query(Chat.id).filter(Chat.id == int(search.strip()))
        )

    return query.filter(
        or_(
            Chat.id.in_(matching_chat_ids),
            Chat.id.in_(matching_message_chat_ids),
        )
    )


def create_action(
    db: Session,
    chat: Chat,
    user_id: int,
    admin_id: int,
    action: str,
    reason: Optional[str] = None,
    duration: Optional[int] = None,
):
    # admin_id is explicitly supplied because this router has no authentication.
    admin = db.query(User).filter(User.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin user not found")

    if user_id not in (chat.user_one_id, chat.user_two_id):
        raise HTTPException(
            status_code=400,
            detail="Target user is not part of this conversation",
        )

    record = ChatModerationAction(
        chat_id=chat.id,
        user_id=user_id,
        admin_id=admin_id,
        action=action,
        reason=reason,
        duration=duration,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def action_data(action):
    return {
        "id": action.id,
        "chat_id": action.chat_id,
        "user_id": action.user_id,
        "admin_id": action.admin_id,
        "action": action.action,
        "reason": action.reason,
        "duration": action.duration,
        "created_at": action.created_at,
    }


# ---------------------------------------------------------
# Dashboard
# GET /admin/chat-moderation/dashboard
# ---------------------------------------------------------

@router.get("/dashboard")
def moderation_dashboard(db: Session = Depends(get_db)):
    total_chats = db.query(func.count(Chat.id)).scalar() or 0

    active_chats = db.query(func.count(Chat.id)).filter(
        Chat.status.is_(True)
    ).scalar() or 0

    total_reports = db.query(func.count(ChatReport.id)).scalar() or 0

    pending_reports = db.query(func.count(ChatReport.id)).filter(
        ChatReport.is_resolved.is_(False)
    ).scalar() or 0

    flagged_messages = db.query(
        func.count(func.distinct(ChatReport.message_id))
    ).filter(
        ChatReport.is_resolved.is_(False),
        ChatReport.message_id.isnot(None),
    ).scalar() or 0

    return {
        "status_code": 200,
        "message": "Moderation dashboard fetched successfully",
        "data": {
            "total_conversations": total_chats,
            "active_conversations": active_chats,
            "total_reports": total_reports,
            "pending_reports": pending_reports,
            "flagged_messages": flagged_messages,
        },
    }


# ---------------------------------------------------------
# Conversation list
# GET /admin/chat-moderation
# ---------------------------------------------------------

@router.get("")
def get_conversations(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None, description="all, active, inactive"),
    filter_type: Optional[str] = Query(None, description="all, reported, flagged"),
    report_status: Optional[str] = Query(None, description="pending, resolved"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Chat)

    if status == "active":
        query = query.filter(Chat.status.is_(True))
    elif status == "inactive":
        query = query.filter(Chat.status.is_(False))
    elif status not in (None, "", "all"):
        raise HTTPException(status_code=400, detail="Invalid status filter")

    if start_date:
        query = query.filter(Chat.created_at >= start_date)
    if end_date:
        query = query.filter(Chat.created_at <= end_date)

    query = apply_search(query, db, search)

    if filter_type == "reported":
        report_query = db.query(ChatReport.chat_id)
        if report_status == "pending":
            report_query = report_query.filter(ChatReport.is_resolved.is_(False))
        elif report_status == "resolved":
            report_query = report_query.filter(ChatReport.is_resolved.is_(True))
        query = query.filter(Chat.id.in_(report_query))
    elif filter_type == "flagged":
        flagged_chat_ids = db.query(ChatReport.chat_id).filter(
            ChatReport.is_resolved.is_(False),
            ChatReport.message_id.isnot(None),
        )
        query = query.filter(Chat.id.in_(flagged_chat_ids))
    elif filter_type not in (None, "", "all"):
        raise HTTPException(status_code=400, detail="Invalid filter_type")

    total = query.count()

    chats = query.order_by(
        Chat.updated_at.desc(),
        Chat.id.desc(),
    ).offset(
        (page - 1) * limit
    ).limit(limit).all()

    return {
        "status_code": 200,
        "message": "Conversations fetched successfully",
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit,
        },
        "data": [chat_data(db, chat) for chat in chats],
    }


# ---------------------------------------------------------
# Conversation detail
# GET /admin/chat-moderation/{chat_id}
# ---------------------------------------------------------

@router.get("/{chat_id}")
def get_conversation_details(
    chat_id: int,
    db: Session = Depends(get_db),
):
    chat = get_chat(db, chat_id)
    return {
        "status_code": 200,
        "message": "Conversation details fetched successfully",
        "data": chat_data(db, chat),
    }


# ---------------------------------------------------------
# Conversation messages
# GET /admin/chat-moderation/{chat_id}/messages
# ---------------------------------------------------------

@router.get("/{chat_id}/messages")
def get_conversation_messages(
    chat_id: int,
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    get_chat(db, chat_id)

    query = db.query(ChatMessage).filter(ChatMessage.chat_id == chat_id)
    if search and search.strip():
        query = query.filter(ChatMessage.message.ilike(f"%{search.strip()}%"))

    total = query.count()
    messages = query.order_by(
        ChatMessage.created_at.asc(),
        ChatMessage.id.asc(),
    ).offset((page - 1) * limit).limit(limit).all()

    return {
        "status_code": 200,
        "message": "Messages fetched successfully",
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit,
        },
        "data": [message_data(db, message) for message in messages],
    }


# ---------------------------------------------------------
# Reports
# GET /admin/chat-moderation/reports/list
# ---------------------------------------------------------

@router.get("/reports/list")
def get_reports(
    status: Optional[str] = Query(None, description="pending, resolved"),
    chat_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(ChatReport)

    if status == "pending":
        query = query.filter(ChatReport.is_resolved.is_(False))
    elif status == "resolved":
        query = query.filter(ChatReport.is_resolved.is_(True))
    elif status not in (None, "", "all"):
        raise HTTPException(status_code=400, detail="Invalid report status")

    if chat_id is not None:
        query = query.filter(ChatReport.chat_id == chat_id)

    total = query.count()
    reports = query.order_by(
        ChatReport.created_at.desc(),
        ChatReport.id.desc(),
    ).offset((page - 1) * limit).limit(limit).all()

    return {
        "status_code": 200,
        "message": "Reports fetched successfully",
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit,
        },
        "data": [report_data(report) for report in reports],
    }


# ---------------------------------------------------------
# Resolve report
# POST /admin/chat-moderation/reports/{report_id}/resolve
# ---------------------------------------------------------

@router.post("/reports/{report_id}/resolve")
def resolve_report(
    report_id: int,
    db: Session = Depends(get_db),
):
    report = get_report(db, report_id)
    report.is_resolved = True
    report.status = "resolved"
    report.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(report)

    return {
        "status_code": 200,
        "message": "Report resolved successfully",
        "data": report_data(report),
    }


# ---------------------------------------------------------
# Warn user
# POST /admin/chat-moderation/{chat_id}/warn
# ---------------------------------------------------------

@router.post("/{chat_id}/warn")
def warn_user(
    chat_id: int,
    user_id: int = Query(...),
    admin_id: int = Query(...),
    reason: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    chat = get_chat(db, chat_id)
    action = create_action(
        db=db,
        chat=chat,
        user_id=user_id,
        admin_id=admin_id,
        action="warn",
        reason=reason,
    )
    return {
        "status_code": 200,
        "message": "Warning recorded successfully",
        "data": action_data(action),
    }


# ---------------------------------------------------------
# Suspend user
# POST /admin/chat-moderation/{chat_id}/suspend
# duration is minutes
# ---------------------------------------------------------

@router.post("/{chat_id}/suspend")
def suspend_user(
    chat_id: int,
    user_id: int = Query(...),
    admin_id: int = Query(...),
    duration: int = Query(..., ge=1),
    reason: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    chat = get_chat(db, chat_id)
    action = create_action(
        db=db,
        chat=chat,
        user_id=user_id,
        admin_id=admin_id,
        action="suspend",
        reason=reason,
        duration=duration,
    )
    return {
        "status_code": 200,
        "message": "Suspension action recorded successfully",
        "data": action_data(action),
    }


# ---------------------------------------------------------
# Ban user
# POST /admin/chat-moderation/{chat_id}/ban
# ---------------------------------------------------------

@router.post("/{chat_id}/ban")
def ban_user(
    chat_id: int,
    user_id: int = Query(...),
    admin_id: int = Query(...),
    reason: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    chat = get_chat(db, chat_id)
    action = create_action(
        db=db,
        chat=chat,
        user_id=user_id,
        admin_id=admin_id,
        action="ban",
        reason=reason,
    )
    return {
        "status_code": 200,
        "message": "Ban action recorded successfully",
        "data": action_data(action),
    }

@router.get("/{chat_id}/actions")
def get_moderation_history(
    chat_id: int,
    db: Session = Depends(get_db),
):
    get_chat(db, chat_id)

    actions = db.query(ChatModerationAction).filter(
        ChatModerationAction.chat_id == chat_id
    ).order_by(
        ChatModerationAction.created_at.desc(),
        ChatModerationAction.id.desc(),
    ).all()

    return {
        "status_code": 200,
        "message": "Moderation history fetched successfully",
        "data": [action_data(action) for action in actions],
    }
