from passlib.context import CryptContext
import random
import string
import random
from fastapi_mail import FastMail, MessageSchema
from email_config import conf

async def send_otp_email(
    email: str,
    otp: str
):
    message = MessageSchema(
        subject="Password Reset OTP",
        recipients=[email],
        body=f"Your OTP is {otp}",
        subtype="plain"
    )

    fm = FastMail(conf)

    await fm.send_message(message)



    

def generate_otp():
    return str(random.randint(100000, 999999))

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(
        plain_password,
        hashed_password
    )


def generate_referral_code():
    return ''.join(
        random.choices(
            string.ascii_uppercase + string.digits,
            k=8
        )
    )