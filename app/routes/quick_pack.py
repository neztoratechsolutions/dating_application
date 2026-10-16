from fastapi import APIRouter,Depends,HTTPException,status
from sqlalchemy.orm import Session

from database import SessionLocal
from models.quick_pack import QuickPack
from schemas.quick_pack import (
    QuickPackCreate,
    QuickPackResponse,
    QuickPackUpdate,
)

router = APIRouter(
    prefix="/quick-packs",
    tags= ["Quick Packs"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db 
    finally:
        db.close()

@router.post(
    "/",
    response_model=QuickPackResponse,
    status_code=201
)
def create_quick_pack(
    data:QuickPackCreate,
    db:Session = Depends(get_db)
):
    quick_pack = QuickPack(
        coins=data.coins,
        bonus=data.bonus,
        mrp=data.mrp,
        is_active=data.is_active,
        display_order=data.display_order
    )

    db.add(quick_pack)
    db.commit()
    db.refresh(quick_pack)

    return quick_pack

@router.get(
    "/",
    response_model=list[QuickPackResponse]
)
def get_quick_pack(
    db:Session = Depends(get_db)
):
    quick_packs = db.query(QuickPack).filter(
        QuickPack.is_active == True
    ).order_by(
        QuickPack.display_order.asc(),
        QuickPack.id.asc()
    ).all()

    return quick_packs

@router.put(
    "/{quick_pack.id}",
    response_model=QuickPackResponse
)
def update_quick_pack(
    quick_pack_id: int,
    data: QuickPackUpdate,
    db: Session = Depends(get_db)
):
    quick_pack = db.query(QuickPack).filter(
        QuickPack.id == quick_pack_id
    ).first()

    if not quick_pack:
        raise HTTPException(
            status_code=404,
            detail="Quick pack not found"
        )

    update_data = data.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(quick_pack, field, value)

    db.commit()
    db.refresh(quick_pack)

    return quick_pack

@router.delete(
    "/{quick_pack_id}"
)
def delete_quick_pack(
    quick_pack_id: int,
    db: Session = Depends(get_db)
):
    quick_pack = db.query(
        QuickPack
    ).filter(
        QuickPack.id == quick_pack_id
    ).first()

    if not quick_pack:
        raise HTTPException(
            status_code=404,
            detail="Quick pack not found"
        )

    db.delete(quick_pack)
    db.commit()

    return {
        "message": "Quick pack deleted successfully"
    }