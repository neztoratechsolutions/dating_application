from fastapi_mail import ConnectionConfig

conf = ConnectionConfig(
    MAIL_USERNAME="palanisamypreetha500@gmail.com",
    MAIL_PASSWORD="yybf efxm hvrv tdjr",
    MAIL_FROM="palanisamypreetha500@gmail.com",
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True
)