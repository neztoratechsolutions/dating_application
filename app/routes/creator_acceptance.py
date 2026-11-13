
import os
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db

from models.users import User
from models.cms_models import CreatorAgreement
from models.creator_agreement_acceptance import (
    CreatorAgreementAcceptance
)

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer
)


router = APIRouter(
    prefix="/creator-agreements",
    tags=["Creator Agreement Acceptance"]
)


# ==========================================================
# GENERATE CREATOR AGREEMENT PDF
# ==========================================================

def generate_agreement_pdf(agreement, creator_id):

    folder = "uploads/creator_agreements"

    os.makedirs(folder, exist_ok=True)

    filename = (
        f"creator_{creator_id}_agreement_{agreement.id}.pdf"
    )

    file_path = os.path.join(folder, filename)

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50
    )

    styles = getSampleStyleSheet()

    content = []

    content.append(
        Paragraph(
            "CREATOR AGREEMENT",
            styles["Title"]
        )
    )

    content.append(Spacer(1, 25))

    agreement_text = escape(agreement.details or "")
    agreement_text = agreement_text.replace("\n", "<br/>")

    content.append(
        Paragraph(
            agreement_text,
            styles["BodyText"]
        )
    )

    doc.build(content)

    return file_path


# ==========================================================
# ACCEPT CREATOR AGREEMENT
# ==========================================================

@router.post("/{agreement_id}/accept/{creator_id}")
def accept_creator_agreement(
    agreement_id: int,
    creator_id: int,
    request: Request,
    db: Session = Depends(get_db)
):

    try:

        # ==================================================
        # CHECK CREATOR
        # ==================================================

        creator = db.query(User).filter(
            User.id == creator_id,
            User.role == "creator"
        ).first()

        if not creator:

            raise HTTPException(
                status_code=404,
                detail="Creator not found"
            )

        # ==================================================
        # CHECK AGREEMENT
        # ==================================================

        agreement = db.query(
            CreatorAgreement
        ).filter(
            CreatorAgreement.id == agreement_id,
            CreatorAgreement.status == True
        ).first()

        if not agreement:

            raise HTTPException(
                status_code=404,
                detail="Creator agreement not found or inactive"
            )

        # ==================================================
        # CHECK EXISTING ACCEPTANCE
        # ==================================================

        existing_acceptance = db.query(
            CreatorAgreementAcceptance
        ).filter(
            CreatorAgreementAcceptance.creator_id == creator_id,
            CreatorAgreementAcceptance.agreement_id == agreement_id
        ).first()

        # ==================================================
        # GET IP ADDRESS
        # ==================================================

        client_ip = None

        if request.client:
            client_ip = request.client.host

        # ==================================================
        # ALREADY ACCEPTED
        # ==================================================

        if existing_acceptance:

            if existing_acceptance.status == "Accepted":

                # Generate PDF if not already available
                if not existing_acceptance.agreement_pdf:

                    existing_acceptance.agreement_pdf = (
                        generate_agreement_pdf(
                            agreement,
                            creator_id
                        )
                    )

                    db.commit()
                    db.refresh(existing_acceptance)

                return {
                    "status": True,
                    "message": "Creator agreement already accepted",
                    "creator_id": creator_id,
                    "agreement_id": agreement_id,
                    "acceptance_id": existing_acceptance.id,
                    "agreement_status": existing_acceptance.status,
                    "accepted_at": existing_acceptance.accepted_at,
                    "ip_address": existing_acceptance.ip_address,
                    "agreement_pdf_url": (
                        "/uploads/" +
                        existing_acceptance.agreement_pdf.replace("\\", "/").replace("uploads/", "", 1)
                    )
                }

            # ==============================================
            # UPDATE EXISTING ACCEPTANCE
            # ==============================================

            existing_acceptance.status = "Accepted"
            existing_acceptance.ip_address = client_ip
            existing_acceptance.accepted_at = datetime.now(timezone.utc)

            existing_acceptance.agreement_pdf = (
                generate_agreement_pdf(
                    agreement,
                    creator_id
                )
            )

            db.commit()
            db.refresh(existing_acceptance)

            return {
                "status": True,
                "message": "Creator agreement accepted successfully",
                "creator_id": creator_id,
                "agreement_id": agreement_id,
                "acceptance_id": existing_acceptance.id,
                "agreement_status": existing_acceptance.status,
                "accepted_at": existing_acceptance.accepted_at,
                "ip_address": existing_acceptance.ip_address,
                "agreement_pdf_url": (
                    "/uploads/" +
                    existing_acceptance.agreement_pdf.replace("\\", "/").replace("uploads/", "", 1)
                )
            }

        # ==================================================
        # CREATE ACCEPTANCE
        # ==================================================

        acceptance = CreatorAgreementAcceptance(
            creator_id=creator_id,
            agreement_id=agreement_id,
            status="Accepted",
            ip_address=client_ip,
            accepted_at=datetime.now(timezone.utc),
            agreement_pdf=generate_agreement_pdf(
                agreement,
                creator_id
            )
        )

        db.add(acceptance)

        db.commit()

        db.refresh(acceptance)

        # ==================================================
        # RESPONSE
        # ==================================================

        return {
            "status": True,
            "message": "Creator agreement accepted successfully",
            "creator_id": creator_id,
            "agreement_id": agreement_id,
            "acceptance_id": acceptance.id,
            "agreement_status": acceptance.status,
            "accepted_at": acceptance.accepted_at,
            "ip_address": acceptance.ip_address,
            "agreement_pdf_url": (
                "/uploads/" +
                acceptance.agreement_pdf.replace("\\", "/").replace("uploads/", "", 1)
            )
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to accept creator agreement: {str(e)}"
        )
