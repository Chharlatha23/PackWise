import smtplib
import logging
from typing import Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

logger = logging.getLogger(__name__)

WELCOME_EMAIL_SUBJECT = "Welcome to PackWise — Your Packaging Design Workspace"

def _build_welcome_email_body(user_name: str) -> str:
    name_display = user_name.strip() if user_name and user_name.strip() else "Researcher"
    return f"""Hello {name_display},

Welcome to PackWise!
We’re delighted to have you join us.

PackWise is an evidence-driven inverse-design decision-support platform developed to help explore sustainable food packaging solutions. By combining packaging requirements, material properties, scientific evaluation, and optimization, PackWise helps you assess packaging options with greater clarity.

Your account is now ready. You can begin exploring the platform, evaluate packaging scenarios, compare material options, and review scientifically assessed recommendations.

We’re excited to be part of your journey toward more informed and sustainable food packaging decisions.

Best regards,
The PackWise Team
foodpackai@gmail.com
"""

def send_welcome_email(to_email: str, user_name: str) -> bool:
    """
    Sends the official PackWise welcome email to newly created accounts.
    Fails safely without raising exceptions or exposing SMTP credentials.
    """
    if not settings.SMTP_HOST or not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        logger.warning("SMTP configuration incomplete; welcome email skipped for %s", to_email)
        return False

    sender_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME
    sender_name = "PackWise"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = WELCOME_EMAIL_SUBJECT
    msg["From"] = f"{sender_name} <{sender_email}>"
    msg["To"] = to_email

    body_text = _build_welcome_email_body(user_name)
    msg.attach(MIMEText(body_text, "plain", "utf-8"))

    try:
        if settings.SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
        else:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
            server.ehlo()
            server.starttls()
            server.ehlo()

        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.sendmail(sender_email, [to_email], msg.as_string())
        server.quit()
        logger.info("Welcome email successfully dispatched to %s", to_email)
        return True
    except Exception as e:
        logger.error("Failed to send welcome email to %s: %s", to_email, str(e))
        return False


def send_password_reset_email(to_email: str, reset_token: str, user_name: Optional[str] = None) -> bool:
    """
    Sends a secure password reset link to the registered user.
    """
    if not settings.SMTP_HOST or not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        logger.warning("SMTP configuration incomplete; reset email skipped for %s", to_email)
        return False

    sender_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME
    sender_name = "PackWise Security"

    frontend_base = settings.FRONTEND_URL.rstrip("/")
    reset_url = f"{frontend_base}/login?reset_token={reset_token}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "PackWise — Password Reset Request"
    msg["From"] = f"{sender_name} <{sender_email}>"
    msg["To"] = to_email

    name_str = f" {user_name}" if user_name else ""
    body_text = f"""Hello{name_str},

We received a request to reset your password for your PackWise account.

To set a new password, click the link below (valid for 30 minutes):
{reset_url}

If you did not request this password reset, please ignore this email. Your account remains secure.

Best regards,
PackWise Security Team
foodpackai@gmail.com
"""
    msg.attach(MIMEText(body_text, "plain", "utf-8"))

    try:
        if settings.SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
        else:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
            server.ehlo()
            server.starttls()
            server.ehlo()

        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.sendmail(sender_email, [to_email], msg.as_string())
        server.quit()
        logger.info("Password reset email sent to %s", to_email)
        return True
    except Exception as e:
        logger.error("Failed to send password reset email to %s: %s", to_email, str(e))
        return False
