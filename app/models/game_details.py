from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.sql import func

from database import Base


# =========================================================
# GAME SETTINGS
# Admin controls for Colour Connect and Scratch Game
# =========================================================

class GameSetting(Base):
    __tablename__ = "game_settings"

    id = Column(Integer, primary_key=True, index=True)

    # Colour Connect / Scratch Game
    name = Column(String(100), nullable=False, unique=True, index=True)

    # Admin can enable or disable each game
    status = Column(Boolean, nullable=False, default=True)

    # All values are coins
    entry_fees = Column(Integer, nullable=False, default=0)
    rewards = Column(Integer, nullable=False, default=0)

    # Maximum plays allowed per user per day for this game
    daily_play_limit = Column(Integer, nullable=False, default=3)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# =========================================================
# GAME PAYMENT DETAILS
# Records entry-fee coin deductions
# =========================================================

class GamePaymentDetail(Base):
    __tablename__ = "game_payment_details"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    game_id = Column(
        Integer,
        ForeignKey("game_settings.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Coins deducted for entering the game
    paid = Column(Integer, nullable=False, default=0)

    # success, failed, refunded
    status = Column(
        String(20),
        nullable=False,
        default="success",
        index=True,
    )

    paid_date = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# =========================================================
# GAME PLAY
# Stores sessions, results and rewards for both games
# =========================================================

class GamePlay(Base):
    __tablename__ = "game_plays"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    game_id = Column(
        Integer,
        ForeignKey("game_settings.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Settings snapshot captured when the game starts
    entry_fee = Column(Integer, nullable=False, default=0)
    reward_amount = Column(Integer, nullable=False, default=0)

    # Actual reward coins credited to the user
    prize_coins = Column(Integer, nullable=False, default=0)

    # started, completed, won, lost, cancelled
    status = Column(
        String(20),
        nullable=False,
        default="started",
        index=True,
    )

    # Colour Connect board data
    board = Column(JSON, nullable=True)

    # Prevents matching the same dots repeatedly
    matched_dot_ids = Column(
        JSON,
        nullable=False,
        default=list,
    )

    matches_completed = Column(Integer, nullable=False, default=0)

    started_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    completed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
