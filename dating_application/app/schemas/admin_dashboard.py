# from pydantic import BaseModel


# class AdminDashboardSummaryResponse(BaseModel):
#     total_users: int
#     total_creators: int
#     live_now: int
#     revenue_today: float
#     pending_kyc: int
#     pending_withdrawals: int


# class RevenueTrendItem(BaseModel):
#     date: str
#     day: str
#     revenue: float


# class TopCreatorResponse(BaseModel):
#     rank: int
#     creator_id: int
#     name: str
#     state_id: int | None
#     profile_photo: str | None
#     earnings_today: float