from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.users import User
from models.customer_settings import CustomerSettings

from schemas.customer_settings import (
    UserSettingsCreate,
    UserSettingsUpdate,
    UserSettingsResponse
)

router = APIRouter(
    prefix="/Customer-settings",
    tags=["Customer Settings"]
)


# Validate Customer ID
def validate_customer(customer_id: int, db: Session):

    user = db.query(User).filter(
        User.id == customer_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    if user.role != "customer":
        raise HTTPException(
            status_code=403,
            detail=f"{str(user.role).capitalize()} not access the settings"
        )

    return user


# CREATE SETTINGS
@router.post("/", response_model=UserSettingsResponse, status_code=201)
def create_settings(
    data: UserSettingsCreate,
    db: Session = Depends(get_db)
):
    validate_customer(data.customer_id, db)

    existing_settings = db.query(CustomerSettings).filter(
        CustomerSettings.customer_id == data.customer_id
    ).first()

    if existing_settings:
        raise HTTPException(
            status_code=400,
            detail="Settings already created for this customer"
        )

    new_settings = CustomerSettings(
        customer_id=data.customer_id,
        push_notifications=data.push_notifications,
        online_status=data.online_status,
        show_in_search=data.show_in_search,
        auto_recharge_coins=data.auto_recharge_coins
    )

    db.add(new_settings)
    db.commit()
    db.refresh(new_settings)

    return new_settings


# GET SETTINGS
@router.get("/{customer_id}", response_model=UserSettingsResponse)
def get_settings(
    customer_id: int,
    db: Session = Depends(get_db)
):
    validate_customer(customer_id, db)

    settings = db.query(CustomerSettings).filter(
        CustomerSettings.customer_id == customer_id
    ).first()

    if not settings:
        raise HTTPException(
            status_code=404,
            detail="Settings not found"
        )

    return settings


# UPDATE SETTINGS
@router.put("/{customer_id}", response_model=UserSettingsResponse)
def update_settings(
    customer_id: int,
    data: UserSettingsUpdate,
    db: Session = Depends(get_db)
):
    validate_customer(customer_id, db)

    settings = db.query(CustomerSettings).filter(
        CustomerSettings.customer_id == customer_id
    ).first()

    if not settings:
        raise HTTPException(
            status_code=404,
            detail="Settings not found"
        )

    update_data = data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="At least one setting field is required"
        )

    for field, value in update_data.items():
        setattr(settings, field, value)

    db.commit()
    db.refresh(settings)

    return settings