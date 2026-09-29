import os
import uuid
import csv
import io

from fastapi.responses import StreamingResponse

from datetime import datetime, date, time, timedelta

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status
)

from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import get_db

from models.kyc_detail import KYCDetail, CreatorKYC
from models.users import User
from models.state import State

from app.schemas.kyc_details import (
    KYCResponse,
    KYCAdminResponse,
    KYCDocumentStatusUpdate,
    KYCOverallStatusUpdate,
    KYCDashboardSummary
)


router = APIRouter(
    prefix="/admin/kyc",
    tags=["Admin KYC"]
)


# ==========================================================
# UPLOAD DIRECTORY
# ==========================================================

UPLOAD_DIR = "uploads/kyc"

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)


# ==========================================================
# ALLOWED STATUS
# ==========================================================

ALLOWED_DOCUMENT_STATUS = {
    "Pending",
    "Under Review",
    "Verified",
    "Rejected",
    "Re-upload"
}


ALLOWED_OVERALL_STATUS = {
    "Pending",
    "Under Review",
    "Approved",
    "Rejected",
    "Re-upload Required"
}


# ==========================================================
# SAVE FILE
# ==========================================================

def save_file(file: UploadFile) -> str:

    extension = os.path.splitext(
        file.filename or ""
    )[1]

    file_name = (
        f"{uuid.uuid4().hex}"
        f"{extension}"
    )

    file_path = os.path.join(
        UPLOAD_DIR,
        file_name
    )

    with open(
        file_path,
        "wb"
    ) as buffer:

        buffer.write(
            file.file.read()
        )

    return file_path.replace(
        "\\",
        "/"
    )


# ==========================================================
# CALCULATE OVERALL STATUS
# ==========================================================

def calculate_overall_status(
    aadhar_status: str,
    pan_status: str,
    selfie_status: str
) -> str:

    document_statuses = [
        aadhar_status,
        pan_status,
        selfie_status
    ]

    # ------------------------------------------------------
    # ANY REJECTED
    # ------------------------------------------------------

    if "Rejected" in document_statuses:

        return "Rejected"

    # ------------------------------------------------------
    # ANY RE-UPLOAD
    # ------------------------------------------------------

    if "Re-upload" in document_statuses:

        return "Re-upload Required"

    # ------------------------------------------------------
    # ALL VERIFIED
    # ------------------------------------------------------

    if all(
        value == "Verified"
        for value in document_statuses
    ):

        return "Approved"

    # ------------------------------------------------------
    # ANY UNDER REVIEW
    # ------------------------------------------------------

    if "Under Review" in document_statuses:

        return "Under Review"

    # ------------------------------------------------------
    # DEFAULT
    # ------------------------------------------------------

    return "Pending"


# ==========================================================
# CREATE KYC
# ==========================================================

@router.post(
    "/",
    response_model=KYCResponse,
    status_code=status.HTTP_201_CREATED
)
def create_kyc(

    user_id: int = Form(...),

    aadhar_photo: UploadFile = File(...),

    pan_photo: UploadFile = File(...),

    selfie_photo: UploadFile = File(...),

    db: Session = Depends(get_db)
):

    # ------------------------------------------------------
    # CHECK USER
    # ------------------------------------------------------

    user = (
        db.query(User)
        .filter(
            User.id == user_id
        )
        .first()
    )

    if not user:

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # ------------------------------------------------------
    # ONLY CREATOR
    # ------------------------------------------------------

    if user.role != "creator":

        raise HTTPException(
            status_code=400,
            detail="KYC can be submitted only for creator"
        )

    # ------------------------------------------------------
    # CHECK EXISTING KYC
    # ------------------------------------------------------

    existing_kyc = (
        db.query(KYCDetail)
        .filter(
            KYCDetail.user_id == user_id
        )
        .first()
    )

    if existing_kyc:

        raise HTTPException(
            status_code=400,
            detail="KYC already submitted for this creator"
        )

    # ------------------------------------------------------
    # SAVE FILES
    # ------------------------------------------------------

    aadhar_path = save_file(
        aadhar_photo
    )

    pan_path = save_file(
        pan_photo
    )

    selfie_path = save_file(
        selfie_photo
    )

    # ------------------------------------------------------
    # CREATE KYC
    # ------------------------------------------------------

    kyc = KYCDetail(

        user_id=user_id,

        aadhar_photo=aadhar_path,

        pan_photo=pan_path,

        selfie_photo=selfie_path,

        aadhar_status="Pending",

        pan_status="Pending",

        selfie_status="Pending",

        status="Pending",

        rejection_reason=None
    )

    db.add(kyc)

    db.commit()

    db.refresh(kyc)

    return kyc


# ==========================================================
# GET KYC DASHBOARD SUMMARY
# ==========================================================

@router.get(
    "/dashboard/summary",
    response_model=KYCDashboardSummary
)
def get_kyc_dashboard_summary(

    db: Session = Depends(get_db)

):

    # ------------------------------------------------------
    # TOTAL CREATORS
    # ------------------------------------------------------

    total_creators = (
        db.query(User)
        .filter(
            User.role == "creator"
        )
        .count()
    )

    # ------------------------------------------------------
    # PENDING
    # ------------------------------------------------------

    pending_kyc = (
        db.query(KYCDetail)
        .join(
            User,
            User.id == KYCDetail.user_id
        )
        .filter(
            User.role == "creator",
            KYCDetail.status == "Pending"
        )
        .count()
    )

    # ------------------------------------------------------
    # APPROVED
    # ------------------------------------------------------

    approved = (
        db.query(KYCDetail)
        .join(
            User,
            User.id == KYCDetail.user_id
        )
        .filter(
            User.role == "creator",
            KYCDetail.status == "Approved"
        )
        .count()
    )

    # ------------------------------------------------------
    # REJECTED
    # ------------------------------------------------------

    rejected = (
        db.query(KYCDetail)
        .join(
            User,
            User.id == KYCDetail.user_id
        )
        .filter(
            User.role == "creator",
            KYCDetail.status == "Rejected"
        )
        .count()
    )

    # ------------------------------------------------------
    # RE-UPLOAD
    # ------------------------------------------------------

    re_upload = (
        db.query(KYCDetail)
        .join(
            User,
            User.id == KYCDetail.user_id
        )
        .filter(
            User.role == "creator",
            KYCDetail.status == "Re-upload Required"
        )
        .count()
    )

    # ------------------------------------------------------
    # COMPLETED TODAY
    # ------------------------------------------------------

    today = date.today()

    completed_today = (
        db.query(KYCDetail)
        .join(
            User,
            User.id == KYCDetail.user_id
        )
        .filter(
            User.role == "creator",

            KYCDetail.updated_at >= datetime.combine(
                today,
                time.min
            ),

            KYCDetail.updated_at < datetime.combine(
                today + timedelta(days=1),
                time.min
            ),

            KYCDetail.status.in_([
                "Approved",
                "Rejected",
                "Re-upload Required"
            ])
        )
        .count()
    )

    return KYCDashboardSummary(

        total_creators=total_creators,

        pending_kyc=pending_kyc,

        approved=approved,

        rejected=rejected,

        re_upload=re_upload,

        completed_today=completed_today
    )


# ==========================================================
# GET ALL KYC
# SEARCH + STATE + STATUS + DATE + PAGINATION
# ==========================================================

@router.get(
    "/",
    response_model=list[KYCAdminResponse]
)
def get_all_kyc(

    search: str | None = Query(
        None,
        description="Search name, mobile, email or creator ID"
    ),

    state_id: int | None = Query(
        None,
        description="Filter by state"
    ),

    kyc_status: str | None = Query(
        None,
        description="Pending, Under Review, Approved, Rejected, Re-upload Required"
    ),

    start_date: date | None = Query(
        None,
        description="Filter KYC created date from this date"
    ),

    end_date: date | None = Query(
        None,
        description="Filter KYC created date up to this date"
    ),

    page: int = Query(
        1,
        ge=1,
        description="Page number"
    ),

    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="Records per page"
    ),

    db: Session = Depends(get_db)
):

    # ------------------------------------------------------
    # VALIDATE DATE RANGE
    # ------------------------------------------------------

    if start_date and end_date:

        if start_date > end_date:

            raise HTTPException(
                status_code=400,
                detail="start_date cannot be greater than end_date"
            )

    # ------------------------------------------------------
    # BASE QUERY
    # ------------------------------------------------------

    query = (
        db.query(
            KYCDetail,
            User,
            State
        )
        .join(
            User,
            User.id == KYCDetail.user_id
        )
        .outerjoin(
            State,
            State.id == User.state_id
        )
        .filter(
            User.role == "creator"
        )
    )

    # ------------------------------------------------------
    # SEARCH
    # ------------------------------------------------------

    if isinstance(search, str) and search.strip():

        search_text = search.strip()

        search_value = f"%{search_text}%"

        creator_id_search = search_text.upper()

        # --------------------------------------------------
        # CREATOR ID
        # Example: VLR00015
        # --------------------------------------------------

        if creator_id_search.startswith("VLR"):

            numeric_part = (
                creator_id_search
                .replace("VLR", "", 1)
            )

            if numeric_part.isdigit():

                creator_user_id = int(
                    numeric_part
                )

                query = query.filter(
                    User.id == creator_user_id
                )

            else:

                query = query.filter(
                    or_(
                        User.display_name.ilike(
                            search_value
                        ),

                        User.email.ilike(
                            search_value
                        ),

                        User.phone.ilike(
                            search_value
                        )
                    )
                )

        else:

            query = query.filter(
                or_(
                    User.display_name.ilike(
                        search_value
                    ),

                    User.email.ilike(
                        search_value
                    ),

                    User.phone.ilike(
                        search_value
                    )
                )
            )

    # ------------------------------------------------------
    # STATE FILTER
    # ------------------------------------------------------

    if state_id is not None:

        query = query.filter(
            User.state_id == state_id
        )

    # ------------------------------------------------------
    # STATUS FILTER
    # ------------------------------------------------------

    if isinstance(kyc_status, str) and kyc_status.strip():

        if kyc_status not in ALLOWED_OVERALL_STATUS:

            raise HTTPException(
                status_code=400,
                detail="Invalid KYC status"
            )

        query = query.filter(
            KYCDetail.status == kyc_status
        )

    # ------------------------------------------------------
    # START DATE FILTER
    # ------------------------------------------------------

    if start_date:

        start_datetime = datetime.combine(
            start_date,
            time.min
        )

        query = query.filter(
            KYCDetail.created_at >= start_datetime
        )

    # ------------------------------------------------------
    # END DATE FILTER
    # ------------------------------------------------------

    if end_date:

        next_day = end_date + timedelta(days=1)

        end_datetime = datetime.combine(
            next_day,
            time.min
        )

        query = query.filter(
            KYCDetail.created_at < end_datetime
        )

    # ------------------------------------------------------
    # ORDER
    # ------------------------------------------------------

    query = query.order_by(
        KYCDetail.created_at.desc()
    )

    # ------------------------------------------------------
    # PAGINATION
    # ------------------------------------------------------

    offset = (page - 1) * limit

    results = (
        query
        .offset(offset)
        .limit(limit)
        .all()
    )

    # ------------------------------------------------------
    # NO DATA
    # ------------------------------------------------------

    if not results:

        raise HTTPException(
            status_code=404,
            detail="KYC data not found"
        )

    # ------------------------------------------------------
    # RESPONSE
    # ------------------------------------------------------

    response = []

    for kyc, user, state in results:

        response.append(

            KYCAdminResponse(

                id=kyc.id,

                user_id=user.id,

                creator_id=f"VLR{user.id:05d}",

                display_name=user.display_name,

                email=user.email,

                phone=user.phone,

                state_id=user.state_id,

                state_name=(
                    state.state_name
                    if state
                    else None
                ),

                profile_photo=user.profile_photo,

                joined_date=user.created_at,

                aadhar_photo=kyc.aadhar_photo,

                pan_photo=kyc.pan_photo,

                selfie_photo=kyc.selfie_photo,

                aadhar_status=kyc.aadhar_status,

                pan_status=kyc.pan_status,

                selfie_status=kyc.selfie_status,

                status=kyc.status,

                rejection_reason=(
                    kyc.rejection_reason
                ),

                updated_at=kyc.updated_at
            )
        )

    return response


# ==========================================================
# DOWNLOAD KYC CSV
# ==========================================================

@router.get(
    "/download/csv"
)
def download_kyc_csv(

    kyc_status: str = Query(
        ...,
        description="Approved, Pending, Rejected, Re-upload Required"
    ),

    search: str | None = Query(
        None,
        description="Search name, mobile, email or creator ID"
    ),

    state_id: int | None = Query(
        None,
        description="Filter by state"
    ),

    start_date: date | None = Query(
        None,
        description="Filter KYC created date from this date"
    ),

    end_date: date | None = Query(
        None,
        description="Filter KYC created date up to this date"
    ),

    db: Session = Depends(get_db)
):

    # ------------------------------------------------------
    # VALIDATE STATUS
    # ------------------------------------------------------

    if kyc_status not in ALLOWED_OVERALL_STATUS:

        raise HTTPException(
            status_code=400,
            detail="Invalid KYC status"
        )

    # ------------------------------------------------------
    # VALIDATE DATE
    # ------------------------------------------------------

    if start_date and end_date:

        if start_date > end_date:

            raise HTTPException(
                status_code=400,
                detail="start_date cannot be greater than end_date"
            )

    # ------------------------------------------------------
    # BASE QUERY
    # ------------------------------------------------------

    query = (
        db.query(
            KYCDetail,
            User,
            State
        )
        .join(
            User,
            User.id == KYCDetail.user_id
        )
        .outerjoin(
            State,
            State.id == User.state_id
        )
        .filter(
            User.role == "creator"
        )
    )

    # ------------------------------------------------------
    # STATUS
    # ------------------------------------------------------

    query = query.filter(
        KYCDetail.status == kyc_status
    )

    # ------------------------------------------------------
    # SEARCH
    # ------------------------------------------------------

    if isinstance(search, str) and search.strip():

        search_text = search.strip()

        search_value = f"%{search_text}%"

        creator_id_search = search_text.upper()

        if creator_id_search.startswith("VLR"):

            numeric_part = (
                creator_id_search
                .replace("VLR", "", 1)
            )

            if numeric_part.isdigit():

                creator_user_id = int(
                    numeric_part
                )

                query = query.filter(
                    User.id == creator_user_id
                )

            else:

                query = query.filter(
                    or_(
                        User.display_name.ilike(
                            search_value
                        ),

                        User.email.ilike(
                            search_value
                        ),

                        User.phone.ilike(
                            search_value
                        )
                    )
                )

        else:

            query = query.filter(
                or_(
                    User.display_name.ilike(
                        search_value
                    ),

                    User.email.ilike(
                        search_value
                    ),

                    User.phone.ilike(
                        search_value
                    )
                )
            )

    # ------------------------------------------------------
    # STATE
    # ------------------------------------------------------

    if state_id is not None:

        query = query.filter(
            User.state_id == state_id
        )

    # ------------------------------------------------------
    # START DATE
    # ------------------------------------------------------

    if start_date:

        start_datetime = datetime.combine(
            start_date,
            time.min
        )

        query = query.filter(
            KYCDetail.created_at >= start_datetime
        )

    # ------------------------------------------------------
    # END DATE
    # ------------------------------------------------------

    if end_date:

        next_day = end_date + timedelta(days=1)

        end_datetime = datetime.combine(
            next_day,
            time.min
        )

        query = query.filter(
            KYCDetail.created_at < end_datetime
        )

    # ------------------------------------------------------
    # GET DATA
    # ------------------------------------------------------

    results = (
        query
        .order_by(
            KYCDetail.created_at.desc()
        )
        .all()
    )

    if not results:

        raise HTTPException(
            status_code=404,
            detail=f"No {kyc_status} KYC data found"
        )

    # ------------------------------------------------------
    # CREATE CSV
    # ------------------------------------------------------

    output = io.StringIO()

    writer = csv.writer(
        output
    )

    # ------------------------------------------------------
    # CSV HEADER
    # ------------------------------------------------------

    writer.writerow([
        "KYC ID",
        "User ID",
        "Creator ID",
        "Display Name",
        "Email",
        "Phone",
        "State",
        "Aadhaar Status",
        "PAN Status",
        "Selfie Status",
        "KYC Status",
        "Rejection Reason",
        "Created Date",
        "Updated Date"
    ])

    # ------------------------------------------------------
    # CSV DATA
    # ------------------------------------------------------

    for kyc, user, state in results:

        writer.writerow([

            kyc.id,

            user.id,

            f"VLR{user.id:05d}",

            user.display_name,

            user.email,

            user.phone,

            (
                state.state_name
                if state
                else ""
            ),

            kyc.aadhar_status,

            kyc.pan_status,

            kyc.selfie_status,

            kyc.status,

            (
                kyc.rejection_reason
                if kyc.rejection_reason
                else ""
            ),

            (
                kyc.created_at.isoformat()
                if kyc.created_at
                else ""
            ),

            (
                kyc.updated_at.isoformat()
                if kyc.updated_at
                else ""
            )
        ])

    # ------------------------------------------------------
    # MOVE TO BEGINNING
    # ------------------------------------------------------

    output.seek(0)

    # ------------------------------------------------------
    # FILE NAME
    # ------------------------------------------------------

    status_file_name = (
        kyc_status
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )

    file_name = (
        f"kyc_{status_file_name}.csv"
    )

    # ------------------------------------------------------
    # DOWNLOAD RESPONSE
    # ------------------------------------------------------

    return StreamingResponse(

        iter([
            output.getvalue()
        ]),

        media_type="text/csv",

        headers={
            "Content-Disposition":
                f'attachment; filename="{file_name}"'
        }
    )


# ==========================================================
# GET SINGLE KYC BY USER ID
# ==========================================================

@router.get(
    "/user/{user_id}",
    response_model=KYCAdminResponse
)
def get_kyc_by_user_id(

    user_id: int,

    db: Session = Depends(get_db)

):

    result = (
        db.query(
            KYCDetail,
            User,
            State
        )
        .join(
            User,
            User.id == KYCDetail.user_id
        )
        .outerjoin(
            State,
            State.id == User.state_id
        )
        .filter(
            KYCDetail.user_id == user_id,
            User.role == "creator"
        )
        .first()
    )

    if not result:

        raise HTTPException(
            status_code=404,
            detail="KYC data not found for this user"
        )

    kyc, user, state = result

    return KYCAdminResponse(

        id=kyc.id,

        user_id=user.id,

        creator_id=f"VLR{user.id:05d}",

        display_name=user.display_name,

        email=user.email,

        phone=user.phone,

        state_id=user.state_id,

        state_name=(
            state.state_name
            if state
            else None
        ),

        profile_photo=user.profile_photo,

        joined_date=user.created_at,

        aadhar_photo=kyc.aadhar_photo,

        pan_photo=kyc.pan_photo,

        selfie_photo=kyc.selfie_photo,

        aadhar_status=kyc.aadhar_status,

        pan_status=kyc.pan_status,

        selfie_status=kyc.selfie_status,

        status=kyc.status,

        rejection_reason=(
            kyc.rejection_reason
        ),

        updated_at=kyc.updated_at
    )


# ==========================================================
# UPDATE DOCUMENT STATUS BY USER ID
# ==========================================================

@router.put(
    "/user/{user_id}/document-status",
    response_model=KYCResponse
)
def update_document_status(

    user_id: int,

    data: KYCDocumentStatusUpdate,

    db: Session = Depends(get_db)

):

    # ------------------------------------------------------
    # FIND KYC USING USER ID
    # ------------------------------------------------------

    kyc = (
        db.query(KYCDetail)
        .filter(
            KYCDetail.user_id == user_id
        )
        .first()
    )

    if not kyc:

        raise HTTPException(
            status_code=404,
            detail="KYC data not found for this user"
        )

    # ------------------------------------------------------
    # AADHAAR
    # ------------------------------------------------------

    if data.aadhar_status is not None:

        if (
            data.aadhar_status
            not in ALLOWED_DOCUMENT_STATUS
        ):

            raise HTTPException(
                status_code=400,
                detail="Invalid Aadhaar status"
            )

        kyc.aadhar_status = (
            data.aadhar_status
        )

    # ------------------------------------------------------
    # PAN
    # ------------------------------------------------------

    if data.pan_status is not None:

        if (
            data.pan_status
            not in ALLOWED_DOCUMENT_STATUS
        ):

            raise HTTPException(
                status_code=400,
                detail="Invalid PAN status"
            )

        kyc.pan_status = (
            data.pan_status
        )

    # ------------------------------------------------------
    # SELFIE
    # ------------------------------------------------------

    if data.selfie_status is not None:

        if (
            data.selfie_status
            not in ALLOWED_DOCUMENT_STATUS
        ):

            raise HTTPException(
                status_code=400,
                detail="Invalid Selfie status"
            )

        kyc.selfie_status = (
            data.selfie_status
        )

    # ------------------------------------------------------
    # REJECTION REASON
    # ------------------------------------------------------

    if data.rejection_reason is not None:

        kyc.rejection_reason = (
            data.rejection_reason
        )

    # ------------------------------------------------------
    # AUTOMATIC OVERALL STATUS
    # ------------------------------------------------------

    kyc.status = calculate_overall_status(

        kyc.aadhar_status,

        kyc.pan_status,

        kyc.selfie_status
    )

    db.commit()

    db.refresh(kyc)

    return kyc


# ==========================================================
# UPDATE OVERALL KYC STATUS BY USER ID
# ==========================================================

@router.put(
    "/user/{user_id}/status",
    response_model=KYCResponse
)
def update_kyc_status(

    user_id: int,

    data: KYCOverallStatusUpdate,

    db: Session = Depends(get_db)

):

    # ------------------------------------------------------
    # FIND KYC USING USER ID
    # ------------------------------------------------------

    kyc = (
        db.query(KYCDetail)
        .filter(
            KYCDetail.user_id == user_id
        )
        .first()
    )

    if not kyc:

        raise HTTPException(
            status_code=404,
            detail="KYC data not found for this user"
        )

    # ------------------------------------------------------
    # VALIDATE STATUS
    # ------------------------------------------------------

    if data.status not in ALLOWED_OVERALL_STATUS:

        raise HTTPException(
            status_code=400,
            detail="Invalid KYC status"
        )

    kyc.status = data.status

    # ------------------------------------------------------
    # REJECTION REASON
    # ------------------------------------------------------

    if data.rejection_reason is not None:

        kyc.rejection_reason = (
            data.rejection_reason
        )

    db.commit()

    db.refresh(kyc)

    return kyc


# ==========================================================
# DELETE KYC BY USER ID
# ==========================================================

@router.delete(
    "/user/{user_id}",
    status_code=status.HTTP_200_OK
)
def delete_kyc(

    user_id: int,

    db: Session = Depends(get_db)

):

    # ------------------------------------------------------
    # FIND KYC USING USER ID
    # ------------------------------------------------------

    kyc = (
        db.query(KYCDetail)
        .filter(
            KYCDetail.user_id == user_id
        )
        .first()
    )

    if not kyc:

        raise HTTPException(
            status_code=404,
            detail="KYC data not found for this user"
        )

    # ------------------------------------------------------
    # DELETE UPLOADED FILES
    # ------------------------------------------------------

    files = [
        kyc.aadhar_photo,
        kyc.pan_photo,
        kyc.selfie_photo
    ]

    for file_path in files:

        if file_path and os.path.exists(file_path):

            try:

                os.remove(file_path)

            except OSError:

                pass

    # ------------------------------------------------------
    # DELETE KYC RECORD
    # ------------------------------------------------------

    db.delete(kyc)

    db.commit()

    # ------------------------------------------------------
    # RESPONSE
    # ------------------------------------------------------

    return {
        "message": "KYC deleted successfully",
        "user_id": user_id
    }


# ==========================================================
# RE-UPLOAD KYC DOCUMENTS BY USER ID
# ==========================================================

@router.put(
    "/user/{user_id}/re-upload",
    response_model=KYCResponse
)
def re_upload_kyc(

    user_id: int,

    aadhar_photo: UploadFile | None = File(None),

    pan_photo: UploadFile | None = File(None),

    selfie_photo: UploadFile | None = File(None),

    db: Session = Depends(get_db)

):

    # ------------------------------------------------------
    # FIND KYC USING USER ID
    # ------------------------------------------------------

    kyc = (
        db.query(KYCDetail)
        .filter(
            KYCDetail.user_id == user_id
        )
        .first()
    )

    if not kyc:

        raise HTTPException(
            status_code=404,
            detail="KYC data not found for this user"
        )

    uploaded = False

    # ------------------------------------------------------
    # AADHAAR
    # ------------------------------------------------------

    if aadhar_photo:

        kyc.aadhar_photo = save_file(
            aadhar_photo
        )

        kyc.aadhar_status = "Pending"

        uploaded = True

    # ------------------------------------------------------
    # PAN
    # ------------------------------------------------------

    if pan_photo:

        kyc.pan_photo = save_file(
            pan_photo
        )

        kyc.pan_status = "Pending"

        uploaded = True

    # ------------------------------------------------------
    # SELFIE
    # ------------------------------------------------------

    if selfie_photo:

        kyc.selfie_photo = save_file(
            selfie_photo
        )

        kyc.selfie_status = "Pending"

        uploaded = True

    # ------------------------------------------------------
    # CHECK UPLOAD
    # ------------------------------------------------------

    if not uploaded:

        raise HTTPException(
            status_code=400,
            detail="At least one document is required"
        )

    # ------------------------------------------------------
    # AFTER RE-UPLOAD
    # ------------------------------------------------------

    kyc.status = calculate_overall_status(

        kyc.aadhar_status,

        kyc.pan_status,

        kyc.selfie_status
    )

    kyc.rejection_reason = None

    db.commit()

    db.refresh(kyc)

    return kyc




@router.get("/review/{user_id}")
def review_kyc(
    user_id: int,
    db: Session = Depends(get_db)
):
    # -----------------------------
    # Check User
    # -----------------------------
    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # -----------------------------
    # Only Creator KYC Review
    # -----------------------------
    if user.role != "creator":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="KYC review is available only for creator"
        )

    # -----------------------------
    # Get KYC
    # -----------------------------
    kyc = db.query(KYCDetail).filter(
        KYCDetail.user_id == user_id
    ).first()

    if not kyc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="KYC data not found for this user"
        )

    # -----------------------------
    # Get Creator Bank KYC
    # -----------------------------
    bank_kyc = db.query(CreatorKYC).filter(
        CreatorKYC.user_id == user_id
    ).first()

    # -----------------------------
    # Get State
    # -----------------------------
    state = None

    if user.state_id:
        state = db.query(State).filter(
            State.id == user.state_id
        ).first()

    # -----------------------------
    # Creator ID
    # -----------------------------
    creator_id = f"VLR{user.id:05d}"

    # =====================================================
    # KYC TIMELINE
    # =====================================================

    kyc_timeline = []

    def get_file_uploaded_time(file_path):
        """
        Get uploaded file date/time from file modification time.
        """
        if not file_path:
            return None

        if not os.path.exists(file_path):
            return None

        return datetime.fromtimestamp(
            os.path.getmtime(file_path)
        ).astimezone()

    # -----------------------------
    # Signup completed
    # -----------------------------
    if user.created_at:
        kyc_timeline.append({
            "title": "Signup completed",
            "date": user.created_at
        })

    # -----------------------------
    # Aadhaar uploaded
    # -----------------------------
    aadhar_uploaded_at = get_file_uploaded_time(
        kyc.aadhar_photo
    )

    if aadhar_uploaded_at:
        kyc_timeline.append({
            "title": "Aadhaar uploaded",
            "date": aadhar_uploaded_at
        })

    # -----------------------------
    # PAN uploaded
    # -----------------------------
    pan_uploaded_at = get_file_uploaded_time(
        kyc.pan_photo
    )

    if pan_uploaded_at:
        kyc_timeline.append({
            "title": "PAN uploaded",
            "date": pan_uploaded_at
        })

    # -----------------------------
    # Selfie captured
    # -----------------------------
    selfie_uploaded_at = get_file_uploaded_time(
        kyc.selfie_photo
    )

    if selfie_uploaded_at:
        kyc_timeline.append({
            "title": "Selfie captured",
            "date": selfie_uploaded_at
        })

    # -----------------------------
    # KYC submitted for review
    # -----------------------------
    if kyc.created_at:
        kyc_timeline.append({
            "title": "KYC submitted for review",
            "date": kyc.created_at
        })

    # -----------------------------
    # Sort Timeline
    # -----------------------------
    kyc_timeline.sort(
        key=lambda x: x["date"]
    )

    # =====================================================
    # RESPONSE
    # =====================================================

    return {
        "status": 200,
        "message": "KYC review details fetched successfully",
        "data": {
            "user_id": user.id,
            "creator_id": creator_id,

            # -------------------------
            # Personal Details
            # -------------------------
            "personal_details": {
                "display_name": user.display_name,
                "phone": user.phone,
                "email": user.email,
                "state_id": user.state_id,
                "state_name": state.state_name if state else None,
                "profile_photo": user.profile_photo,
                "joined_date": user.created_at
            },

            # -------------------------
            # Bank Details
            # -------------------------
            "bank_details": {
                "bank_photo": (
                    bank_kyc.bank_photo
                    if bank_kyc
                    else None
                ),
                "bank_status": (
                    bank_kyc.bank_status
                    if bank_kyc
                    else None
                ),
                "uploaded_at": (
                    bank_kyc.created_at
                    if bank_kyc
                    else None
                ),
                "updated_at": (
                    bank_kyc.updated_at
                    if bank_kyc
                    else None
                )
            },

            # -------------------------
            # KYC Documents
            # -------------------------
            "documents": {
                "aadhar": {
                    "photo": kyc.aadhar_photo,
                    "status": kyc.aadhar_status
                },
                "pan": {
                    "photo": kyc.pan_photo,
                    "status": kyc.pan_status
                },
                "selfie": {
                    "photo": kyc.selfie_photo,
                    "status": kyc.selfie_status
                }
            },

            # -------------------------
            # Overall KYC Status
            # -------------------------
            "kyc_status": kyc.status,

            "rejection_reason": kyc.rejection_reason,

            # -------------------------
            # KYC Timeline
            # -------------------------
            "kyc_timeline": kyc_timeline
        }
    }