# from fastapi import APIRouter, Depends, HTTPException, status
# from sqlalchemy.orm import Session

# from database import SessionLocal
# from models.pricing_details import PricingDetail
# from models.users import User
# from schemas.pricing_details import (PricingDetailCreate,PricingDetailUpdate,PricingDetailResponse)

# router = APIRouter(prefix="/pricing-details",tags=["Pricing Details"])


# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# @router.post(
#     "/",
#     response_model=PricingDetailResponse,
#     status_code=status.HTTP_200_OK
# )
# def create_or_update_pricing_detail(
#     data: PricingDetailCreate,
#     db: Session = Depends(get_db)
# ):

#     # --------------------------------------------------
#     # Check User
#     # --------------------------------------------------
#     user = db.query(User).filter(
#         User.id == data.user_id
#     ).first()

#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="User not found"
#         )

#     # --------------------------------------------------
#     # Check Existing Pricing
#     # --------------------------------------------------
#     pricing = db.query(PricingDetail).filter(
#         PricingDetail.user_id == data.user_id
#     ).first()

#     # --------------------------------------------------
#     # If pricing already exists -> UPDATE
#     # --------------------------------------------------
#     if pricing:

#         pricing.chat_amount = data.chat_amount
#         pricing.voice_call_amount = data.voice_call_amount
#         pricing.video_call_amount = data.video_call_amount

#         # updated_at will be automatically updated
#         # because the model has:
#         # onupdate=func.now()

#         db.commit()
#         db.refresh(pricing)

#         return pricing

#     # --------------------------------------------------
#     # If pricing does not exist -> CREATE
#     # --------------------------------------------------
#     pricing = PricingDetail(
#         user_id=data.user_id,
#         chat_amount=data.chat_amount,
#         voice_call_amount=data.voice_call_amount,
#         video_call_amount=data.video_call_amount
#     )

#     db.add(pricing)
#     db.commit()
#     db.refresh(pricing)

#     return pricing
# # @router.post(
# #     "/",
# #     response_model=PricingDetailResponse,
# #     status_code=status.HTTP_201_CREATED
# # )
# # def create_pricing_detail(
# #     data: PricingDetailCreate,
# #     db: Session = Depends(get_db)
# # ):

# #     user = db.query(User).filter(
# #         User.id == data.user_id
# #     ).first()

# #     if not user:
# #         raise HTTPException(
# #             status_code=status.HTTP_404_NOT_FOUND,
# #             detail="User not found"
# #         )

# #     existing = db.query(PricingDetail).filter(
# #         PricingDetail.user_id == data.user_id
# #     ).first()

# #     if existing:
# #         raise HTTPException(
# #             status_code=status.HTTP_400_BAD_REQUEST,
# #             detail="Pricing detail already exists for this user"
# #         )

# #     pricing = PricingDetail(**data.model_dump())

# #     db.add(pricing)
# #     db.commit()
# #     db.refresh(pricing)

# #     return pricing


# @router.get(
#     "/",
#     response_model=list[PricingDetailResponse],
#     status_code=status.HTTP_200_OK
# )
# def get_pricing_details(
#     db: Session = Depends(get_db)
# ):
#     pricing_details = db.query(
#         PricingDetail
#     ).all()

#     if not pricing_details:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="No data found"
#         )

#     return pricing_details


# @router.get(
#     "/{pricing_id}",
#     response_model=PricingDetailResponse,
#     status_code=status.HTTP_200_OK
# )
# def get_pricing_detail(
#     pricing_id: int,
#     db: Session = Depends(get_db)
# ):
#     pricing = db.query(PricingDetail).filter(
#         PricingDetail.id == pricing_id
#     ).first()

#     if not pricing:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Pricing detail not found"
#         )

#     return pricing


# @router.put(
#     "/{pricing_id}",
#     response_model=PricingDetailResponse,
#     status_code=status.HTTP_200_OK
# )
# def update_pricing_detail(
#     pricing_id: int,
#     data: PricingDetailUpdate,
#     db: Session = Depends(get_db)
# ):
#     pricing = db.query(PricingDetail).filter(
#         PricingDetail.id == pricing_id
#     ).first()

#     if not pricing:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Pricing detail not found"
#         )

#     for key, value in data.model_dump(exclude_unset=True).items():
#         setattr(pricing, key, value)

#     db.commit()
#     db.refresh(pricing)

#     return pricing


# @router.delete(
#     "/{pricing_id}",
#     status_code=status.HTTP_200_OK
# )
# def delete_pricing_detail(
#     pricing_id: int,
#     db: Session = Depends(get_db)
# ):
#     pricing = db.query(PricingDetail).filter(
#         PricingDetail.id == pricing_id
#     ).first()

#     if not pricing:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Pricing detail not found"
#         )

#     db.delete(pricing)
#     db.commit()

#     return {
#         "message": "Pricing detail deleted successfully"
#     }

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from database import SessionLocal
from models.pricing_details import PricingDetail
from models.users import User
from schemas.pricing_details import (
    PricingDetailCreate,
    PricingDetailUpdate,
    PricingDetailResponse
)

router = APIRouter(
    prefix="/pricing-details",
    tags=["Pricing Details"]
)


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --------------------------------------------------
# CREATE OR UPDATE PRICING DETAILS
# POST /pricing-details/
# --------------------------------------------------
@router.post(
    "/",
    response_model=PricingDetailResponse,
    status_code=status.HTTP_200_OK
)
def create_or_update_pricing_detail(
    data: PricingDetailCreate,
    db: Session = Depends(get_db)
):
    try:
        # Check whether user exists
        user = db.query(User).filter(
            User.id == data.user_id
        ).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Check existing pricing for this user
        pricing = db.query(PricingDetail).filter(
            PricingDetail.user_id == data.user_id
        ).first()

        if pricing:
            # Update existing pricing
            pricing.chat_amount = data.chat_amount
            pricing.voice_call_amount = data.voice_call_amount
            pricing.video_call_amount = data.video_call_amount

            message = "Pricing details updated successfully"

        else:
            # Create new pricing
            pricing = PricingDetail(
                user_id=data.user_id,
                chat_amount=data.chat_amount,
                voice_call_amount=data.voice_call_amount,
                video_call_amount=data.video_call_amount
            )

            db.add(pricing)
            message = "Pricing details created successfully"

        db.commit()
        db.refresh(pricing)

        return pricing

    except HTTPException:
        db.rollback()
        raise

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


# --------------------------------------------------
# GET ALL PRICING DETAILS
# GET /pricing-details/
# --------------------------------------------------
@router.get(
    "/",
    response_model=list[PricingDetailResponse],
    status_code=status.HTTP_200_OK
)
def get_pricing_details(
    db: Session = Depends(get_db)
):
    pricing_details = db.query(PricingDetail).all()

    return pricing_details


# --------------------------------------------------
# GET PRICING BY USER ID
# GET /pricing-details/user/3
# --------------------------------------------------
@router.get(
    "/user/{user_id}",
    response_model=PricingDetailResponse,
    status_code=status.HTTP_200_OK
)
def get_pricing_by_user_id(
    user_id: int,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    pricing = db.query(PricingDetail).filter(
        PricingDetail.user_id == user_id
    ).first()

    if not pricing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pricing details not found for this user"
        )

    return pricing


# --------------------------------------------------
# GET PRICING BY PRICING ID
# GET /pricing-details/1
# --------------------------------------------------
@router.get(
    "/{pricing_id}",
    response_model=PricingDetailResponse,
    status_code=status.HTTP_200_OK
)
def get_pricing_detail(
    pricing_id: int,
    db: Session = Depends(get_db)
):
    pricing = db.query(PricingDetail).filter(
        PricingDetail.id == pricing_id
    ).first()

    if not pricing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pricing detail not found"
        )

    return pricing


# --------------------------------------------------
# UPDATE PRICING BY PRICING ID
# PUT /pricing-details/1
# --------------------------------------------------
@router.put(
    "/{pricing_id}",
    response_model=PricingDetailResponse,
    status_code=status.HTTP_200_OK
)
def update_pricing_detail(
    pricing_id: int,
    data: PricingDetailUpdate,
    db: Session = Depends(get_db)
):
    try:
        pricing = db.query(PricingDetail).filter(
            PricingDetail.id == pricing_id
        ).first()

        if not pricing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pricing detail not found"
            )

        update_data = data.dict(exclude_unset=True)

        for key, value in update_data.items():
            if key != "user_id":
                setattr(pricing, key, value)

        db.commit()
        db.refresh(pricing)

        return pricing

    except HTTPException:
        db.rollback()
        raise

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


# --------------------------------------------------
# DELETE PRICING BY PRICING ID
# DELETE /pricing-details/1
# --------------------------------------------------
@router.delete(
    "/{pricing_id}",
    status_code=status.HTTP_200_OK
)
def delete_pricing_detail(
    pricing_id: int,
    db: Session = Depends(get_db)
):
    try:
        pricing = db.query(PricingDetail).filter(
            PricingDetail.id == pricing_id
        ).first()

        if not pricing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pricing detail not found"
            )

        db.delete(pricing)
        db.commit()

        return {
            "message": "Pricing details deleted successfully"
        }

    except HTTPException:
        db.rollback()
        raise

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
