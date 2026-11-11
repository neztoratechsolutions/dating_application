# import os
# import uuid
# import csv
# import io

# from fastapi.responses import StreamingResponse

# from datetime import datetime, date, time, timedelta

# from fastapi import (
#     APIRouter,
#     Depends,
#     File,
#     Form,
#     HTTPException,
#     Query,
#     UploadFile,
#     status
# )

# from sqlalchemy import or_
# from sqlalchemy.orm import Session

# from database import get_db

# from models.kyc_detail import KYCDetail, CreatorKYC
# from models.users import User
# from models.state import State

# from schemas.kyc_details import (
#     KYCResponse,
#     KYCAdminResponse,
#     KYCDocumentStatusUpdate,
#     KYCOverallStatusUpdate,
#     KYCDashboardSummary
# )


# router = APIRouter(
#     prefix="/admin/kyc",
#     tags=["Admin KYC"]
# )


# # ==========================================================
# # UPLOAD DIRECTORY
# # ==========================================================

# UPLOAD_DIR = "uploads/kyc"

# os.makedirs(
#     UPLOAD_DIR,
#     exist_ok=True
# )


# # ==========================================================
# # ALLOWED STATUS
# # ==========================================================

# ALLOWED_DOCUMENT_STATUS = {
#     "Pending",
#     "Under Review",
#     "Verified",
#     "Rejected",
#     "Re-upload"
# }


# ALLOWED_OVERALL_STATUS = {
#     "Pending",
#     "Under Review",
#     "Approved",
#     "Rejected",
#     "Re-upload Required"
# }


# # ==========================================================
# # SAVE FILE
# # ==========================================================

# def save_file(file: UploadFile) -> str:

#     extension = os.path.splitext(
#         file.filename or ""
#     )[1]

#     file_name = (
#         f"{uuid.uuid4().hex}"
#         f"{extension}"
#     )

#     file_path = os.path.join(
#         UPLOAD_DIR,
#         file_name
#     )

#     with open(
#         file_path,
#         "wb"
#     ) as buffer:

#         buffer.write(
#             file.file.read()
#         )

#     return file_path.replace(
#         "\\",
#         "/"
#     )


# # ==========================================================
# # CALCULATE OVERALL STATUS
# # ==========================================================

# def calculate_overall_status(
#     aadhar_status: str,
#     pan_status: str,
#     selfie_status: str
# ) -> str:

#     document_statuses = [
#         aadhar_status,
#         pan_status,
#         selfie_status
#     ]

#     # ------------------------------------------------------
#     # ANY REJECTED
#     # ------------------------------------------------------

#     if "Rejected" in document_statuses:

#         return "Rejected"

#     # ------------------------------------------------------
#     # ANY RE-UPLOAD
#     # ------------------------------------------------------

#     if "Re-upload" in document_statuses:

#         return "Re-upload Required"

#     # ------------------------------------------------------
#     # ALL VERIFIED
#     # ------------------------------------------------------

#     if all(
#         value == "Verified"
#         for value in document_statuses
#     ):

#         return "Approved"

#     # ------------------------------------------------------
#     # ANY UNDER REVIEW
#     # ------------------------------------------------------

#     if "Under Review" in document_statuses:

#         return "Under Review"

#     # ------------------------------------------------------
#     # DEFAULT
#     # ------------------------------------------------------

#     return "Pending"


# # ==========================================================
# # CREATE KYC
# # ==========================================================

# @router.post(
#     "/",
#     response_model=KYCResponse,
#     status_code=status.HTTP_201_CREATED
# )
# def create_kyc(

#     user_id: int = Form(...),

#     aadhar_photo: UploadFile = File(...),

#     pan_photo: UploadFile = File(...),

#     selfie_photo: UploadFile = File(...),

#     db: Session = Depends(get_db)
# ):

#     # ------------------------------------------------------
#     # CHECK USER
#     # ------------------------------------------------------

#     user = (
#         db.query(User)
#         .filter(
#             User.id == user_id
#         )
#         .first()
#     )

#     if not user:

#         raise HTTPException(
#             status_code=404,
#             detail="User not found"
#         )

#     # ------------------------------------------------------
#     # ONLY CREATOR
#     # ------------------------------------------------------

#     if user.role != "creator":

#         raise HTTPException(
#             status_code=400,
#             detail="KYC can be submitted only for creator"
#         )

#     # ------------------------------------------------------
#     # CHECK EXISTING KYC
#     # ------------------------------------------------------

#     existing_kyc = (
#         db.query(KYCDetail)
#         .filter(
#             KYCDetail.user_id == user_id
#         )
#         .first()
#     )

#     if existing_kyc:

#         raise HTTPException(
#             status_code=400,
#             detail="KYC already submitted for this creator"
#         )

#     # ------------------------------------------------------
#     # SAVE FILES
#     # ------------------------------------------------------

#     aadhar_path = save_file(
#         aadhar_photo
#     )

#     pan_path = save_file(
#         pan_photo
#     )

#     selfie_path = save_file(
#         selfie_photo
#     )

#     # ------------------------------------------------------
#     # CREATE KYC
#     # ------------------------------------------------------

#     kyc = KYCDetail(

#         user_id=user_id,

#         aadhar_photo=aadhar_path,

#         pan_photo=pan_path,

#         selfie_photo=selfie_path,

#         aadhar_status="Pending",

#         pan_status="Pending",

#         selfie_status="Pending",

#         status="Pending",

#         rejection_reason=None
#     )

#     db.add(kyc)

#     db.commit()

#     db.refresh(kyc)

#     return kyc


# # ==========================================================
# # GET KYC DASHBOARD SUMMARY
# # ==========================================================

# @router.get(
#     "/dashboard/summary",
#     response_model=KYCDashboardSummary
# )
# def get_kyc_dashboard_summary(

#     db: Session = Depends(get_db)

# ):

#     # ------------------------------------------------------
#     # TOTAL CREATORS
#     # ------------------------------------------------------

#     total_creators = (
#         db.query(User)
#         .filter(
#             User.role == "creator"
#         )
#         .count()
#     )

#     # ------------------------------------------------------
#     # PENDING
#     # ------------------------------------------------------

#     pending_kyc = (
#         db.query(KYCDetail)
#         .join(
#             User,
#             User.id == KYCDetail.user_id
#         )
#         .filter(
#             User.role == "creator",
#             KYCDetail.status == "Pending"
#         )
#         .count()
#     )

#     # ------------------------------------------------------
#     # APPROVED
#     # ------------------------------------------------------

#     approved = (
#         db.query(KYCDetail)
#         .join(
#             User,
#             User.id == KYCDetail.user_id
#         )
#         .filter(
#             User.role == "creator",
#             KYCDetail.status == "Approved"
#         )
#         .count()
#     )

#     # ------------------------------------------------------
#     # REJECTED
#     # ------------------------------------------------------

#     rejected = (
#         db.query(KYCDetail)
#         .join(
#             User,
#             User.id == KYCDetail.user_id
#         )
#         .filter(
#             User.role == "creator",
#             KYCDetail.status == "Rejected"
#         )
#         .count()
#     )

#     # ------------------------------------------------------
#     # RE-UPLOAD
#     # ------------------------------------------------------

#     re_upload = (
#         db.query(KYCDetail)
#         .join(
#             User,
#             User.id == KYCDetail.user_id
#         )
#         .filter(
#             User.role == "creator",
#             KYCDetail.status == "Re-upload Required"
#         )
#         .count()
#     )

#     # ------------------------------------------------------
#     # COMPLETED TODAY
#     # ------------------------------------------------------

#     today = date.today()

#     completed_today = (
#         db.query(KYCDetail)
#         .join(
#             User,
#             User.id == KYCDetail.user_id
#         )
#         .filter(
#             User.role == "creator",

#             KYCDetail.updated_at >= datetime.combine(
#                 today,
#                 time.min
#             ),

#             KYCDetail.updated_at < datetime.combine(
#                 today + timedelta(days=1),
#                 time.min
#             ),

#             KYCDetail.status.in_([
#                 "Approved",
#                 "Rejected",
#                 "Re-upload Required"
#             ])
#         )
#         .count()
#     )

#     return KYCDashboardSummary(

#         total_creators=total_creators,

#         pending_kyc=pending_kyc,

#         approved=approved,

#         rejected=rejected,

#         re_upload=re_upload,

#         completed_today=completed_today
#     )


# # ==========================================================
# # GET ALL KYC
# # SEARCH + STATE + STATUS + DATE + PAGINATION
# # ==========================================================

# @router.get(
#     "/",
#     response_model=list[KYCAdminResponse]
# )
# def get_all_kyc(

#     search: str | None = Query(
#         None,
#         description="Search name, mobile, email or creator ID"
#     ),

#     state_id: int | None = Query(
#         None,
#         description="Filter by state"
#     ),

#     kyc_status: str | None = Query(
#         None,
#         description="Pending, Under Review, Approved, Rejected, Re-upload Required"
#     ),

#     start_date: date | None = Query(
#         None,
#         description="Filter KYC created date from this date"
#     ),

#     end_date: date | None = Query(
#         None,
#         description="Filter KYC created date up to this date"
#     ),

#     page: int = Query(
#         1,
#         ge=1,
#         description="Page number"
#     ),

#     limit: int = Query(
#         20,
#         ge=1,
#         le=100,
#         description="Records per page"
#     ),

#     db: Session = Depends(get_db)
# ):

#     # ------------------------------------------------------
#     # VALIDATE DATE RANGE
#     # ------------------------------------------------------

#     if start_date and end_date:

#         if start_date > end_date:

#             raise HTTPException(
#                 status_code=400,
#                 detail="start_date cannot be greater than end_date"
#             )

#     # ------------------------------------------------------
#     # BASE QUERY
#     # ------------------------------------------------------

#     query = (
#         db.query(
#             KYCDetail,
#             User,
#             State
#         )
#         .join(
#             User,
#             User.id == KYCDetail.user_id
#         )
#         .outerjoin(
#             State,
#             State.id == User.state_id
#         )
#         .filter(
#             User.role == "creator"
#         )
#     )

#     # ------------------------------------------------------
#     # SEARCH
#     # ------------------------------------------------------

#     if isinstance(search, str) and search.strip():

#         search_text = search.strip()

#         search_value = f"%{search_text}%"

#         creator_id_search = search_text.upper()

#         # --------------------------------------------------
#         # CREATOR ID
#         # Example: VLR00015
#         # --------------------------------------------------

#         if creator_id_search.startswith("VLR"):

#             numeric_part = (
#                 creator_id_search
#                 .replace("VLR", "", 1)
#             )

#             if numeric_part.isdigit():

#                 creator_user_id = int(
#                     numeric_part
#                 )

#                 query = query.filter(
#                     User.id == creator_user_id
#                 )

#             else:

#                 query = query.filter(
#                     or_(
#                         User.display_name.ilike(
#                             search_value
#                         ),

#                         User.email.ilike(
#                             search_value
#                         ),

#                         User.phone.ilike(
#                             search_value
#                         )
#                     )
#                 )

#         else:

#             query = query.filter(
#                 or_(
#                     User.display_name.ilike(
#                         search_value
#                     ),

#                     User.email.ilike(
#                         search_value
#                     ),

#                     User.phone.ilike(
#                         search_value
#                     )
#                 )
#             )

#     # ------------------------------------------------------
#     # STATE FILTER
#     # ------------------------------------------------------

#     if state_id is not None:

#         query = query.filter(
#             User.state_id == state_id
#         )

#     # ------------------------------------------------------
#     # STATUS FILTER
#     # ------------------------------------------------------

#     if isinstance(kyc_status, str) and kyc_status.strip():

#         if kyc_status not in ALLOWED_OVERALL_STATUS:

#             raise HTTPException(
#                 status_code=400,
#                 detail="Invalid KYC status"
#             )

#         query = query.filter(
#             KYCDetail.status == kyc_status
#         )

#     # ------------------------------------------------------
#     # START DATE FILTER
#     # ------------------------------------------------------

#     if start_date:

#         start_datetime = datetime.combine(
#             start_date,
#             time.min
#         )

#         query = query.filter(
#             KYCDetail.created_at >= start_datetime
#         )

#     # ------------------------------------------------------
#     # END DATE FILTER
#     # ------------------------------------------------------

#     if end_date:

#         next_day = end_date + timedelta(days=1)

#         end_datetime = datetime.combine(
#             next_day,
#             time.min
#         )

#         query = query.filter(
#             KYCDetail.created_at < end_datetime
#         )

#     # ------------------------------------------------------
#     # ORDER
#     # ------------------------------------------------------

#     query = query.order_by(
#         KYCDetail.created_at.desc()
#     )

#     # ------------------------------------------------------
#     # PAGINATION
#     # ------------------------------------------------------

#     offset = (page - 1) * limit

#     results = (
#         query
#         .offset(offset)
#         .limit(limit)
#         .all()
#     )

#     # ------------------------------------------------------
#     # NO DATA
#     # ------------------------------------------------------

#     if not results:

#         raise HTTPException(
#             status_code=404,
#             detail="KYC data not found"
#         )

#     # ------------------------------------------------------
#     # RESPONSE
#     # ------------------------------------------------------

#     response = []

#     for kyc, user, state in results:

#         response.append(

#             KYCAdminResponse(

#                 id=kyc.id,

#                 user_id=user.id,

#                 creator_id=f"VLR{user.id:05d}",

#                 display_name=user.display_name,

#                 email=user.email,

#                 phone=user.phone,

#                 state_id=user.state_id,

#                 state_name=(
#                     state.state_name
#                     if state
#                     else None
#                 ),

#                 profile_photo=user.profile_photo,

#                 joined_date=user.created_at,

#                 aadhar_photo=kyc.aadhar_photo,

#                 pan_photo=kyc.pan_photo,

#                 selfie_photo=kyc.selfie_photo,

#                 aadhar_status=kyc.aadhar_status,

#                 pan_status=kyc.pan_status,

#                 selfie_status=kyc.selfie_status,

#                 status=kyc.status,

#                 rejection_reason=(
#                     kyc.rejection_reason
#                 ),

#                 updated_at=kyc.updated_at
#             )
#         )

#     return response


# # ==========================================================
# # DOWNLOAD KYC CSV
# # ==========================================================

# @router.get(
#     "/download/csv"
# )
# def download_kyc_csv(

#     kyc_status: str = Query(
#         ...,
#         description="Approved, Pending, Rejected, Re-upload Required"
#     ),

#     search: str | None = Query(
#         None,
#         description="Search name, mobile, email or creator ID"
#     ),

#     state_id: int | None = Query(
#         None,
#         description="Filter by state"
#     ),

#     start_date: date | None = Query(
#         None,
#         description="Filter KYC created date from this date"
#     ),

#     end_date: date | None = Query(
#         None,
#         description="Filter KYC created date up to this date"
#     ),

#     db: Session = Depends(get_db)
# ):

#     # ------------------------------------------------------
#     # VALIDATE STATUS
#     # ------------------------------------------------------

#     if kyc_status not in ALLOWED_OVERALL_STATUS:

#         raise HTTPException(
#             status_code=400,
#             detail="Invalid KYC status"
#         )

#     # ------------------------------------------------------
#     # VALIDATE DATE
#     # ------------------------------------------------------

#     if start_date and end_date:

#         if start_date > end_date:

#             raise HTTPException(
#                 status_code=400,
#                 detail="start_date cannot be greater than end_date"
#             )

#     # ------------------------------------------------------
#     # BASE QUERY
#     # ------------------------------------------------------

#     query = (
#         db.query(
#             KYCDetail,
#             User,
#             State
#         )
#         .join(
#             User,
#             User.id == KYCDetail.user_id
#         )
#         .outerjoin(
#             State,
#             State.id == User.state_id
#         )
#         .filter(
#             User.role == "creator"
#         )
#     )

#     # ------------------------------------------------------
#     # STATUS
#     # ------------------------------------------------------

#     query = query.filter(
#         KYCDetail.status == kyc_status
#     )

#     # ------------------------------------------------------
#     # SEARCH
#     # ------------------------------------------------------

#     if isinstance(search, str) and search.strip():

#         search_text = search.strip()

#         search_value = f"%{search_text}%"

#         creator_id_search = search_text.upper()

#         if creator_id_search.startswith("VLR"):

#             numeric_part = (
#                 creator_id_search
#                 .replace("VLR", "", 1)
#             )

#             if numeric_part.isdigit():

#                 creator_user_id = int(
#                     numeric_part
#                 )

#                 query = query.filter(
#                     User.id == creator_user_id
#                 )

#             else:

#                 query = query.filter(
#                     or_(
#                         User.display_name.ilike(
#                             search_value
#                         ),

#                         User.email.ilike(
#                             search_value
#                         ),

#                         User.phone.ilike(
#                             search_value
#                         )
#                     )
#                 )

#         else:

#             query = query.filter(
#                 or_(
#                     User.display_name.ilike(
#                         search_value
#                     ),

#                     User.email.ilike(
#                         search_value
#                     ),

#                     User.phone.ilike(
#                         search_value
#                     )
#                 )
#             )

#     # ------------------------------------------------------
#     # STATE
#     # ------------------------------------------------------

#     if state_id is not None:

#         query = query.filter(
#             User.state_id == state_id
#         )

#     # ------------------------------------------------------
#     # START DATE
#     # ------------------------------------------------------

#     if start_date:

#         start_datetime = datetime.combine(
#             start_date,
#             time.min
#         )

#         query = query.filter(
#             KYCDetail.created_at >= start_datetime
#         )

#     # ------------------------------------------------------
#     # END DATE
#     # ------------------------------------------------------

#     if end_date:

#         next_day = end_date + timedelta(days=1)

#         end_datetime = datetime.combine(
#             next_day,
#             time.min
#         )

#         query = query.filter(
#             KYCDetail.created_at < end_datetime
#         )

#     # ------------------------------------------------------
#     # GET DATA
#     # ------------------------------------------------------

#     results = (
#         query
#         .order_by(
#             KYCDetail.created_at.desc()
#         )
#         .all()
#     )

#     if not results:

#         raise HTTPException(
#             status_code=404,
#             detail=f"No {kyc_status} KYC data found"
#         )

#     # ------------------------------------------------------
#     # CREATE CSV
#     # ------------------------------------------------------

#     output = io.StringIO()

#     writer = csv.writer(
#         output
#     )

#     # ------------------------------------------------------
#     # CSV HEADER
#     # ------------------------------------------------------

#     writer.writerow([
#         "KYC ID",
#         "User ID",
#         "Creator ID",
#         "Display Name",
#         "Email",
#         "Phone",
#         "State",
#         "Aadhaar Status",
#         "PAN Status",
#         "Selfie Status",
#         "KYC Status",
#         "Rejection Reason",
#         "Created Date",
#         "Updated Date"
#     ])

#     # ------------------------------------------------------
#     # CSV DATA
#     # ------------------------------------------------------

#     for kyc, user, state in results:

#         writer.writerow([

#             kyc.id,

#             user.id,

#             f"VLR{user.id:05d}",

#             user.display_name,

#             user.email,

#             user.phone,

#             (
#                 state.state_name
#                 if state
#                 else ""
#             ),

#             kyc.aadhar_status,

#             kyc.pan_status,

#             kyc.selfie_status,

#             kyc.status,

#             (
#                 kyc.rejection_reason
#                 if kyc.rejection_reason
#                 else ""
#             ),

#             (
#                 kyc.created_at.isoformat()
#                 if kyc.created_at
#                 else ""
#             ),

#             (
#                 kyc.updated_at.isoformat()
#                 if kyc.updated_at
#                 else ""
#             )
#         ])

#     # ------------------------------------------------------
#     # MOVE TO BEGINNING
#     # ------------------------------------------------------

#     output.seek(0)

#     # ------------------------------------------------------
#     # FILE NAME
#     # ------------------------------------------------------

#     status_file_name = (
#         kyc_status
#         .lower()
#         .replace(" ", "_")
#         .replace("-", "_")
#     )

#     file_name = (
#         f"kyc_{status_file_name}.csv"
#     )

#     # ------------------------------------------------------
#     # DOWNLOAD RESPONSE
#     # ------------------------------------------------------

#     return StreamingResponse(

#         iter([
#             output.getvalue()
#         ]),

#         media_type="text/csv",

#         headers={
#             "Content-Disposition":
#                 f'attachment; filename="{file_name}"'
#         }
#     )


# # ==========================================================
# # GET SINGLE KYC BY USER ID
# # ==========================================================

# @router.get(
#     "/user/{user_id}",
#     response_model=KYCAdminResponse
# )
# def get_kyc_by_user_id(

#     user_id: int,

#     db: Session = Depends(get_db)

# ):

#     result = (
#         db.query(
#             KYCDetail,
#             User,
#             State
#         )
#         .join(
#             User,
#             User.id == KYCDetail.user_id
#         )
#         .outerjoin(
#             State,
#             State.id == User.state_id
#         )
#         .filter(
#             KYCDetail.user_id == user_id,
#             User.role == "creator"
#         )
#         .first()
#     )

#     if not result:

#         raise HTTPException(
#             status_code=404,
#             detail="KYC data not found for this user"
#         )

#     kyc, user, state = result

#     return KYCAdminResponse(

#         id=kyc.id,

#         user_id=user.id,

#         creator_id=f"VLR{user.id:05d}",

#         display_name=user.display_name,

#         email=user.email,

#         phone=user.phone,

#         state_id=user.state_id,

#         state_name=(
#             state.state_name
#             if state
#             else None
#         ),

#         profile_photo=user.profile_photo,

#         joined_date=user.created_at,

#         aadhar_photo=kyc.aadhar_photo,

#         pan_photo=kyc.pan_photo,

#         selfie_photo=kyc.selfie_photo,

#         aadhar_status=kyc.aadhar_status,

#         pan_status=kyc.pan_status,

#         selfie_status=kyc.selfie_status,

#         status=kyc.status,

#         rejection_reason=(
#             kyc.rejection_reason
#         ),

#         updated_at=kyc.updated_at
#     )


# # ==========================================================
# # UPDATE DOCUMENT STATUS BY USER ID
# # ==========================================================

# @router.put(
#     "/user/{user_id}/document-status",
#     response_model=KYCResponse
# )
# def update_document_status(

#     user_id: int,

#     data: KYCDocumentStatusUpdate,

#     db: Session = Depends(get_db)

# ):

#     # ------------------------------------------------------
#     # FIND KYC USING USER ID
#     # ------------------------------------------------------

#     kyc = (
#         db.query(KYCDetail)
#         .filter(
#             KYCDetail.user_id == user_id
#         )
#         .first()
#     )

#     if not kyc:

#         raise HTTPException(
#             status_code=404,
#             detail="KYC data not found for this user"
#         )

#     # ------------------------------------------------------
#     # AADHAAR
#     # ------------------------------------------------------

#     if data.aadhar_status is not None:

#         if (
#             data.aadhar_status
#             not in ALLOWED_DOCUMENT_STATUS
#         ):

#             raise HTTPException(
#                 status_code=400,
#                 detail="Invalid Aadhaar status"
#             )

#         kyc.aadhar_status = (
#             data.aadhar_status
#         )

#     # ------------------------------------------------------
#     # PAN
#     # ------------------------------------------------------

#     if data.pan_status is not None:

#         if (
#             data.pan_status
#             not in ALLOWED_DOCUMENT_STATUS
#         ):

#             raise HTTPException(
#                 status_code=400,
#                 detail="Invalid PAN status"
#             )

#         kyc.pan_status = (
#             data.pan_status
#         )

#     # ------------------------------------------------------
#     # SELFIE
#     # ------------------------------------------------------

#     if data.selfie_status is not None:

#         if (
#             data.selfie_status
#             not in ALLOWED_DOCUMENT_STATUS
#         ):

#             raise HTTPException(
#                 status_code=400,
#                 detail="Invalid Selfie status"
#             )

#         kyc.selfie_status = (
#             data.selfie_status
#         )

#     # ------------------------------------------------------
#     # REJECTION REASON
#     # ------------------------------------------------------

#     if data.rejection_reason is not None:

#         kyc.rejection_reason = (
#             data.rejection_reason
#         )

#     # ------------------------------------------------------
#     # AUTOMATIC OVERALL STATUS
#     # ------------------------------------------------------

#     kyc.status = calculate_overall_status(

#         kyc.aadhar_status,

#         kyc.pan_status,

#         kyc.selfie_status
#     )

#     db.commit()

#     db.refresh(kyc)

#     return kyc


# # ==========================================================
# # UPDATE OVERALL KYC STATUS BY USER ID
# # ==========================================================

# @router.put(
#     "/user/{user_id}/status",
#     response_model=KYCResponse
# )
# def update_kyc_status(

#     user_id: int,

#     data: KYCOverallStatusUpdate,

#     db: Session = Depends(get_db)

# ):

#     # ------------------------------------------------------
#     # FIND KYC USING USER ID
#     # ------------------------------------------------------

#     kyc = (
#         db.query(KYCDetail)
#         .filter(
#             KYCDetail.user_id == user_id
#         )
#         .first()
#     )

#     if not kyc:

#         raise HTTPException(
#             status_code=404,
#             detail="KYC data not found for this user"
#         )

#     # ------------------------------------------------------
#     # VALIDATE STATUS
#     # ------------------------------------------------------

#     if data.status not in ALLOWED_OVERALL_STATUS:

#         raise HTTPException(
#             status_code=400,
#             detail="Invalid KYC status"
#         )

#     kyc.status = data.status

#     # ------------------------------------------------------
#     # REJECTION REASON
#     # ------------------------------------------------------

#     if data.rejection_reason is not None:

#         kyc.rejection_reason = (
#             data.rejection_reason
#         )

#     db.commit()

#     db.refresh(kyc)

#     return kyc


# # ==========================================================
# # DELETE KYC BY USER ID
# # ==========================================================

# @router.delete(
#     "/user/{user_id}",
#     status_code=status.HTTP_200_OK
# )
# def delete_kyc(

#     user_id: int,

#     db: Session = Depends(get_db)

# ):

#     # ------------------------------------------------------
#     # FIND KYC USING USER ID
#     # ------------------------------------------------------

#     kyc = (
#         db.query(KYCDetail)
#         .filter(
#             KYCDetail.user_id == user_id
#         )
#         .first()
#     )

#     if not kyc:

#         raise HTTPException(
#             status_code=404,
#             detail="KYC data not found for this user"
#         )

#     # ------------------------------------------------------
#     # DELETE UPLOADED FILES
#     # ------------------------------------------------------

#     files = [
#         kyc.aadhar_photo,
#         kyc.pan_photo,
#         kyc.selfie_photo
#     ]

#     for file_path in files:

#         if file_path and os.path.exists(file_path):

#             try:

#                 os.remove(file_path)

#             except OSError:

#                 pass

#     # ------------------------------------------------------
#     # DELETE KYC RECORD
#     # ------------------------------------------------------

#     db.delete(kyc)

#     db.commit()

#     # ------------------------------------------------------
#     # RESPONSE
#     # ------------------------------------------------------

#     return {
#         "message": "KYC deleted successfully",
#         "user_id": user_id
#     }


# # ==========================================================
# # RE-UPLOAD KYC DOCUMENTS BY USER ID
# # ==========================================================

# @router.put(
#     "/user/{user_id}/re-upload",
#     response_model=KYCResponse
# )
# def re_upload_kyc(

#     user_id: int,

#     aadhar_photo: UploadFile | None = File(None),

#     pan_photo: UploadFile | None = File(None),

#     selfie_photo: UploadFile | None = File(None),

#     db: Session = Depends(get_db)

# ):

#     # ------------------------------------------------------
#     # FIND KYC USING USER ID
#     # ------------------------------------------------------

#     kyc = (
#         db.query(KYCDetail)
#         .filter(
#             KYCDetail.user_id == user_id
#         )
#         .first()
#     )

#     if not kyc:

#         raise HTTPException(
#             status_code=404,
#             detail="KYC data not found for this user"
#         )

#     uploaded = False

#     # ------------------------------------------------------
#     # AADHAAR
#     # ------------------------------------------------------

#     if aadhar_photo:

#         kyc.aadhar_photo = save_file(
#             aadhar_photo
#         )

#         kyc.aadhar_status = "Pending"

#         uploaded = True

#     # ------------------------------------------------------
#     # PAN
#     # ------------------------------------------------------

#     if pan_photo:

#         kyc.pan_photo = save_file(
#             pan_photo
#         )

#         kyc.pan_status = "Pending"

#         uploaded = True

#     # ------------------------------------------------------
#     # SELFIE
#     # ------------------------------------------------------

#     if selfie_photo:

#         kyc.selfie_photo = save_file(
#             selfie_photo
#         )

#         kyc.selfie_status = "Pending"

#         uploaded = True

#     # ------------------------------------------------------
#     # CHECK UPLOAD
#     # ------------------------------------------------------

#     if not uploaded:

#         raise HTTPException(
#             status_code=400,
#             detail="At least one document is required"
#         )

#     # ------------------------------------------------------
#     # AFTER RE-UPLOAD
#     # ------------------------------------------------------

#     kyc.status = calculate_overall_status(

#         kyc.aadhar_status,

#         kyc.pan_status,

#         kyc.selfie_status
#     )

#     kyc.rejection_reason = None

#     db.commit()

#     db.refresh(kyc)

#     return kyc




# @router.get("/review/{user_id}")
# def review_kyc(
#     user_id: int,
#     db: Session = Depends(get_db)
# ):
#     # -----------------------------
#     # Check User
#     # -----------------------------
#     user = db.query(User).filter(
#         User.id == user_id
#     ).first()

#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="User not found"
#         )

#     # -----------------------------
#     # Only Creator KYC Review
#     # -----------------------------
#     if user.role != "creator":
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="KYC review is available only for creator"
#         )

#     # -----------------------------
#     # Get KYC
#     # -----------------------------
#     kyc = db.query(KYCDetail).filter(
#         KYCDetail.user_id == user_id
#     ).first()

#     if not kyc:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="KYC data not found for this user"
#         )

#     # -----------------------------
#     # Get Creator Bank KYC
#     # -----------------------------
#     bank_kyc = db.query(CreatorKYC).filter(
#         CreatorKYC.user_id == user_id
#     ).first()

#     # -----------------------------
#     # Get State
#     # -----------------------------
#     state = None

#     if user.state_id:
#         state = db.query(State).filter(
#             State.id == user.state_id
#         ).first()

#     # -----------------------------
#     # Creator ID
#     # -----------------------------
#     creator_id = f"VLR{user.id:05d}"

#     # =====================================================
#     # KYC TIMELINE
#     # =====================================================

#     kyc_timeline = []

#     def get_file_uploaded_time(file_path):
#         """
#         Get uploaded file date/time from file modification time.
#         """
#         if not file_path:
#             return None

#         if not os.path.exists(file_path):
#             return None

#         return datetime.fromtimestamp(
#             os.path.getmtime(file_path)
#         ).astimezone()

#     # -----------------------------
#     # Signup completed
#     # -----------------------------
#     if user.created_at:
#         kyc_timeline.append({
#             "title": "Signup completed",
#             "date": user.created_at
#         })

#     # -----------------------------
#     # Aadhaar uploaded
#     # -----------------------------
#     aadhar_uploaded_at = get_file_uploaded_time(
#         kyc.aadhar_photo
#     )

#     if aadhar_uploaded_at:
#         kyc_timeline.append({
#             "title": "Aadhaar uploaded",
#             "date": aadhar_uploaded_at
#         })

#     # -----------------------------
#     # PAN uploaded
#     # -----------------------------
#     pan_uploaded_at = get_file_uploaded_time(
#         kyc.pan_photo
#     )

#     if pan_uploaded_at:
#         kyc_timeline.append({
#             "title": "PAN uploaded",
#             "date": pan_uploaded_at
#         })

#     # -----------------------------
#     # Selfie captured
#     # -----------------------------
#     selfie_uploaded_at = get_file_uploaded_time(
#         kyc.selfie_photo
#     )

#     if selfie_uploaded_at:
#         kyc_timeline.append({
#             "title": "Selfie captured",
#             "date": selfie_uploaded_at
#         })

#     # -----------------------------
#     # KYC submitted for review
#     # -----------------------------
#     if kyc.created_at:
#         kyc_timeline.append({
#             "title": "KYC submitted for review",
#             "date": kyc.created_at
#         })

#     # -----------------------------
#     # Sort Timeline
#     # -----------------------------
#     kyc_timeline.sort(
#         key=lambda x: x["date"]
#     )

#     # =====================================================
#     # RESPONSE
#     # =====================================================

#     return {
#         "status": 200,
#         "message": "KYC review details fetched successfully",
#         "data": {
#             "user_id": user.id,
#             "creator_id": creator_id,

#             # -------------------------
#             # Personal Details
#             # -------------------------
#             "personal_details": {
#                 "display_name": user.display_name,
#                 "phone": user.phone,
#                 "email": user.email,
#                 "state_id": user.state_id,
#                 "state_name": state.state_name if state else None,
#                 "profile_photo": user.profile_photo,
#                 "joined_date": user.created_at
#             },

#             # -------------------------
#             # Bank Details
#             # -------------------------
#             "bank_details": {
#                 "bank_photo": (
#                     bank_kyc.bank_photo
#                     if bank_kyc
#                     else None
#                 ),
#                 "bank_status": (
#                     bank_kyc.bank_status
#                     if bank_kyc
#                     else None
#                 ),
#                 "uploaded_at": (
#                     bank_kyc.created_at
#                     if bank_kyc
#                     else None
#                 ),
#                 "updated_at": (
#                     bank_kyc.updated_at
#                     if bank_kyc
#                     else None
#                 )
#             },

#             # -------------------------
#             # KYC Documents
#             # -------------------------
#             "documents": {
#                 "aadhar": {
#                     "photo": kyc.aadhar_photo,
#                     "status": kyc.aadhar_status
#                 },
#                 "pan": {
#                     "photo": kyc.pan_photo,
#                     "status": kyc.pan_status
#                 },
#                 "selfie": {
#                     "photo": kyc.selfie_photo,
#                     "status": kyc.selfie_status
#                 }
#             },

#             # -------------------------
#             # Overall KYC Status
#             # -------------------------
#             "kyc_status": kyc.status,

#             "rejection_reason": kyc.rejection_reason,

#             # -------------------------
#             # KYC Timeline
#             # -------------------------
#             "kyc_timeline": kyc_timeline
#         }
#     }


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
