
import random
import secrets
from datetime import datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.game_details import GameSetting, GamePaymentDetail, GamePlay
from models.wallet import Wallet


router = APIRouter(
    prefix="/games",
    tags=["Games"],
)


# =========================================================
# CONSTANTS
# =========================================================

COLOR_GAME = "Colour Connect"
SCRATCH_GAME = "Scratch Game"

COLORS = [
    "red",
    "blue",
    "green",
    "yellow",
    "purple",
    "orange",
]


# =========================================================
# REQUEST SCHEMAS
# =========================================================

class GameStartRequest(BaseModel):
    user_id: int = Field(gt=0)


class MatchDotsRequest(BaseModel):
    user_id: int = Field(gt=0)
    game_play_id: int = Field(gt=0)
    dot_ids: list[str] = Field(min_length=3, max_length=3)


class GamePlayRequest(BaseModel):
    user_id: int = Field(gt=0)
    game_play_id: int = Field(gt=0)


# =========================================================
# HELPERS
# =========================================================

def get_game_setting(db: Session, game_name: str):
    game = db.query(GameSetting).filter(
        GameSetting.name == game_name
    ).first()

    if not game:
        raise HTTPException(
            status_code=404,
            detail=f"{game_name} settings not found. Configure it in admin settings.",
        )

    if not game.status:
        raise HTTPException(
            status_code=400,
            detail=f"{game_name} is currently disabled",
        )

    return game


def get_wallet_for_update(db: Session, user_id: int):
    wallet = db.query(Wallet).filter(
        Wallet.user_id == user_id
    ).with_for_update().first()

    if not wallet:
        raise HTTPException(
            status_code=404,
            detail="Wallet not found for this user",
        )

    return wallet


def get_play_for_user(
    db: Session,
    game_play_id: int,
    user_id: int,
    game_name: str,
):
    play = db.query(GamePlay).filter(
        GamePlay.id == game_play_id,
        GamePlay.user_id == user_id,
    ).with_for_update().first()

    if not play:
        raise HTTPException(
            status_code=404,
            detail="Game session not found",
        )

    game = db.query(GameSetting).filter(
        GameSetting.id == play.game_id
    ).first()

    if not game or game.name != game_name:
        raise HTTPException(
            status_code=400,
            detail="This game session does not belong to the requested game",
        )

    return play


def get_today_range():
    now = datetime.now(timezone.utc)
    start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


def enforce_daily_limit(
    db: Session,
    user_id: int,
    game: GameSetting,
):
    start, end = get_today_range()

    plays_today = db.query(GamePlay).filter(
        GamePlay.user_id == user_id,
        GamePlay.game_id == game.id,
        GamePlay.created_at >= start,
        GamePlay.created_at < end,
    ).count()

    if plays_today >= game.daily_play_limit:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Daily play limit reached. "
                f"Maximum {game.daily_play_limit} plays per day."
            ),
        )


def create_game_play(
    db: Session,
    user_id: int,
    game: GameSetting,
    board=None,
):
    wallet = get_wallet_for_update(db, user_id)

    if wallet.coins < game.entry_fees:
        raise HTTPException(
            status_code=400,
            detail="Insufficient coins",
        )

    wallet.coins -= game.entry_fees

    payment = GamePaymentDetail(
        user_id=user_id,
        game_id=game.id,
        paid=game.entry_fees,
        status="success",
    )

    play = GamePlay(
        user_id=user_id,
        game_id=game.id,
        entry_fee=game.entry_fees,
        reward_amount=game.rewards,
        prize_coins=0,
        status="started",
        board=board,
        matched_dot_ids=[],
        matches_completed=0,
    )

    db.add(payment)
    db.add(play)
    db.commit()
    db.refresh(play)
    db.refresh(wallet)

    return play, wallet


# =========================================================
# GET ENABLED GAMES
# GET /games
# =========================================================

@router.get("")
def get_games(db: Session = Depends(get_db)):
    games = db.query(GameSetting).filter(
        GameSetting.name.in_([COLOR_GAME, SCRATCH_GAME]),
        GameSetting.status.is_(True),
    ).order_by(GameSetting.id).all()

    return {
        "games": [
            {
                "id": game.id,
                "name": game.name,
                "entry_fees": game.entry_fees,
                "rewards": game.rewards,
                "daily_play_limit": game.daily_play_limit,
                "currency": "coins",
            }
            for game in games
        ]
    }


# =========================================================
# GET USER WALLET
# GET /games/wallet/{user_id}
# =========================================================

@router.get("/wallet/{user_id}")
def get_wallet(
    user_id: int,
    db: Session = Depends(get_db),
):
    wallet = db.query(Wallet).filter(
        Wallet.user_id == user_id
    ).first()

    if not wallet:
        raise HTTPException(
            status_code=404,
            detail="Wallet not found",
        )

    return {
        "user_id": user_id,
        "coins": wallet.coins,
        "currency": "coins",
    }


# =========================================================
# COLOUR CONNECT - GENERATE BOARD
# =========================================================

def generate_color_board():
    dots = []

    for color in COLORS:
        for number in range(1, 4):
            dots.append({
                "dot_id": f"{color}_{number}",
                "color": color,
            })

    random.shuffle(dots)
    return dots


# =========================================================
# START COLOUR CONNECT
# POST /games/color-connect/start
# =========================================================

@router.post("/color-connect/start")
def start_color_connect(
    payload: GameStartRequest,
    db: Session = Depends(get_db),
):
    try:
        game = get_game_setting(db, COLOR_GAME)
        enforce_daily_limit(db, payload.user_id, game)

        board = generate_color_board()

        play, wallet = create_game_play(
            db=db,
            user_id=payload.user_id,
            game=game,
            board=board,
        )

        return {
            "message": "Colour Connect started successfully",
            "game_play_id": play.id,
            "user_id": payload.user_id,
            "entry_fee": play.entry_fee,
            "reward_amount": play.reward_amount,
            "matches_required": len(COLORS),
            "board": play.board,
            "wallet_coins": wallet.coins,
            "currency": "coins",
        }

    except Exception:
        db.rollback()
        raise


# =========================================================
# MATCH COLOUR CONNECT DOTS
# POST /games/color-connect/match
# =========================================================

@router.post("/color-connect/match")
def match_color_dots(
    payload: MatchDotsRequest,
    db: Session = Depends(get_db),
):
    try:
        play = get_play_for_user(
            db,
            payload.game_play_id,
            payload.user_id,
            COLOR_GAME,
        )

        if play.status != "started":
            raise HTTPException(
                status_code=400,
                detail="This game is not active",
            )

        if len(set(payload.dot_ids)) != 3:
            raise HTTPException(
                status_code=400,
                detail="Select three different dots",
            )

        board = play.board or []
        dot_map = {
            dot["dot_id"]: dot
            for dot in board
        }

        for dot_id in payload.dot_ids:
            if dot_id not in dot_map:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid dot ID: {dot_id}",
                )

        matched = set(play.matched_dot_ids or [])

        if any(dot_id in matched for dot_id in payload.dot_ids):
            raise HTTPException(
                status_code=400,
                detail="One or more dots have already been matched",
            )

        selected_colors = {
            dot_map[dot_id]["color"]
            for dot_id in payload.dot_ids
        }

        if len(selected_colors) != 1:
            raise HTTPException(
                status_code=400,
                detail="The three dots must have the same color",
            )

        matched.update(payload.dot_ids)

        play.matched_dot_ids = list(matched)
        play.matches_completed += 1

        db.commit()
        db.refresh(play)

        return {
            "message": "Match successful",
            "game_play_id": play.id,
            "matched_color": list(selected_colors)[0],
            "matches_completed": play.matches_completed,
            "matches_required": len(COLORS),
            "game_completed": play.matches_completed >= len(COLORS),
        }

    except Exception:
        db.rollback()
        raise


# =========================================================
# COMPLETE COLOUR CONNECT
# POST /games/color-connect/complete
# =========================================================

@router.post("/color-connect/complete")
def complete_color_connect(
    payload: GamePlayRequest,
    db: Session = Depends(get_db),
):
    try:
        play = get_play_for_user(
            db,
            payload.game_play_id,
            payload.user_id,
            COLOR_GAME,
        )

        if play.status != "started":
            raise HTTPException(
                status_code=400,
                detail="This game has already been completed",
            )

        if play.matches_completed < len(COLORS):
            raise HTTPException(
                status_code=400,
                detail=f"Complete all {len(COLORS)} color matches first",
            )

        wallet = get_wallet_for_update(db, payload.user_id)

        reward = play.reward_amount

        wallet.coins += reward
        play.prize_coins = reward
        play.status = "won"
        play.completed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(play)
        db.refresh(wallet)

        return {
            "message": "Colour Connect completed successfully",
            "game_play_id": play.id,
            "result": "won",
            "reward_coins": reward,
            "wallet_coins": wallet.coins,
            "currency": "coins",
        }

    except Exception:
        db.rollback()
        raise


# =========================================================
# START SCRATCH GAME
# POST /games/scratch/start
# =========================================================

@router.post("/scratch/start")
def start_scratch_game(
    payload: GameStartRequest,
    db: Session = Depends(get_db),
):
    try:
        game = get_game_setting(db, SCRATCH_GAME)
        enforce_daily_limit(db, payload.user_id, game)

        play, wallet = create_game_play(
            db=db,
            user_id=payload.user_id,
            game=game,
        )

        return {
            "message": "Scratch Game started successfully",
            "game_play_id": play.id,
            "user_id": payload.user_id,
            "entry_fee": play.entry_fee,
            "maximum_reward": play.reward_amount,
            "wallet_coins": wallet.coins,
            "currency": "coins",
        }

    except Exception:
        db.rollback()
        raise


# =========================================================
# REVEAL SCRATCH RESULT
# POST /games/scratch/reveal
# =========================================================

@router.post("/scratch/reveal")
def reveal_scratch_result(
    payload: GamePlayRequest,
    db: Session = Depends(get_db),
):
    try:
        play = get_play_for_user(
            db,
            payload.game_play_id,
            payload.user_id,
            SCRATCH_GAME,
        )

        if play.status != "started":
            raise HTTPException(
                status_code=400,
                detail="This scratch game has already been revealed",
            )

        wallet = get_wallet_for_update(db, payload.user_id)

        # Reward is randomly selected from 0 to the configured maximum.
        reward = (
            secrets.randbelow(play.reward_amount + 1)
            if play.reward_amount > 0
            else 0
        )

        wallet.coins += reward
        play.prize_coins = reward
        play.status = "won" if reward > 0 else "lost"
        play.completed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(play)
        db.refresh(wallet)

        return {
            "message": "Scratch result revealed",
            "game_play_id": play.id,
            "result": play.status,
            "reward_coins": reward,
            "wallet_coins": wallet.coins,
            "currency": "coins",
        }

    except Exception:
        db.rollback()
        raise


# =========================================================
# USER DAILY PLAY LIMIT
# GET /games/daily-limit/{user_id}
# =========================================================

@router.get("/daily-limit/{user_id}")
def get_daily_play_limit(
    user_id: int,
    db: Session = Depends(get_db),
):
    start, end = get_today_range()

    results = []

    games = db.query(GameSetting).filter(
        GameSetting.name.in_([COLOR_GAME, SCRATCH_GAME])
    ).order_by(GameSetting.id).all()

    for game in games:
        played = db.query(GamePlay).filter(
            GamePlay.user_id == user_id,
            GamePlay.game_id == game.id,
            GamePlay.created_at >= start,
            GamePlay.created_at < end,
        ).count()

        results.append({
            "game_id": game.id,
            "game_name": game.name,
            "daily_play_limit": game.daily_play_limit,
            "plays_used": played,
            "plays_remaining": max(game.daily_play_limit - played, 0),
            "enabled": game.status,
        })

    return {"user_id": user_id, "games": results}


# =========================================================
# USER GAME HISTORY
# GET /games/history/{user_id}
# =========================================================

@router.get("/history/{user_id}")
def game_history(
    user_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    plays = db.query(GamePlay).filter(
        GamePlay.user_id == user_id,
    ).order_by(
        GamePlay.created_at.desc()
    ).limit(limit).all()

    game_ids = list({play.game_id for play in plays})

    games = {}
    if game_ids:
        game_rows = db.query(GameSetting).filter(
            GameSetting.id.in_(game_ids)
        ).all()
        games = {game.id: game.name for game in game_rows}

    return {
        "user_id": user_id,
        "history": [
            {
                "game_play_id": play.id,
                "game_id": play.game_id,
                "game_name": games.get(play.game_id, "Unknown Game"),
                "entry_fee": play.entry_fee,
                "reward_amount": play.reward_amount,
                "prize_coins": play.prize_coins,
                "status": play.status,
                "matches_completed": play.matches_completed,
                "started_at": play.started_at,
                "completed_at": play.completed_at,
            }
            for play in plays
        ],
        "currency": "coins",
    }
