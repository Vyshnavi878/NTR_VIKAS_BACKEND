import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, List, Dict, Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """
    Reusable email service for NTR Vikasa.
    Sends transactional emails via SMTP when configured, with mock/test capture support.
    """

    # Captured emails for test assertions
    sent_emails_history: List[Dict[str, Any]] = []

    @classmethod
    def send_password_reset_email(cls, to_email: str, reset_url: str) -> bool:
        """
        Send password reset link to user's registered email address.
        Security Note: The reset_url contains the sensitive token and must NEVER be logged.
        """
        subject = "Reset your NTR Vikasa password"

        plain_text_content = f"""Hi,

We received a request to reset your NTR Vikasa account password.

Click the link below to create a new password:
{reset_url}

This link will expire in {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.

If you did not request a password reset, you can safely ignore this email.

Regards,
NTR Vikasa
"""

        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{subject}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; color: #1e293b; margin: 0; padding: 24px; }}
    .container {{ max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; padding: 36px 32px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }}
    .header {{ text-align: center; margin-bottom: 28px; }}
    .logo-text {{ font-size: 24px; font-weight: 800; color: #0f172a; text-decoration: none; }}
    .btn {{ display: inline-block; background-color: #2563eb; color: #ffffff !important; font-size: 15px; font-weight: 600; text-decoration: none; padding: 12px 28px; border-radius: 8px; margin: 20px 0; }}
    .footer {{ font-size: 12px; color: #64748b; margin-top: 32px; border-top: 1px solid #f1f5f9; padding-top: 16px; text-align: center; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="logo-text">NTR VIKASA</div>
    </div>
    <p>Hi,</p>
    <p>We received a request to reset your NTR Vikasa account password.</p>
    <p>Click the button below to create a new password:</p>
    <p style="text-align: center;">
      <a href="{reset_url}" class="btn">Reset Password</a>
    </p>
    <p style="font-size: 13px; color: #64748b;">This link will expire in {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.</p>
    <p style="font-size: 13px; color: #64748b;">If you did not request a password reset, you can safely ignore this email.</p>
    <div class="footer">
      <p>Regards,<br><strong>NTR Vikasa Job Portal</strong></p>
    </div>
  </div>
</body>
</html>
"""

        # Record in test history (without exposing token in logs)
        cls.sent_emails_history.append({
            "to": to_email,
            "subject": subject,
            "has_reset_url": bool(reset_url),
        })

        # Send via SMTP if host is configured
        if settings.SMTP_HOST:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
                msg["To"] = to_email

                msg.attach(MIMEText(plain_text_content, "plain"))
                msg.attach(MIMEText(html_content, "html"))

                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                    if settings.SMTP_TLS:
                        server.starttls()
                    if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                    server.sendmail(settings.SMTP_FROM_EMAIL, [to_email], msg.as_string())
                logger.info("Password reset email sent to recipient: %s", to_email)
                return True
            except Exception as e:
                logger.error("Failed to send email to %s via SMTP: %s", to_email, str(e))
                return False
        else:
            # Development/Testing simulated delivery (never log the sensitive raw token)
            logger.info("Email service simulated delivery for recipient: %s", to_email)
            return True
