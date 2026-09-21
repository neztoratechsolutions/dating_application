from pydantic import BaseModel


class StateCreate(BaseModel):
    state_name: str


class StateUpdate(BaseModel):
    state_name: str | None = None
    is_active: bool | None = None


class StateResponse(BaseModel):
    id: int
    state_name: str
    is_active: bool

    class Config:
        from_attributes = True