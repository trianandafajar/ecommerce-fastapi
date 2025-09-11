# app/utils/email.py
import os
import smtplib
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

MAIL_PROVIDER = os.getenv("MAIL_PROVIDER", "mailtrap").lower()

# Mailgun config
MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN")
MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY")

# Mailtrap SMTP config
MAILTRAP_HOST = os.getenv("MAILTRAP_HOST", "sandbox.smtp.mailtrap.io")
MAILTRAP_PORT = int(os.getenv("MAILTRAP_PORT", 2525))
MAILTRAP_USER = os.getenv("MAILTRAP_USER")
MAILTRAP_PASS = os.getenv("MAILTRAP_PASS")


def send_email(to_email: str, subject: str, html_body: str, from_email: str = None):
    """
    Kirim email menggunakan Mailgun API atau Mailtrap SMTP sesuai MAIL_PROVIDER
    """

    if MAIL_PROVIDER == "mailgun":
        if not MAILGUN_DOMAIN or not MAILGUN_API_KEY:
            raise RuntimeError("Mailgun env not configured")

        resp = requests.post(
            f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
            auth=("api", MAILGUN_API_KEY),
            data={
                "from": from_email or f"noreply@{MAILGUN_DOMAIN}",
                "to": [to_email],
                "subject": subject,
                "html": html_body,
            },
        )
        resp.raise_for_status()
        return resp.json()

    elif MAIL_PROVIDER == "mailtrap":
        if not MAILTRAP_USER or not MAILTRAP_PASS:
            raise RuntimeError("Mailtrap SMTP env not configured")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_email or "mailer.triananda@gmail.com"
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(MAILTRAP_HOST, MAILTRAP_PORT) as server:
            server.starttls()
            server.login(MAILTRAP_USER, MAILTRAP_PASS)
            server.sendmail(msg["From"], [to_email], msg.as_string())

        return {"status": "sent", "provider": "mailtrap"}

    else:
        raise ValueError(f"Unsupported MAIL_PROVIDER: {MAIL_PROVIDER}")
