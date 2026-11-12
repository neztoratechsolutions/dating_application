from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    Query,
    status,
)

from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from database import get_db

from models.users import User
from models.state import State

from models.live_users import LiveUserSession

from models.chat_history import (
    Chat,
    ChatMessage,
)

from models.voice_call import VoiceCall
from models.video_call import VideoCall

from models.game_details import (
    GamePlay,
    GameSetting,
)


router = APIRouter(
    prefix="/admin/live-users",
    tags=["Admin - Live Users"],
)


# =========================================================
# CONSTANTS
# =========================================================

ONLINE_TIMEOUT_MINUTES = 5
CHAT_ACTIVE_MINUTES = 5


# =========================================================
# HELPERS
# =========================================================

def get_utc_now():
    return datetime.now(timezone.utc)


def make_session_duration(
    login_at: datetime,
    now: datetime,
):

    if not login_at:
        return "0m"

    if login_at.tzinfo is None:
        login_at = login_at.replace(
            tzinfo=timezone.utc
        )

    difference = now - login_at

    total_seconds = int(
        difference.total_seconds()
    )

    if total_seconds < 0:
        total_seconds = 0

    minutes = total_seconds // 60

    hours = minutes // 60

    remaining_minutes = minutes % 60

    if hours > 0:
        return f"{hours}h {remaining_minutes}m"

    return f"{minutes}m"


def format_login_time(
    login_at: datetime,
):

    if not login_at:
        return None

    return login_at.strftime(
        "%I:%M %p"
    )


# =========================================================
# GET USER ACTIVITY
# =========================================================

def get_user_activity(
    user_id: int,
    db: Session,
):

    # -----------------------------------------------------
    # 1. VOICE CALL
    # -----------------------------------------------------

    voice_call = (
        db.query(VoiceCall)
        .filter(
            VoiceCall.status == "ongoing",
            or_(
                VoiceCall.customer_id == user_id,
                VoiceCall.creator_id == user_id,
                VoiceCall.caller_id == user_id,
                VoiceCall.receiver_id == user_id,
            ),
        )
        .order_by(
            VoiceCall.start_time.desc()
        )
        .first()
    )

    if voice_call:
        return "Voice Call"


    # -----------------------------------------------------
    # 2. VIDEO CALL
    # -----------------------------------------------------

    video_call = (
        db.query(VideoCall)
        .filter(
            VideoCall.status.in_(
                ["ringing", "ongoing"]
            ),
            or_(
                VideoCall.customer_id == user_id,
                VideoCall.creator_id == user_id,
                VideoCall.caller_id == user_id,
                VideoCall.receiver_id == user_id,
            ),
        )
        .order_by(
            VideoCall.start_time.desc()
        )
        .first()
    )

    if video_call:
        return "Video Call"


    # -----------------------------------------------------
    # 3. GAME
    # -----------------------------------------------------

    game_play = (
        db.query(GamePlay)
        .filter(
            GamePlay.user_id == user_id,
            GamePlay.status == "started",
        )
        .order_by(
            GamePlay.started_at.desc()
        )
        .first()
    )

    if game_play:
        return "Playing Game"


    # -----------------------------------------------------
    # 4. CHAT
    # -----------------------------------------------------

    chat_cutoff = (
        get_utc_now()
        - timedelta(minutes=CHAT_ACTIVE_MINUTES)
    )

    recent_message = (
        db.query(ChatMessage)
        .filter(
            or_(
                ChatMessage.sender_id == user_id,
                ChatMessage.receiver_id == user_id,
            ),
            ChatMessage.created_at >= chat_cutoff,
            ChatMessage.is_deleted == False,
        )
        .order_by(
            ChatMessage.created_at.desc()
        )
        .first()
    )

    if recent_message:
        return "Chatting"


    # -----------------------------------------------------
    # 5. DEFAULT
    # -----------------------------------------------------

    return "Browsing"


# =========================================================
# GET ACTIVE VOICE COUNT
# =========================================================

def get_active_voice_count(
    db: Session,
):

    return (
        db.query(
            func.count(VoiceCall.id)
        )
        .filter(
            VoiceCall.status == "ongoing"
        )
        .scalar()
        or 0
    )


# =========================================================
# GET ACTIVE VIDEO COUNT
# =========================================================

def get_active_video_count(
    db: Session,
):

    return (
        db.query(
            func.count(VideoCall.id)
        )
        .filter(
            VideoCall.status.in_(
                ["ringing", "ongoing"]
            )
        )
        .scalar()
        or 0
    )


# =========================================================
# GET ACTIVE GAME COUNT
# =========================================================

def get_active_game_count(
    db: Session,
):

    return (
        db.query(
            func.count(GamePlay.id)
        )
        .filter(
            GamePlay.status == "started"
        )
        .scalar()
        or 0
    )


# =========================================================
# GET ACTIVE CHAT COUNT
# =========================================================

def get_active_chat_count(
    db: Session,
):

    cutoff = (
        get_utc_now()
        - timedelta(minutes=CHAT_ACTIVE_MINUTES)
    )

    return (
        db.query(
            func.count(
                func.distinct(ChatMessage.chat_id)
            )
        )
        .filter(
            ChatMessage.created_at >= cutoff,
            ChatMessage.is_deleted == False,
        )
        .scalar()
        or 0
    )


# =========================================================
# GET LIVE USERS
# =========================================================

@router.get(
    "/",
    status_code=status.HTTP_200_OK,
)
def get_live_users(

    search: Optional[str] = Query(
        None,
        description=(
            "Search by name, email, phone "
            "or creator ID"
        ),
    ),

    role: Optional[str] = Query(
        None,
        description="customer / creator",
    ),

    state_id: Optional[int] = Query(
        None,
        description="Filter by state ID",
    ),

    activity: Optional[str] = Query(
        None,
        description=(
            "Browsing / Chatting / Voice Call / "
            "Video Call / Playing Game"
        ),
    ),

    page: int = Query(
        1,
        ge=1,
    ),

    limit: int = Query(
        20,
        ge=1,
        le=100,
    ),

    db: Session = Depends(get_db),
):

    now = get_utc_now()

    online_cutoff = (
        now
        - timedelta(
            minutes=ONLINE_TIMEOUT_MINUTES
        )
    )


    # =====================================================
    # BASE QUERY
    # =====================================================

    query = (
        db.query(
            LiveUserSession,
            User,
            State,
        )
        .join(
            User,
            User.id ==
            LiveUserSession.user_id,
        )
        .outerjoin(
            State,
            State.id ==
            User.state_id,
        )
        .filter(
            LiveUserSession.is_online == True,
            LiveUserSession.last_activity_at
            >= online_cutoff,
        )
    )


    # =====================================================
    # ROLE FILTER
    # =====================================================

    if role:

        query = query.filter(
            User.role == role
        )


    # =====================================================
    # STATE FILTER
    # =====================================================

    if state_id:

        query = query.filter(
            User.state_id == state_id
        )


    # =====================================================
    # SEARCH
    # =====================================================

    if search:

        search_value = (
            f"%{search.strip()}%"
        )

        query = query.filter(
            or_(
                User.display_name.ilike(
                    search_value
                ),

                User.email.ilike(
                    search_value
                ),

                User.phone.ilike(
                    search_value
                ),

                User.referral_code.ilike(
                    search_value
                ),
            )
        )


    # =====================================================
    # GET USERS
    # =====================================================

    rows = (
        query
        .order_by(
            LiveUserSession.last_activity_at.desc()
        )
        .all()
    )


    data = []


    # =====================================================
    # BUILD USER DATA
    # =====================================================

    for (
        live_session,
        user,
        state,
    ) in rows:

        current_activity = get_user_activity(
            user.id,
            db,
        )


        # -------------------------------------------------
        # ACTIVITY FILTER
        # -------------------------------------------------

        if activity:

            if (
                current_activity.lower()
                != activity.lower()
            ):
                continue


        data.append({

            "user_id":
                user.id,

            "name":
                user.display_name,

            "email":
                user.email,

            "phone":
                user.phone,

            "creator_id": (
                f"VLR{10000 + user.id}"
                if user.role == "creator"
                else None
            ),

            "role":
                user.role,

            "state": (
                state.state_name
                if state
                else None
            ),

            "activity":
                current_activity,

            "device": (
                live_session.device
                or "Unknown"
            ),

            "login_time":
                format_login_time(
                    live_session.login_at
                ),

            "session_duration":
                make_session_duration(
                    live_session.login_at,
                    now,
                ),

            "is_online":
                True,

            "last_activity_at":
                live_session.last_activity_at,
        })


    # =====================================================
    # PAGINATION
    # =====================================================

    total = len(data)

    start = (
        page - 1
    ) * limit

    end = start + limit

    paginated_data = data[
        start:end
    ]

    total_pages = (
        (total + limit - 1)
        // limit
        if total
        else 0
    )


    # =====================================================
    # LIVE CUSTOMER / CREATOR
    # =====================================================

    live_customers = sum(
        1
        for item in data
        if item["role"] == "customer"
    )

    live_creators = sum(
        1
        for item in data
        if item["role"] == "creator"
    )


    # =====================================================
    # IMPORTANT:
    # ACTIVE COUNTS ARE CALCULATED DIRECTLY
    # FROM ACTIVITY TABLES
    # =====================================================

    active_chats = (
        get_active_chat_count(db)
    )

    active_voice = (
        get_active_voice_count(db)
    )

    active_video = (
        get_active_video_count(db)
    )

    active_games = (
        get_active_game_count(db)
    )


    return {

        "status_code":
            200,

        "message":
            "Live users fetched successfully",

        "summary": {

            "live_customers":
                live_customers,

            "live_creators":
                live_creators,

            "active_chats":
                active_chats,

            "active_voice":
                active_voice,

            "active_video":
                active_video,

            "active_games":
                active_games,
        },

        "pagination": {

            "page":
                page,

            "limit":
                limit,

            "total":
                total,

            "total_pages":
                total_pages,
        },

        "data":
            paginated_data,
    }


# =========================================================
# ACTIVE USERS BY STATE
# =========================================================

@router.get(
    "/by-state",
    status_code=status.HTTP_200_OK,
)
def get_active_users_by_state(
    db: Session = Depends(get_db),
):

    now = get_utc_now()

    online_cutoff = (
        now
        - timedelta(
            minutes=ONLINE_TIMEOUT_MINUTES
        )
    )


    rows = (
        db.query(
            State.state_name,
            func.count(
                func.distinct(
                    LiveUserSession.user_id
                )
            ),
        )
        .join(
            User,
            User.state_id ==
            State.id,
        )
        .join(
            LiveUserSession,
            LiveUserSession.user_id ==
            User.id,
        )
        .filter(
            LiveUserSession.is_online == True,

            LiveUserSession.last_activity_at
            >= online_cutoff,
        )
        .group_by(
            State.id,
            State.state_name,
        )
        .order_by(
            func.count(
                func.distinct(
                    LiveUserSession.user_id
                )
            ).desc()
        )
        .all()
    )


    data = []

    for state_name, count in rows:

        data.append({

            "state":
                state_name,

            "active_users":
                count,
        })


    return {

        "status_code":
            200,

        "message":
            "Active users by state fetched successfully",

        "data":
            data,
    }


# =========================================================
# REAL-TIME FEED
# =========================================================

@router.get(
    "/feed",
    status_code=status.HTTP_200_OK,
)
def get_real_time_feed(

    limit: int = Query(
        20,
        ge=1,
        le=100,
    ),

    db: Session = Depends(get_db),
):

    now = get_utc_now()

    feed_cutoff = (
        now
        - timedelta(minutes=5)
    )

    feed = []


    # =====================================================
    # LOGIN EVENTS
    # =====================================================

    sessions = (
        db.query(
            LiveUserSession
        )
        .filter(
            LiveUserSession.login_at
            >= feed_cutoff
        )
        .order_by(
            LiveUserSession.login_at.desc()
        )
        .limit(
            limit
        )
        .all()
    )


    for session in sessions:

        user = (
            db.query(User)
            .filter(
                User.id ==
                session.user_id
            )
            .first()
        )

        if user:

            feed.append({

                "event":
                    "User Login",

                "user_id":
                    user.id,

                "user_name":
                    user.display_name,

                "role":
                    user.role,

                "activity":
                    "Browsing",

                "timestamp":
                    session.login_at,
            })


    # =====================================================
    # VOICE CALL EVENTS
    # =====================================================

    voice_calls = (
        db.query(
            VoiceCall
        )
        .filter(
            VoiceCall.start_time
            >= feed_cutoff
        )
        .order_by(
            VoiceCall.start_time.desc()
        )
        .limit(
            limit
        )
        .all()
    )


    for call in voice_calls:

        if call.status in [
            "ongoing",
            "completed",
        ]:

            user_id = (
                call.caller_id
                or call.customer_id
            )

            user = (
                db.query(User)
                .filter(
                    User.id ==
                    user_id
                )
                .first()
            )

            if user:

                feed.append({

                    "event":
                        "Started Voice Call",

                    "user_id":
                        user.id,

                    "user_name":
                        user.display_name,

                    "role":
                        user.role,

                    "activity":
                        "Voice Call",

                    "timestamp":
                        call.start_time,
                })


    # =====================================================
    # VIDEO CALL EVENTS
    # =====================================================

    video_calls = (
        db.query(
            VideoCall
        )
        .filter(
            VideoCall.start_time
            >= feed_cutoff
        )
        .order_by(
            VideoCall.start_time.desc()
        )
        .limit(
            limit
        )
        .all()
    )


    for call in video_calls:

        if call.status in [
            "ringing",
            "ongoing",
            "completed",
        ]:

            user_id = (
                call.caller_id
                or call.customer_id
            )

            user = (
                db.query(User)
                .filter(
                    User.id ==
                    user_id
                )
                .first()
            )

            if user:

                feed.append({

                    "event":
                        "Started Video Call",

                    "user_id":
                        user.id,

                    "user_name":
                        user.display_name,

                    "role":
                        user.role,

                    "activity":
                        "Video Call",

                    "timestamp":
                        call.start_time,
                })


    # =====================================================
    # GAME EVENTS
    # =====================================================

    game_plays = (
        db.query(
            GamePlay,
            GameSetting,
        )
        .join(
            GameSetting,
            GameSetting.id ==
            GamePlay.game_id,
        )
        .filter(
            GamePlay.started_at
            >= feed_cutoff
        )
        .order_by(
            GamePlay.started_at.desc()
        )
        .limit(
            limit
        )
        .all()
    )


    for (
        game_play,
        game_setting,
    ) in game_plays:

        user = (
            db.query(User)
            .filter(
                User.id ==
                game_play.user_id
            )
            .first()
        )

        if user:

            feed.append({

                "event":
                    "Joined Game",

                "user_id":
                    user.id,

                "user_name":
                    user.display_name,

                "role":
                    user.role,

                "activity":
                    "Playing Game",

                "game":
                    game_setting.name,

                "timestamp":
                    game_play.started_at,
            })


    # =====================================================
    # CHAT EVENTS
    # =====================================================

    messages = (
        db.query(
            ChatMessage
        )
        .filter(
            ChatMessage.created_at
            >= feed_cutoff,

            ChatMessage.is_deleted == False,
        )
        .order_by(
            ChatMessage.created_at.desc()
        )
        .limit(
            limit
        )
        .all()
    )


    for message in messages:

        user = (
            db.query(User)
            .filter(
                User.id ==
                message.sender_id
            )
            .first()
        )

        if user:

            feed.append({

                "event":
                    "Started Chat",

                "user_id":
                    user.id,

                "user_name":
                    user.display_name,

                "role":
                    user.role,

                "activity":
                    "Chatting",

                "timestamp":
                    message.created_at,
            })


    # =====================================================
    # SORT ALL EVENTS
    # =====================================================

    feed.sort(
        key=lambda item: (
            item["timestamp"]
            or datetime.min.replace(
                tzinfo=timezone.utc
            )
        ),
        reverse=True,
    )


    feed = feed[:limit]


    return {

        "status_code":
            200,

        "message":
            "Real-time feed fetched successfully",

        "data":
            feed,
    }