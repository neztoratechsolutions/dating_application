
from datetime import date, datetime, timedelta
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, cast, String

from database import get_db

from models.users import User
from models.state import State
from models.kyc_detail import KYCDetail
from models.creator_verify import CreatorVerification


router = APIRouter(
    prefix="/admin/kyc-dashboard",
    tags=["Admin KYC Dashboard"]
)


# ==========================================================
# COMMON HELPERS
# ==========================================================

def format_creator_id(user_id: int) -> str:
    return f"VLR{user_id:05d}"


def normalize_status(value, default="Pending"):
    if not value:
        return default

    value = str(value).strip().lower()

    status_mapping = {
        "pending": "Pending",
        "under review": "Under Review",
        "verified": "Verified",
        "approved": "Approved",
        "rejected": "Rejected",
        "re-upload": "Re-upload",
        "re-upload required": "Re-upload Required"
    }

    return status_mapping.get(value, value.title())


def get_aadhar_status(kyc):
    if not kyc:
        return "Pending"

    return normalize_status(kyc.aadhar_status)


def get_pan_status(kyc):
    if not kyc:
        return "Pending"

    return normalize_status(kyc.pan_status)


def get_selfie_status(verification):
    if not verification:
        return "Pending"

    # Selfie status comes from CreatorVerification
    return normalize_status(verification.selfie_status)


def get_overall_status(kyc):
    if not kyc:
        return "Pending"

    return normalize_status(kyc.status)


# ==========================================================
# BASE QUERY
# ==========================================================

def get_dashboard_query(db: Session):

    return (
        db.query(
            User,
            KYCDetail,
            CreatorVerification,
            State
        )
        .outerjoin(
            KYCDetail,
            KYCDetail.user_id == User.id
        )
        .outerjoin(
            CreatorVerification,
            CreatorVerification.creator_id == User.id
        )
        .outerjoin(
            State,
            State.id == User.state_id
        )
        .filter(
            User.role == "creator"
        )
    )


# ==========================================================
# COMMON FILTERS
# ==========================================================

def apply_dashboard_filters(
    query,
    search: Optional[str] = None,
    state_id: Optional[int] = None,
    kyc_status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):

    # Search
    if search:

        search_value = search.strip()

        search_filters = [
            User.display_name.ilike(f"%{search_value}%"),
            User.email.ilike(f"%{search_value}%"),
            User.phone.ilike(f"%{search_value}%"),
            cast(User.id, String).ilike(f"%{search_value}%")
        ]

        # Creator ID search: VLR10000
        creator_search = search_value.upper()

        if creator_search.startswith("VLR"):

            creator_number = creator_search[3:]

            if creator_number.isdigit():
                search_filters.append(
                    User.id == int(creator_number)
                )

        query = query.filter(
            or_(*search_filters)
        )

    # State filter
    if state_id is not None:
        query = query.filter(
            User.state_id == state_id
        )

    # Overall KYC status filter
    if kyc_status:

        query = query.filter(
            KYCDetail.status.ilike(
                kyc_status.strip()
            )
            if kyc_status.strip().lower() != "pending"
            else or_(
                KYCDetail.status.ilike("Pending"),
                KYCDetail.id.is_(None)
            )
        )

    # Joined date filter
    if start_date:

        query = query.filter(
            User.created_at >= datetime.combine(
                start_date,
                datetime.min.time()
            )
        )

    if end_date:

        next_day = end_date + timedelta(days=1)

        query = query.filter(
            User.created_at < datetime.combine(
                next_day,
                datetime.min.time()
            )
        )

    return query


# ==========================================================
# CREATOR RESPONSE
# ==========================================================

def build_creator_response(
    user,
    kyc,
    verification,
    state
):

    return {
        "id": kyc.id if kyc else None,

        "user_id": user.id,

        "creator_id": format_creator_id(user.id),

        "display_name": user.display_name,

        "email": user.email,

        "phone": user.phone,

        "state_id": user.state_id,

        "state_name": (
            state.state_name if state else None
        ),

        "profile_photo": user.profile_photo,

        "joined_date": user.created_at,

        "aadhar_photo": (
            kyc.aadhar_photo if kyc else None
        ),

        "pan_photo": (
            kyc.pan_photo if kyc else None
        ),

        "selfie_photo": (
            kyc.selfie_photo if kyc else None
        ),

        "aadhar_status": get_aadhar_status(kyc),

        "pan_status": get_pan_status(kyc),

        "selfie_status": get_selfie_status(verification),

        "status": get_overall_status(kyc),

        "rejection_reason": (
            kyc.rejection_reason if kyc else None
        ),

        "updated_at": (
            kyc.updated_at if kyc else user.updated_at
        ),

        # Risk calculation is not available in current models.
        "risk": None
    }


# ==========================================================
# GET ADMIN KYC DASHBOARD
# ==========================================================

@router.get("/")
def get_admin_kyc_dashboard(

    search: Optional[str] = Query(None),

    state_id: Optional[int] = Query(None),

    kyc_status: Optional[str] = Query(None),

    start_date: Optional[date] = Query(None),

    end_date: Optional[date] = Query(None),

    page: int = Query(1, ge=1),

    limit: int = Query(10, ge=1, le=100),

    db: Session = Depends(get_db)

):

    try:

        if start_date and end_date and start_date > end_date:
            raise HTTPException(
                status_code=400,
                detail="Start date cannot be greater than end date"
            )

        # --------------------------------------------------
        # DASHBOARD SUMMARY
        # --------------------------------------------------

        all_creators = get_dashboard_query(db).all()

        total_creators = len(all_creators)

        pending_kyc = 0
        approved = 0
        rejected = 0
        re_upload = 0
        completed_today = 0

        today = date.today()

        for user, kyc, verification, state in all_creators:

            status = get_overall_status(kyc)

            if status == "Pending":
                pending_kyc += 1

            elif status == "Approved":
                approved += 1

            elif status == "Rejected":
                rejected += 1

            elif status == "Re-upload Required":
                re_upload += 1

            if (
                kyc
                and kyc.updated_at
                and kyc.updated_at.date() == today
                and status in [
                    "Approved",
                    "Rejected",
                    "Re-upload Required"
                ]
            ):
                completed_today += 1

        summary = {
            "total_creators": total_creators,
            "pending_kyc": pending_kyc,
            "approved": approved,
            "rejected": rejected,
            "re_upload": re_upload,
            "completed_today": completed_today
        }

        # --------------------------------------------------
        # STATE FILTER OPTIONS
        # --------------------------------------------------

        states = (
            db.query(State)
            .filter(State.is_active == True)
            .order_by(State.state_name.asc())
            .all()
        )

        state_list = [
            {
                "id": state.id,
                "state_name": state.state_name
            }
            for state in states
        ]

        # --------------------------------------------------
        # CREATOR LIST
        # --------------------------------------------------

        query = get_dashboard_query(db)

        query = apply_dashboard_filters(
            query=query,
            search=search,
            state_id=state_id,
            kyc_status=kyc_status,
            start_date=start_date,
            end_date=end_date
        )

        total_records = query.count()

        total_pages = (
            (total_records + limit - 1) // limit
            if total_records else 0
        )

        offset = (page - 1) * limit

        records = (
            query
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        creator_list = []

        for user, kyc, verification, state in records:

            creator_list.append(
                build_creator_response(
                    user,
                    kyc,
                    verification,
                    state
                )
            )

        return {
            "success": True,

            "message": "KYC dashboard data fetched successfully",

            "summary": summary,

            "states": state_list,

            "filters": {
                "search": search,
                "state_id": state_id,
                "kyc_status": kyc_status,
                "start_date": start_date,
                "end_date": end_date
            },

            "pagination": {
                "page": page,
                "limit": limit,
                "total_records": total_records,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1
            },

            "creators": creator_list
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch KYC dashboard data: {str(e)}"
        )


# ==========================================================
# COMMON PDF GENERATOR
# ==========================================================

def generate_kyc_status_pdf(

    db: Session,

    status: str,

    search: Optional[str] = None,

    state_id: Optional[int] = None,

    start_date: Optional[date] = None,

    end_date: Optional[date] = None

):

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm

    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle
    )

    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="Start date cannot be greater than end date"
        )

    # ------------------------------------------------------
    # GET FILTERED RECORDS
    # No pagination for PDF.
    # ------------------------------------------------------

    query = get_dashboard_query(db)

    query = apply_dashboard_filters(
        query=query,
        search=search,
        state_id=state_id,
        kyc_status=status,
        start_date=start_date,
        end_date=end_date
    )

    records = (
        query
        .order_by(User.created_at.desc())
        .all()
    )

    # ------------------------------------------------------
    # CREATE PDF
    # ------------------------------------------------------

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=8 * mm,
        leftMargin=8 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm
    )

    styles = getSampleStyleSheet()

    elements = []

    elements.append(
        Paragraph(
            f"Creator KYC - {status} Report",
            styles["Title"]
        )
    )

    elements.append(Spacer(1, 5 * mm))

    elements.append(
        Paragraph(
            f"Generated Date: {datetime.now().strftime('%d-%m-%Y %H:%M')}",
            styles["Normal"]
        )
    )

    elements.append(
        Paragraph(
            f"Total Records: {len(records)}",
            styles["Normal"]
        )
    )

    if state_id:

        state = (
            db.query(State)
            .filter(State.id == state_id)
            .first()
        )

        if state:
            elements.append(
                Paragraph(
                    f"State: {state.state_name}",
                    styles["Normal"]
                )
            )

    if search:
        elements.append(
            Paragraph(
                f"Search: {search}",
                styles["Normal"]
            )
        )

    if start_date:
        elements.append(
            Paragraph(
                f"Start Date: {start_date}",
                styles["Normal"]
            )
        )

    if end_date:
        elements.append(
            Paragraph(
                f"End Date: {end_date}",
                styles["Normal"]
            )
        )

    elements.append(Spacer(1, 5 * mm))

    # ------------------------------------------------------
    # PDF TABLE
    # ------------------------------------------------------

    table_data = [[
        "Creator",
        "Creator ID",
        "Email",
        "Mobile",
        "State",
        "Joined",
        "Aadhaar",
        "PAN",
        "Selfie",
        "Status"
    ]]

    for user, kyc, verification, state in records:

        table_data.append([

            user.display_name or "-",

            format_creator_id(user.id),

            user.email or "-",

            user.phone or "-",

            state.state_name if state else "-",

            (
                user.created_at.strftime("%d-%m-%Y")
                if user.created_at else "-"
            ),

            get_aadhar_status(kyc),

            get_pan_status(kyc),

            get_selfie_status(verification),

            get_overall_status(kyc)
        ])

    if len(table_data) == 1:

        table_data.append([
            "No records found",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            ""
        ])

    report_table = Table(
        table_data,
        repeatRows=1,
        colWidths=[
            27 * mm,
            20 * mm,
            40 * mm,
            23 * mm,
            25 * mm,
            20 * mm,
            19 * mm,
            19 * mm,
            19 * mm,
            25 * mm
        ]
    )

    report_table.setStyle(
        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#263B5A")
            ),

            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),

            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),

            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                7
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.4,
                colors.grey
            ),

            (
                "ALIGN",
                (0, 0),
                (-1, -1),
                "CENTER"
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            ),

            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [
                    colors.white,
                    colors.HexColor("#F2F5F9")
                ]
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                6
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                6
            )

        ])
    )

    elements.append(report_table)

    document.build(elements)

    buffer.seek(0)

    filename = (
        f"creator_kyc_{status.lower().replace(' ', '_')}_"
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    )

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            )
        }
    )


# ==========================================================
# APPROVED PDF DOWNLOAD
# ==========================================================

@router.get("/export/approved/pdf")
def download_approved_kyc_pdf(

    search: Optional[str] = Query(None),

    state_id: Optional[int] = Query(None),

    start_date: Optional[date] = Query(None),

    end_date: Optional[date] = Query(None),

    db: Session = Depends(get_db)

):

    return generate_kyc_status_pdf(
        db=db,
        status="Approved",
        search=search,
        state_id=state_id,
        start_date=start_date,
        end_date=end_date
    )


# ==========================================================
# PENDING PDF DOWNLOAD
# ==========================================================

@router.get("/export/pending/pdf")
def download_pending_kyc_pdf(

    search: Optional[str] = Query(None),

    state_id: Optional[int] = Query(None),

    start_date: Optional[date] = Query(None),

    end_date: Optional[date] = Query(None),

    db: Session = Depends(get_db)

):

    return generate_kyc_status_pdf(
        db=db,
        status="Pending",
        search=search,
        state_id=state_id,
        start_date=start_date,
        end_date=end_date
    )


# ==========================================================
# REJECTED PDF DOWNLOAD
# ==========================================================

@router.get("/export/rejected/pdf")
def download_rejected_kyc_pdf(

    search: Optional[str] = Query(None),

    state_id: Optional[int] = Query(None),

    start_date: Optional[date] = Query(None),

    end_date: Optional[date] = Query(None),

    db: Session = Depends(get_db)

):

    return generate_kyc_status_pdf(
        db=db,
        status="Rejected",
        search=search,
        state_id=state_id,
        start_date=start_date,
        end_date=end_date
    )


# ==========================================================
# RE-UPLOAD PDF DOWNLOAD
# ==========================================================

@router.get("/export/re-upload/pdf")
def download_reupload_kyc_pdf(

    search: Optional[str] = Query(None),

    state_id: Optional[int] = Query(None),

    start_date: Optional[date] = Query(None),

    end_date: Optional[date] = Query(None),

    db: Session = Depends(get_db)

):

    return generate_kyc_status_pdf(
        db=db,
        status="Re-upload Required",
        search=search,
        state_id=state_id,
        start_date=start_date,
        end_date=end_date
    )
