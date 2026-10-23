from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
from models.users import User
from models.wallet import Wallet


router = APIRouter(
    prefix="/leaderboard",
    tags=["Leaderboard"],
)


@router.get("/weekly")
def get_weekly_leaderboard(
    db: Session = Depends(get_db),
):
    try:
        now = datetime.now(timezone.utc)

        week_start = (
            now - timedelta(days=now.weekday())
        ).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        results = (
            db.query(
                User.id.label("user_id"),
                User.display_name.label("name"),
                User.profile_photo.label("profile_image"),
                Wallet.coins.label("coins"),
            )
            .join(
                Wallet,
                Wallet.user_id == User.id,
            )
            .filter(
                Wallet.updated_at >= week_start,
                Wallet.updated_at <= now,
            )
            .order_by(
                desc(Wallet.coins),
                User.id.asc(),
            )
            .limit(10)
            .all()
        )

        if not results:
            raise HTTPException(
                status_code=404,
                detail="Data not found",
            )

        leaderboard = [
            {
                "rank": rank,
                "user_id": player.user_id,
                "name": player.name,
                "profile_image": player.profile_image,
                "coins": int(player.coins or 0),
            }
            for rank, player in enumerate(results, start=1)
        ]

        return {
            "message": "Weekly leaderboard fetched successfully",
            "period": "weekly",
            "total_players": len(leaderboard),
            "leaderboard": leaderboard,
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch leaderboard: {str(e)}",
        )