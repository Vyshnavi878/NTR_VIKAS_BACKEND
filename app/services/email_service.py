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

    @classmethod
    def send_interview_invitation_email(
        cls,
        to_email: str,
        candidate_name: str,
        job_title: str,
        scheduled_date: str,
        start_time: str,
        end_time: Optional[str] = None,
        timezone: str = "Asia/Kolkata",
        format_type: str = "ONLINE",
        meeting_link: Optional[str] = None,
        venue: Optional[str] = None,
        interviewer_panel: Optional[List[str]] = None,
        agenda_notes: Optional[str] = None,
    ) -> bool:
        """
        Send interview invitation email to candidate.
        Gracefully handles unconfigured SMTP without blocking interview scheduling.
        """
        time_display = f"{start_time} - {end_time} {timezone}" if end_time else f"{start_time} {timezone}"
        subject = f"Interview Scheduled: {job_title} - NTR Vikasa"

        panel_display = ", ".join(interviewer_panel) if interviewer_panel else "Interview Evaluation Panel"
        location_display = f"Meeting Link: {meeting_link}" if format_type == "ONLINE" and meeting_link else (f"Venue: {venue}" if venue else "Online Video Conference")

        plain_text = f"""Hi {candidate_name},

Your interview for {job_title} has been scheduled.

Interview Details:
- Date: {scheduled_date}
- Time: {time_display}
- Format: {format_type}
- {location_display}
- Interview Panel: {panel_display}
{f'- Notes: {agenda_notes}' if agenda_notes else ''}

Please be prepared 5 minutes before the scheduled time.

Best regards,
NTR Vikasa Recruitment Team
"""

        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{subject}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f8fafc; color: #1e293b; padding: 24px; }}
    .card {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 32px; }}
    .header {{ border-bottom: 2px solid #2563eb; padding-bottom: 16px; margin-bottom: 24px; }}
    .title {{ font-size: 20px; font-weight: 700; color: #0f172a; margin: 0; }}
    .detail-row {{ margin: 12px 0; font-size: 14px; line-height: 1.5; }}
    .label {{ font-weight: 600; color: #475569; width: 140px; display: inline-block; }}
    .btn {{ display: inline-block; background-color: #2563eb; color: #ffffff !important; padding: 10px 24px; border-radius: 6px; text-decoration: none; font-weight: 600; margin-top: 16px; }}
    .footer {{ margin-top: 32px; font-size: 12px; color: #64748b; border-top: 1px solid #f1f5f9; padding-top: 16px; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h2 class="title">Interview Invitation: {job_title}</h2>
    </div>
    <p>Dear {candidate_name},</p>
    <p>Your interview round has been scheduled. Below are your interview details:</p>
    
    <div class="detail-row"><span class="label">Job Role:</span> <strong>{job_title}</strong></div>
    <div class="detail-row"><span class="label">Date:</span> <strong>{scheduled_date}</strong></div>
    <div class="detail-row"><span class="label">Time:</span> <strong>{time_display}</strong></div>
    <div class="detail-row"><span class="label">Format:</span> <strong>{format_type}</strong></div>
    <div class="detail-row"><span class="label">Interview Panel:</span> {panel_display}</div>
    {f'<div class="detail-row"><span class="label">Agenda/Notes:</span> {agenda_notes}</div>' if agenda_notes else ''}

    {f'<p style="margin-top: 24px;"><a href="{meeting_link}" class="btn">Join Interview Meeting</a></p>' if format_type == "ONLINE" and meeting_link else (f'<div class="detail-row"><span class="label">Venue:</span> {venue}</div>' if venue else '')}

    <div class="footer">
      <p>Regards,<br><strong>NTR Vikasa Recruitment Portal</strong></p>
    </div>
  </div>
</body>
</html>
"""

        # Record in test history
        cls.sent_emails_history.append({
            "to": to_email,
            "subject": subject,
            "candidate_name": candidate_name,
            "job_title": job_title,
            "scheduled_date": scheduled_date,
            "start_time": start_time,
            "end_time": end_time,
            "format": format_type,
            "meeting_link": meeting_link,
            "venue": venue,
        })

        if settings.SMTP_HOST:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
                msg["To"] = to_email

                msg.attach(MIMEText(plain_text, "plain"))
                msg.attach(MIMEText(html_content, "html"))

                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                    if settings.SMTP_TLS:
                        server.starttls()
                    if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                    server.sendmail(settings.SMTP_FROM_EMAIL, [to_email], msg.as_string())
                logger.info("Interview invite email delivered to: %s", to_email)
                return True
            except Exception as e:
                logger.error("Failed to send interview invite email to %s via SMTP: %s", to_email, str(e))
                return False
        else:
            logger.info("Simulated interview invite email sent to: %s", to_email)
            return True

    @classmethod
    def send_team_invitation_email(
        cls,
        to_email: str,
        full_name: str,
        company_name: str,
        role: str,
        inviter_name: str,
        invite_url: str,
    ) -> bool:
        """
        Send recruiter team invitation email.
        Contains company name, invited role, inviter name, and secure invitation link.
        """
        subject = f"Invitation to join {company_name} on NTR Vikasa"

        plain_text_content = f"""Hi {full_name},

You have been invited to join {company_name} as {role}.
Invited by: {inviter_name}

To accept this invitation and set up your account password, click the link below:
{invite_url}

This invitation link is valid for 48 hours.

Regards,
NTR Vikasa Recruitment Portal
"""

        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{subject}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; color: #1e293b; margin: 0; padding: 24px; }}
    .container {{ max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; padding: 36px 32px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }}
    .header {{ text-align: center; margin-bottom: 24px; }}
    .logo-text {{ font-size: 22px; font-weight: 800; color: #0f172a; text-decoration: none; }}
    .badge {{ display: inline-block; background-color: #eff6ff; color: #1d4ed8; font-size: 13px; font-weight: 700; padding: 4px 12px; border-radius: 9999px; margin-bottom: 16px; }}
    .details-box {{ background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px 20px; margin: 20px 0; }}
    .detail-row {{ display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px; }}
    .detail-label {{ color: #64748b; font-weight: 500; }}
    .detail-val {{ font-weight: 600; color: #0f172a; }}
    .btn {{ display: inline-block; background-color: #2563eb; color: #ffffff !important; font-size: 15px; font-weight: 600; text-decoration: none; padding: 12px 28px; border-radius: 8px; margin: 20px 0; text-align: center; }}
    .footer {{ font-size: 12px; color: #64748b; margin-top: 32px; border-top: 1px solid #f1f5f9; padding-top: 16px; text-align: center; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="logo-text">NTR VIKASA</div>
    </div>
    <div style="text-align: center;">
      <span class="badge">Team Invitation</span>
      <h2 style="margin: 0 0 12px 0; font-size: 20px; color: #0f172a;">Join {company_name}</h2>
      <p style="margin: 0; color: #475569; font-size: 15px;">Hello {full_name}, you have been invited to collaborate on hiring.</p>
    </div>

    <div class="details-box">
      <div class="detail-row">
        <span class="detail-label">Company:</span>
        <span class="detail-val">{company_name}</span>
      </div>
      <div class="detail-row">
        <span class="detail-label">Role:</span>
        <span class="detail-val">{role}</span>
      </div>
      <div class="detail-row" style="margin-bottom: 0;">
        <span class="detail-label">Invited By:</span>
        <span class="detail-val">{inviter_name}</span>
      </div>
    </div>

    <div style="text-align: center;">
      <a href="{invite_url}" class="btn">Accept Invitation</a>
      <p style="font-size: 13px; color: #64748b; margin-top: 8px;">Link valid for 48 hours. Sets up your secure credentials.</p>
    </div>

    <div class="footer">
      <p>Regards,<br><strong>NTR Vikasa Recruitment Portal</strong></p>
    </div>
  </div>
</body>
</html>
"""

        cls.sent_emails_history.append({
            "to": to_email,
            "subject": subject,
            "has_invite_url": bool(invite_url),
            "role": role,
            "company_name": company_name,
        })

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
                logger.info("Team invitation email sent to: %s", to_email)
                return True
            except Exception as e:
                logger.error("Failed to send team invitation email to %s via SMTP: %s", to_email, str(e))
                return False
        else:
            logger.info("Simulated team invitation email sent to: %s", to_email)
            return True

