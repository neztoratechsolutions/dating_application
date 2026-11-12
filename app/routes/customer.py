from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.users import User
from models.state import State

from schemas.customer import CustomerResponse,CreatorResponse



router = APIRouter(
    tags=["Customers & Creators"]
)


# ==========================================================
# GET ALL CUSTOMERS
# ==========================================================

@router.get(
    "/customers/",
    response_model=list[CustomerResponse]
)
def get_all_customers(
    db: Session = Depends(get_db)
):

    customers = (
        db.query(
            User,
            State.state_name.label("state_name")
        )
        .outerjoin(
            State,
            User.state_id == State.id
        )
        .filter(
            User.role == "customer"
        )
        .order_by(
            User.id.desc()
        )
        .all()
    )

    response = []

    for customer, state_name in customers:

        if customer.is_active:
            status = "Active"
        else:
            status = "Pending"

        response.append({
            "id": customer.id,
            "display_name": customer.display_name,
            "email": customer.email,
            "phone": customer.phone,
            "profile_photo": customer.profile_photo,
            "gender": customer.gender,
            "state": state_name,
            "status": status,
            "created_at": customer.created_at
        })

    return response


# ==========================================================
# GET ALL CREATORS
# ==========================================================

@router.get(
    "/creators/",
    response_model=list[CreatorResponse]
)
def get_all_creators(
    db: Session = Depends(get_db)
):

    creators = (
        db.query(
            User,
            State.state_name.label("state_name")
        )
        .outerjoin(
            State,
            User.state_id == State.id
        )
        .filter(
            User.role == "creator"
        )
        .order_by(
            User.id.desc()
        )
        .all()
    )

    response = []

    for creator, state_name in creators:

        if creator.is_active:
            status = "Active"
        else:
            status = "Pending"

        response.append({
            "id": creator.id,
            "display_name": creator.display_name,
            "email": creator.email,
            "phone": creator.phone,
            "profile_photo": creator.profile_photo,
            "gender": creator.gender,
            "state": state_name,
            "status": status,
            "created_at": creator.created_at
        })

    return response