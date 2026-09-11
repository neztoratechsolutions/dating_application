from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func

from app.database import Base

class Gift(Base):
    __tablename__ = "gifts"

    id= Column(Integer,primary_key=True, index=True)

    sender_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable= False
    )

    receiver_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable= False
    )

    gift_name = Column(
        String,
        nullable= False
    )

    gift_image = Column(
        String,
        nullable= True
    )

    message = Column(
        String,
        nullable= True
    )

    status = Column(
        String,
        default="received"
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )
