
from datetime import datetime, timedelta, timezone, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models.game_details import GameSetting, GamePaymentDetail, GamePlay
from models.users import User
from models.state import State


router = APIRouter(prefix="/admin/games", tags=["Admin Games"])

ALLOWED_GAMES = {"Colour Connect", "Scratch Game"}


# -------------------- SCHEMAS --------------------

class GameSettingCreate(BaseModel):
    name: str
    status: bool = True
    entry_fees: int = Field(default=0, ge=0)
    rewards: int = Field(default=0, ge=0)
    daily_play_limit: int = Field(default=3, ge=1)


class CreateGamesRequest(BaseModel):
    games: List[GameSettingCreate]


class GameSettingUpdate(BaseModel):
    id: int
    status: Optional[bool] = None
    entry_fees: Optional[int] = Field(default=None, ge=0)
    rewards: Optional[int] = Field(default=None, ge=0)
    daily_play_limit: Optional[int] = Field(default=None, ge=1)


class UpdateGamesRequest(BaseModel):
    games: List[GameSettingUpdate]


# -------------------- HELPER FUNCTIONS --------------------

def get_user_name(user):
    return (
        getattr(user, "display_name", None)
        or getattr(user, "name", None)
        or f"User {user.id}"
    )


def get_user_state(user, db: Session):
    if not getattr(user, "state_id", None):
        return None

    state_name = (
        db.query(State.state_name)
        .filter(State.id == user.state_id)
        .scalar()
    )

    return state_name


def get_game_stats(db: Session, game: GameSetting, start_date: datetime):
    entries = (
        db.query(func.count(GamePlay.id))
        .filter(
            GamePlay.game_id == game.id,
            GamePlay.created_at >= start_date,
        )
        .scalar()
        or 0
    )

    revenue = (
        db.query(func.coalesce(func.sum(GamePaymentDetail.paid), 0))
        .filter(
            GamePaymentDetail.game_id == game.id,
            GamePaymentDetail.status == "success",
            GamePaymentDetail.paid_date >= start_date,
        )
        .scalar()
        or 0
    )

    winners = (
        db.query(func.count(GamePlay.id))
        .filter(
            GamePlay.game_id == game.id,
            GamePlay.status == "won",
            GamePlay.created_at >= start_date,
        )
        .scalar()
        or 0
    )

    rewards_paid = (
        db.query(func.coalesce(func.sum(GamePlay.prize_coins), 0))
        .filter(
            GamePlay.game_id == game.id,
            GamePlay.status == "won",
            GamePlay.created_at >= start_date,
        )
        .scalar()
        or 0
    )

    active_players = (
        db.query(func.count(func.distinct(GamePlay.user_id)))
        .filter(
            GamePlay.game_id == game.id,
            GamePlay.status == "started",
            GamePlay.created_at >= start_date,
        )
        .scalar()
        or 0
    )

    return {
        "game_id": game.id,
        "game_name": game.name,
        "entries": entries,
        "revenue": int(revenue),
        "winners": winners,
        "rewards_paid": int(rewards_paid),
        "profit": int(revenue) - int(rewards_paid),
        "active_players": active_players,
    }


# -------------------- 1. GET DASHBOARD --------------------

@router.get("/dashboard", status_code=status.HTTP_200_OK)
def get_games_dashboard(db: Session = Depends(get_db)):
    games = db.query(GameSetting).order_by(GameSetting.id.asc()).all()

    if not games:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No game settings found",
        )

    today_start = datetime.combine(
        date.today(), datetime.min.time()
    ).replace(tzinfo=timezone.utc)

    seven_days_ago = today_start - timedelta(days=6)

    # All-time game totals
    total_entries = (
        db.query(func.count(GamePlay.id)).scalar() or 0
    )

    total_revenue = (
        db.query(func.coalesce(func.sum(GamePaymentDetail.paid), 0))
        .filter(GamePaymentDetail.status == "success")
        .scalar()
        or 0
    )

    total_rewards = (
        db.query(func.coalesce(func.sum(GamePlay.prize_coins), 0))
        .filter(GamePlay.status == "won")
        .scalar()
        or 0
    )

    players_today = (
        db.query(func.count(func.distinct(GamePlay.user_id)))
        .filter(GamePlay.created_at >= today_start)
        .scalar()
        or 0
    )

    active_players = (
        db.query(func.count(func.distinct(GamePlay.user_id)))
        .filter(GamePlay.status == "started")
        .scalar()
        or 0
    )

    # Settings for both games
    game_settings = [
        {
            "id": game.id,
            "name": game.name,
            "status": game.status,
            "entry_fees": game.entry_fees,
            "rewards": game.rewards,
            "daily_play_limit": game.daily_play_limit,
            "created_at": game.created_at,
            "updated_at": game.updated_at,
        }
        for game in games
    ]

    # Per-game analytics
    game_analytics = [
        get_game_stats(db, game, seven_days_ago)
        for game in games
    ]

    # Last 7 days charts
    daily_revenue = []
    participation = []
    profit_trend = []

    for offset in range(6, -1, -1):
        chart_date = date.today() - timedelta(days=offset)

        day_start = datetime.combine(
            chart_date, datetime.min.time()
        ).replace(tzinfo=timezone.utc)

        day_end = day_start + timedelta(days=1)

        revenue = (
            db.query(func.coalesce(func.sum(GamePaymentDetail.paid), 0))
            .filter(
                GamePaymentDetail.status == "success",
                GamePaymentDetail.paid_date >= day_start,
                GamePaymentDetail.paid_date < day_end,
            )
            .scalar()
            or 0
        )

        rewards = (
            db.query(func.coalesce(func.sum(GamePlay.prize_coins), 0))
            .filter(
                GamePlay.status == "won",
                GamePlay.created_at >= day_start,
                GamePlay.created_at < day_end,
            )
            .scalar()
            or 0
        )

        entries = (
            db.query(func.count(GamePlay.id))
            .filter(
                GamePlay.created_at >= day_start,
                GamePlay.created_at < day_end,
            )
            .scalar()
            or 0
        )

        daily_revenue.append({
            "date": chart_date.isoformat(),
            "revenue": int(revenue),
        })

        participation.append({
            "date": chart_date.isoformat(),
            "entries": entries,
        })

        profit_trend.append({
            "date": chart_date.isoformat(),
            "profit": int(revenue) - int(rewards),
        })

    # Top 10 leaderboard based on wins and rewards
    leaderboard_rows = (
        db.query(
            GamePlay.user_id,
            func.count(GamePlay.id).label("wins"),
            func.coalesce(
                func.sum(GamePlay.prize_coins), 0
            ).label("earnings"),
        )
        .filter(GamePlay.status == "won")
        .group_by(GamePlay.user_id)
        .order_by(
            func.count(GamePlay.id).desc(),
            func.coalesce(
                func.sum(GamePlay.prize_coins), 0
            ).desc(),
        )
        .limit(10)
        .all()
    )

    leaderboard = []

    for rank, row in enumerate(leaderboard_rows, start=1):
        user = (
            db.query(User)
            .filter(User.id == row.user_id)
            .first()
        )

        if not user:
            continue

        # Get state name using user's state_id
        state_name = get_user_state(user, db)

        leaderboard.append({
            "rank": rank,
            "user_id": row.user_id,
            "user": get_user_name(user),
            "wins": row.wins,
            "earnings": int(row.earnings),
            "state": state_name,
        })

    return {
        "overview": {
            "players_today": players_today,
            "game_entries": total_entries,
            "revenue": int(total_revenue),
            "rewards_paid": int(total_rewards),
            "profit": int(total_revenue) - int(total_rewards),
            "active_players": active_players,
        },
        "game_settings": game_settings,
        "game_analytics": game_analytics,
        "charts": {
            "daily_game_revenue": daily_revenue,
            "user_participation": participation,
            "profit_trend": profit_trend,
        },
        "leaderboard": leaderboard,
    }


# -------------------- 2. CREATE GAME SETTINGS --------------------

@router.post(
    "/settings",
    status_code=status.HTTP_201_CREATED,
)
def create_game_settings(
    payload: CreateGamesRequest,
    db: Session = Depends(get_db),
):
    if not payload.games:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one game is required",
        )

    requested_names = []

    for item in payload.games:
        name = item.name.strip()

        if name not in ALLOWED_GAMES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid game name: {name}",
            )

        if name in requested_names:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Duplicate game name in request: {name}",
            )

        requested_names.append(name)

        existing = (
            db.query(GameSetting)
            .filter(GameSetting.name == name)
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{name} already exists",
            )

    created_games = []

    try:
        for item in payload.games:
            game = GameSetting(
                name=item.name.strip(),
                status=item.status,
                entry_fees=item.entry_fees,
                rewards=item.rewards,
                daily_play_limit=item.daily_play_limit,
            )

            db.add(game)
            created_games.append(game)

        db.commit()

        for game in created_games:
            db.refresh(game)

        return {
            "message": "Game settings created successfully",
            "games": [
                {
                    "id": game.id,
                    "name": game.name,
                    "status": game.status,
                    "entry_fees": game.entry_fees,
                    "rewards": game.rewards,
                    "daily_play_limit": game.daily_play_limit,
                }
                for game in created_games
            ],
        }

    except Exception:
        db.rollback()
        raise


# -------------------- 3. UPDATE GAME SETTINGS --------------------

@router.put("/settings", status_code=status.HTTP_200_OK)
def update_game_settings(
    payload: UpdateGamesRequest,
    db: Session = Depends(get_db),
):
    if not payload.games:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one game setting is required",
        )

    ids = [item.id for item in payload.games]

    if len(ids) != len(set(ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate game IDs in request",
        )

    games_to_update = {}

    for item in payload.games:
        game = (
            db.query(GameSetting)
            .filter(GameSetting.id == item.id)
            .first()
        )

        if not game:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Game setting not found for ID {item.id}",
            )

        games_to_update[item.id] = (game, item)

    try:
        for game, item in games_to_update.values():
            if item.status is not None:
                game.status = item.status

            if item.entry_fees is not None:
                game.entry_fees = item.entry_fees

            if item.rewards is not None:
                game.rewards = item.rewards

            if item.daily_play_limit is not None:
                game.daily_play_limit = item.daily_play_limit

        db.commit()

        response_games = []

        for game, _ in games_to_update.values():
            db.refresh(game)

            response_games.append({
                "id": game.id,
                "name": game.name,
                "status": game.status,
                "entry_fees": game.entry_fees,
                "rewards": game.rewards,
                "daily_play_limit": game.daily_play_limit,
            })

        return {
            "message": "Game settings updated successfully",
            "games": response_games,
        }

    except Exception:
        db.rollback()
        raise



