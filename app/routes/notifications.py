
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import SessionLocal
from models.users import User
from models.user_status import UserStatus
from models.wallet import Wallet
from models.social_models import FollowDetail
from models.game_details import GamePlay, GameSetting
from models.wallet_transaction import WalletTransaction


router = APIRouter(
    prefix="/notifications",
    tags=["Customer Notifications"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def format_datetime(value):
    return value.isoformat() if value else None


@router.get("/customer/{customer_id}")
def get_customer_notifications(
    customer_id: int,
    db: Session = Depends(get_db)
):
    # -------------------------------------------------
    # 1. CHECK CUSTOMER
    # -------------------------------------------------

    customer = db.query(User).filter(
        User.id == customer_id,
        User.role == "customer"
    ).first()

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    today = date.today()
    start_datetime = datetime.combine(today, time.min)
    end_datetime = start_datetime + timedelta(days=1)

    notifications = []

    # -------------------------------------------------
    # 2. ONLINE CREATORS FOLLOWED BY CUSTOMER
    # -------------------------------------------------

    online_creators = (
        db.query(User, UserStatus)
        .join(
            FollowDetail,
            FollowDetail.following_id == User.id
        )
        .join(
            UserStatus,
            UserStatus.user_id == User.id
        )
        .filter(
            FollowDetail.follower_id == customer_id,
            FollowDetail.follow_status == "following",
            User.role == "creator",
            UserStatus.is_online.is_(True)
        )
        .distinct()
        .all()
    )

    online_creator_list = []

    for creator, creator_status in online_creators:
        online_creator_list.append({
            "creator_id": creator.id,
            "creator_name": creator.display_name,
            "status": "online",
            "date_time": format_datetime(
                creator_status.updated_at
            )
        })

        notifications.append({
            "type": "creator_online",
            "title": f"{creator.display_name} is online!",
            "message": "Your favourite creator just came online",
            "date_time": format_datetime(
                creator_status.updated_at
            ),
            "is_read": False
        })


    # -------------------------------------------------
    # 3. TODAY'S WALLET CREDITS
    # -------------------------------------------------

    today = date.today()

    start_datetime = datetime.combine(today, time.min)
    end_datetime = start_datetime + timedelta(days=1)

    wallet_transactions = (
        db.query(WalletTransaction)
        .filter(
            WalletTransaction.user_id == customer_id,
            func.lower(WalletTransaction.type) == "credit",
            func.lower(WalletTransaction.status) == "success",
            WalletTransaction.created_at >= start_datetime,
            WalletTransaction.created_at < end_datetime
        )
        .order_by(WalletTransaction.created_at.desc())
        .all()
    )

    total_coins_added = 0
    total_amount_added = 0.0
    wallet_credit_list = []

    for transaction in wallet_transactions:

        coins_added = transaction.coins or 0
        amount_added = float(transaction.amount or 0)

        total_coins_added += coins_added
        total_amount_added += amount_added

        wallet_credit_list.append({
            "transaction_id": transaction.transaction_id,
            "coins_added": coins_added,
            "amount": amount_added,
            "method": transaction.method,
            "message": f"{coins_added} coins added to your wallet",
            "date_time": (
                transaction.created_at.isoformat()
                if transaction.created_at else None
            )
        })

    wallet_today = {
        "available": True,
        "total_coins_added": total_coins_added,
        "total_amount_added": round(total_amount_added, 2),
        "transaction_count": len(wallet_credit_list),
        "transactions": wallet_credit_list
    }


    # -------------------------------------------------
    # 4. DAILY BONUS / GAME REWARDS
    # -------------------------------------------------

    game_rewards = (
        db.query(GamePlay, GameSetting)
        .join(
            GameSetting,
            GameSetting.id == GamePlay.game_id
        )
        .filter(
            GamePlay.user_id == customer_id,
            GamePlay.prize_coins > 0,
            GamePlay.status.in_(["completed", "won"]),
            func.coalesce(
                GamePlay.completed_at,
                GamePlay.created_at
            ) >= start_datetime,
            func.coalesce(
                GamePlay.completed_at,
                GamePlay.created_at
            ) < end_datetime
        )
        .order_by(
            func.coalesce(
                GamePlay.completed_at,
                GamePlay.created_at
            ).desc()
        )
        .all()
    )

    daily_bonus_list = []
    total_bonus_coins = 0

    for game, game_setting in game_rewards:
        reward_coins = game.prize_coins or 0
        total_bonus_coins += reward_coins

        reward_datetime = (
            game.completed_at or game.created_at
        )

        daily_bonus_list.append({
            "game_id": game.id,
            "game_name": game_setting.name,
            "coins_earned": reward_coins,
            "message": (
                f"You earned {reward_coins} coins "
                f"from {game_setting.name}"
            ),
            "date_time": format_datetime(reward_datetime)
        })

        notifications.append({
            "type": "daily_bonus",
            "title": "Daily bonus 🎉",
            "message": (
                f"You earned {reward_coins} coins "
                f"from {game_setting.name}"
            ),
            "date_time": format_datetime(reward_datetime),
            "is_read": False
        })

    # -------------------------------------------------
    # 5. CREATORS WHO STARTED FOLLOWING THIS CUSTOMER
    # -------------------------------------------------

    new_followers = (
        db.query(FollowDetail, User)
        .join(
            User,
            User.id == FollowDetail.follower_id
        )
        .filter(
            FollowDetail.following_id == customer_id,
            FollowDetail.follow_status == "following",
            User.role == "creator"
        )
        .order_by(FollowDetail.created_at.desc())
        .all()
    )

    new_follower_list = []

    for follow, creator in new_followers:
        follow_datetime = follow.created_at

        new_follower_list.append({
            "creator_id": creator.id,
            "creator_name": creator.display_name,
            "message": (
                f"{creator.display_name} started following you"
            ),
            "date_time": format_datetime(follow_datetime)
        })

        notifications.append({
            "type": "new_follower",
            "title": "New follower",
            "message": (
                f"{creator.display_name} started following you"
            ),
            "date_time": format_datetime(follow_datetime),
            "is_read": False
        })

    # -------------------------------------------------
    # 6. SORT ALL NOTIFICATIONS BY DATE AND TIME
    # -------------------------------------------------

    notifications.sort(
        key=lambda item: item["date_time"] or "",
        reverse=True
    )

    # -------------------------------------------------
    # 7. FINAL RESPONSE
    # -------------------------------------------------

    return {
        "customer_id": customer_id,
        "customer_name": customer.display_name,
        "date": today.isoformat(),

        "total_notifications": len(notifications),

        "online_creators": {
            "count": len(online_creator_list),
            "data": online_creator_list
        },

        "today_wallet_credits": wallet_today,

        "daily_bonus": {
            "total_coins_earned": total_bonus_coins,
            "total_games_won": len(daily_bonus_list),
            "data": daily_bonus_list
        },

        "new_followers": {
            "count": len(new_follower_list),
            "data": new_follower_list
        },

        "notifications": notifications
    }
