from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import SessionLocal
from models.state import State


router = APIRouter(
    prefix="/state",
    tags=["State"]
)

router = APIRouter(prefix="/states",tags=["States"])



# DB Session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# CREATE
@router.post("/")
def create_state(state_name: str, db: Session = Depends(get_db)):


    existing_state = (
        db.query(State)
        .filter(State.state_name.ilike(state_name))
        .first()
    )

    if existing_state:
        raise HTTPException(
            status_code=400,
            detail="State already exists"
        )


    state = State(state_name=state_name)

    db.add(state)
    db.commit()
    db.refresh(state)

    return {
        "message": "State created successfully",
        "data": state
    }

# GET ALL
@router.get("/")
def get_states(db: Session = Depends(get_db)):
    return db.query(State).all()


# GET BY ID
@router.get("/{state_id}")
def get_state(state_id: int, db: Session = Depends(get_db)):
    state = db.query(State).filter(State.id == state_id).first()

    if not state:
        raise HTTPException(status_code=404, detail="State not found")

    return state


# UPDATE
@router.put("/{state_id}")
def update_state(
    state_id: int,
    state_name: str,
    is_active: bool,
    db: Session = Depends(get_db)
):
    state = db.query(State).filter(State.id == state_id).first()

    if not state:
        raise HTTPException(status_code=404, detail="State not found")

    state.state_name = state_name
    state.is_active = is_active

    db.commit()
    db.refresh(state)

    return state


# DELETE
@router.delete("/{state_id}")
def delete_state(state_id: int, db: Session = Depends(get_db)):
    state = db.query(State).filter(State.id == state_id).first()

    if not state:
        raise HTTPException(status_code=404, detail="State not found")

    db.delete(state)
    db.commit()

    return {"message": "State deleted successfully"}