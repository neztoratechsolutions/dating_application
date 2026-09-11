from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db

from models.ad_setting import AdSetting
from models.ad_details import AdDetail

from schemas.ad_settings import (AdCreate,AdUpdate,AdResponse)
from datetime import datetime

router = APIRouter(prefix="/ad_settings",tags=["ad_settings"])


# ==========================================
# CREATE ADVERTISEMENT
# ==========================================
@router.post(
    "/",
    response_model=AdResponse,
    status_code=status.HTTP_201_CREATED
)
def create_ad(
    data: AdCreate,
    db: Session = Depends(get_db)
):
    ad = AdSetting(
        title=data.title,
        banner_url=data.banner_url,
        redirect_url=data.redirect_url,
        placement=data.placement.value,
        start_date=data.start_date,
        end_date=data.end_date,
        status=data.status.value
    )

    db.add(ad)
    db.commit()
    db.refresh(ad)

    ad_detail = AdDetail(
        ad_id=ad.id,
        impressions=0,
        clicks=0,
        ctr=0,
        revenue=0,
        status=True
    )

    db.add(ad_detail)
    db.commit()

    return ad


# ==========================================
# GET ALL ADS (TABLE DATA)
# ==========================================

# ==========================================
# GET ALL ADS (TABLE DATA)
# ==========================================
@router.get(
    "/",
    status_code=status.HTTP_200_OK
)
def get_ads(
    db: Session = Depends(get_db)
):
    ads = (
        db.query(
            AdSetting,
            AdDetail
        )
        .join(
            AdDetail,
            AdSetting.id == AdDetail.ad_id
        )
        .all()
    )

    if not ads:
        raise HTTPException(
            status_code=404,
            detail="Data not found"
        )

    return [
        {
            "id": ad.id,
            "title": ad.title,
            "banner_url": ad.banner_url,  # <--- ADD THIS
            "redirect_url": ad.redirect_url, # <--- ADD THIS
            "placement": ad.placement,
            "start_date": ad.start_date,  # <--- ADD THIS
            "end_date": ad.end_date,      # <--- ADD THIS
            "impressions": detail.impressions,
            "clicks": detail.clicks,
            "ctr": float(detail.ctr),
            "revenue": float(detail.revenue),
            "status": ad.status
        }
        for ad, detail in ads
    ]

# ==========================================
# GET BY ID
# ==========================================

@router.get(
    "/{ad_id}",
    status_code=status.HTTP_200_OK
)
def get_ad_by_id(
    ad_id: int,
    db: Session = Depends(get_db)
):
    ad_data = (
        db.query(
            AdSetting,
            AdDetail
        )
        .join(
            AdDetail,
            AdSetting.id == AdDetail.ad_id
        )
        .filter(
            AdSetting.id == ad_id
        )
        .first()
    )

    if not ad_data:
        raise HTTPException(
            status_code=404,
            detail="Advertisement not found"
        )

    ad, detail = ad_data

    return {
        "id": ad.id,
        "title": ad.title,
        "placement": ad.placement,
        "impressions": detail.impressions,
        "clicks": detail.clicks,
        "ctr": float(detail.ctr),
        "revenue": float(detail.revenue),
        "status": ad.status,
        "created_at": ad.created_at
    }


# ==========================================
# UPDATE
# ==========================================
@router.put(
    "/{ad_id}",
    response_model=AdResponse,
    status_code=status.HTTP_200_OK
)
def update_ad(
    ad_id: int,
    data: AdUpdate,
    db: Session = Depends(get_db)
):
    ad = db.query(
        AdSetting
    ).filter(
        AdSetting.id == ad_id
    ).first()

    if not ad:
        raise HTTPException(
            status_code=404,
            detail="Advertisement not found"
        )

    update_data = data.model_dump(
        exclude_unset=True
    )

    if "placement" in update_data:
        update_data["placement"] = update_data["placement"].value

    if "status" in update_data:
        update_data["status"] = update_data["status"].value

    for key, value in update_data.items():
        setattr(ad, key, value)

    db.commit()
    db.refresh(ad)

    return ad


# ==========================================
# DELETE
# ==========================================

@router.delete(
    "/{ad_id}",
    status_code=status.HTTP_200_OK
)
def delete_ad(
    ad_id: int,
    db: Session = Depends(get_db)
):
    ad = db.query(
        AdSetting
    ).filter(
        AdSetting.id == ad_id
    ).first()

    if not ad:
        raise HTTPException(
            status_code=404,
            detail="Advertisement not found"
        )

    db.delete(ad)
    db.commit()

    return {
        "message": "Advertisement deleted successfully"
    }


# ==========================================
# DASHBOARD COUNTS
# ==========================================

@router.get(
    "/dashboard/counts",
    status_code=status.HTTP_200_OK
)
def dashboard_counts(
    db: Session = Depends(get_db)
):
    active_ads = db.query(AdSetting).filter(
        AdSetting.status == "Active"
    ).count()

    scheduled_ads = db.query(AdSetting).filter(
        AdSetting.status == "Scheduled"
    ).count()

    total_revenue = db.query(
        func.sum(AdDetail.revenue)
    ).scalar() or 0

    total_clicks = db.query(
        func.sum(AdDetail.clicks)
    ).scalar() or 0

    total_impressions = db.query(
        func.sum(AdDetail.impressions)
    ).scalar() or 0

    return {
        "active_ads": active_ads,
        "scheduled_ads": scheduled_ads,
        "revenue": float(total_revenue),
        "total_clicks": total_clicks,
        "impressions": total_impressions
    }

import os
from fastapi import UploadFile, File

# Ensure uploads directory exists
os.makedirs("uploads", exist_ok=True)

@router.post(
    "/upload",
    status_code=status.HTTP_200_OK
)
def upload_ad_image(file: UploadFile = File(...)):
    # Generate a safe filename
    file_ext = file.filename.split(".")[-1]
    save_name = f"ad_{datetime.now().strftime('%Y%m%d%H%M%S')}.{file_ext}"
    file_location = f"uploads/{save_name}"
    
    # Save the file to disk
    with open(file_location, "wb+") as file_object:
        file_object.write(file.file.read())
    
    # Return the path to be saved in the DB
    return {"url": file_location}    