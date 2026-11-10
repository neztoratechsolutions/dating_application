from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import SessionLocal

from models.voice_call import VoiceCall
from models.video_call import VideoCall
from models.gift_details import GiftDetail
from models.game_details import GamePlay


router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def convert_amount(value):
    return float(value or 0)


@router.get("/analytics/platform-performance")
def get_platform_performance(
    db: Session = Depends(get_db)
):
    try:
        # Current UTC date
        today = datetime.now(timezone.utc).date()

        # Current week: Monday to next Monday
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        start_datetime = datetime.combine(
            week_start,
            datetime.min.time(),
            tzinfo=timezone.utc
        )

        end_datetime = datetime.combine(
            week_end + timedelta(days=1),
            datetime.min.time(),
            tzinfo=timezone.utc
        )

        # ==========================================
        # 1. VOICE CALL EARNINGS
        # ==========================================

        voice_results = (
            db.query(
                func.date(VoiceCall.created_at).label("earning_date"),
                func.sum(VoiceCall.revenue).label("total")
            )
            .filter(
                VoiceCall.created_at >= start_datetime,
                VoiceCall.created_at < end_datetime,
                VoiceCall.status.in_(["completed", "ongoing"])
            )
            .group_by(func.date(VoiceCall.created_at))
            .all()
        )

        voice_data = {
            row.earning_date: convert_amount(row.total)
            for row in voice_results
        }

        # ==========================================
        # 2. VIDEO CALL EARNINGS
        # ==========================================

        video_results = (
            db.query(
                func.date(VideoCall.created_at).label("earning_date"),
                func.sum(VideoCall.revenue).label("total")
            )
            .filter(
                VideoCall.created_at >= start_datetime,
                VideoCall.created_at < end_datetime,
                VideoCall.status.in_(["completed", "ongoing"])
            )
            .group_by(func.date(VideoCall.created_at))
            .all()
        )

        video_data = {
            row.earning_date: convert_amount(row.total)
            for row in video_results
        }

        # ==========================================
        # 3. GIFT EARNINGS
        # ==========================================

        gift_results = (
            db.query(
                func.date(GiftDetail.created_at).label("earning_date"),
                func.sum(GiftDetail.earnings).label("total")
            )
            .filter(
                GiftDetail.created_at >= start_datetime,
                GiftDetail.created_at < end_datetime
            )
            .group_by(func.date(GiftDetail.created_at))
            .all()
        )

        gift_data = {
            row.earning_date: convert_amount(row.total)
            for row in gift_results
        }

        # ==========================================
        # 4. GAME EARNINGS
        # Players' winning coins only
        # ==========================================

        game_results = (
            db.query(
                func.date(GamePlay.completed_at).label("earning_date"),
                func.sum(GamePlay.prize_coins).label("total")
            )
            .filter(
                GamePlay.completed_at >= start_datetime,
                GamePlay.completed_at < end_datetime,
                GamePlay.status == "won",
                GamePlay.prize_coins > 0
            )
            .group_by(func.date(GamePlay.completed_at))
            .all()
        )

        game_data = {
            row.earning_date: convert_amount(row.total)
            for row in game_results
        }

        # ==========================================
        # DAILY + WEEKLY BREAKDOWN
        # ==========================================

        daily_breakdown = []

        weekly_voice = 0
        weekly_video = 0
        weekly_gift = 0
        weekly_game = 0
        weekly_total = 0

        for i in range(7):

            current_date = week_start + timedelta(days=i)

            voice_earnings = voice_data.get(current_date, 0)
            video_earnings = video_data.get(current_date, 0)
            gift_earnings = gift_data.get(current_date, 0)
            game_earnings = game_data.get(current_date, 0)

            total_earnings = (
                voice_earnings
                + video_earnings
                + gift_earnings
                + game_earnings
            )

            daily_breakdown.append({
                "date": current_date.isoformat(),
                "voice_call_earnings": voice_earnings,
                "video_call_earnings": video_earnings,
                "gift_earnings": gift_earnings,
                "game_earnings": game_earnings,
                "total_earnings": total_earnings
            })

            weekly_voice += voice_earnings
            weekly_video += video_earnings
            weekly_gift += gift_earnings
            weekly_game += game_earnings
            weekly_total += total_earnings

        # ==========================================
        # TODAY'S DAILY DATA
        # ==========================================

        today_voice = voice_data.get(today, 0)
        today_video = video_data.get(today, 0)
        today_gift = gift_data.get(today, 0)
        today_game = game_data.get(today, 0)

        today_total = (
            today_voice
            + today_video
            + today_gift
            + today_game
        )

        daily_data = {
            "date": today.isoformat(),
            "voice_call_earnings": today_voice,
            "video_call_earnings": today_video,
            "gift_earnings": today_gift,
            "game_earnings": today_game,
            "total_earnings": today_total
        }

        # ==========================================
        # FINAL RESPONSE
        # ==========================================

        return {
            "status": True,
            "message": "Platform performance fetched successfully",

            "daily_data": daily_data,

            "weekly_data": {
                "week_start": week_start.isoformat(),
                "week_end": week_end.isoformat(),

                "daily_breakdown": daily_breakdown,

                "summary": {
                    "voice_call_earnings": weekly_voice,
                    "video_call_earnings": weekly_video,
                    "gift_earnings": weekly_gift,
                    "game_earnings": weekly_game,
                    "total_earnings": weekly_total
                }
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )