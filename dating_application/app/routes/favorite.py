from fastapi import APIRouter , Depends , HTTPException , status
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.users import User
from app.models.favorite import Favorite
from app.schemas.favorite import FavoriteCreate, FavoriteResponse

router = APIRouter(
    prefix="/favorites",
    tags= ["Favorites"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Add creator to customer's favourite

@router.post(
    "/",
    response_model=FavoriteResponse,
    status_code=status.HTTP_201_CREATED
)
def add_favourite(
    data : FavoriteCreate,
    db : Session =Depends(get_db)
):
    #check customer 

    customer = db.query(User).filter(
        User.id == data.customer_id,
        User.role == "customer"
    ).first()

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    #check creator

    creator = db.query(User).filter(
        User.id == data.creator_id,
        User.role == "creator"
    ).first()

    if not creator:
        raise HTTPException(
            status_code=404,
            detail="Creator not found"
        )

    # Check whether already favourite
    existing_favorite = db.query(Favorite).filter(
        Favorite.customer_id == data.customer_id,
        Favorite.creator_id == data.creator_id
    ).first()

    if existing_favorite:
        raise HTTPException(
            status_code=400,
            detail="Creator is already in favourites"
        )

    # Create favourite
    favorite = Favorite(
        customer_id = data.customer_id,
        creator_id = data.creator_id
    )

    db.add(favorite)
    db.commit()
    db.refresh(favorite)

    return favorite

# Get favourite creators of a customer

@router.get(
    "{customer_id}",
    response_model=list[FavoriteResponse]
)
def get_favorite_creators(
    customer_id : int,
    db: Session = Depends(get_db)
):
    # Check customer
    customer = db.query(User).filter(
        User.id == customer_id ,
        User.role == "customer"
    ).first()

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    favorites = db.query(Favorite).filter(
        Favorite.customer_id == customer_id
    ).all()

    return favorites