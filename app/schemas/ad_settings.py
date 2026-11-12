from enum import Enum
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class AdPlacement(str, Enum):
    HOME_BANNER = "Home Banner"
    CREATOR_LISTING = "Creator Listing"
    WALLET_PAGE = "Wallet Page"
    GAMES_ZONE = "Games Zone"
    SPLASH_SCREEN = "Splash Screen"
    POPUP_ADS = "Popup Ads"


class AdStatus(str, Enum):
    ACTIVE = "Active"
    SCHEDULED = "Scheduled"
    EXPIRED = "Expired"


class AdCreate(BaseModel):
    title: str
    banner_url: str
    redirect_url: str
    placement: AdPlacement
    start_date: date
    end_date: date
    status: AdStatus = AdStatus.ACTIVE


class AdUpdate(BaseModel):
    title: Optional[str] = None
    banner_url: Optional[str] = None
    redirect_url: Optional[str] = None
    placement: Optional[AdPlacement] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[AdStatus] = None


class AdResponse(BaseModel):
    id: int
    title: str
    banner_url: str
    redirect_url: str
    placement: str
    start_date: date
    end_date: date
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True