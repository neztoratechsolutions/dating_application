from pydantic import BaseModel


class ReferralResponse(BaseModel):
    referral_code: str
    referral_link: str
    friends_joined: int
    coins_earned: int


class BadgeResponse(BaseModel):
    id: int
    name: str
    description: str
    icon: str
    unlocked: bool


class RewardsResponse(BaseModel):
    referral: ReferralResponse
    badges: list[BadgeResponse]