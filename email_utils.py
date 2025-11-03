import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import settings

def send_email(to: str, subject: str, body: str):
    """Send an email using SMTP"""
    try:
        # Create message
        msg = MIMEMultipart()
        msg["From"] = settings.EMAIL_FROM
        msg["To"] = to
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))

        # Connect to the SMTP server
        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
            server.starttls()  # Enable encryption
            server.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
            server.send_message(msg)

        return {"status": "success", "message": f"Email sent to {to}"}

    except Exception as e:
        return {"status": "error", "message": str(e)}
