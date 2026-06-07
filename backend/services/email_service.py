import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, html_body: str) -> bool:
    """Send email via configured SMTP. Returns True on success."""
    if not settings.SMTP_USER or not settings.SMTP_PASS:
        logger.warning(f"SMTP credentials not set, skipping email to {to}")
        return False

    try:
        from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_SENDER_NAME} <{from_email}>"
        msg["To"] = to

        part = MIMEText(html_body, "html")
        msg.attach(part)

        timeout = 10  # 10 seconds timeout for SMTP operations

        if settings.SMTP_SECURE:
            logger.info(f"Connecting to SMTP via SSL: {settings.SMTP_HOST}:{settings.SMTP_PORT}")
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context, timeout=timeout) as server:
                server.login(settings.SMTP_USER, settings.SMTP_PASS)
                server.sendmail(from_email, to, msg.as_string())
        else:
            logger.info(f"Connecting to SMTP via STARTTLS: {settings.SMTP_HOST}:{settings.SMTP_PORT}")
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=timeout) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASS)
                server.sendmail(from_email, to, msg.as_string())

        logger.info(f"Email successfully sent to {to}: {subject}")
        return True
    except Exception as e:
        logger.error(f"CRITICAL: Email send failed to {to}. Error: {str(e)}", exc_info=True)
        return False


def send_approval_email(username: str, to_email: str) -> bool:
    subject = "Your Nexus Exchange Account Has Been Approved"
    html = f"""
    <div style="font-family:'Plus Jakarta Sans',Arial,sans-serif;max-width:560px;margin:0 auto;background:#0a0e17;color:#f0f4f8;padding:40px;border-radius:16px;">
      <div style="text-align:center;margin-bottom:32px;">
        <h1 style="background:linear-gradient(135deg,#00d4aa,#6366f1);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:28px;margin:0;">Nexus Exchange</h1>
        <span style="background:rgba(0,212,170,0.15);color:#00d4aa;border:1px solid #00d4aa;border-radius:999px;padding:2px 10px;font-size:11px;font-weight:700;letter-spacing:0.05em;">BETA</span>
      </div>
      <div style="background:#1a2035;border-radius:12px;padding:28px;border:1px solid #1e2a45;">
        <h2 style="color:#00d4aa;margin-top:0;">✅ Account Approved!</h2>
        <p style="color:#8899a6;line-height:1.7;">Hi <strong style="color:#f0f4f8;">{username}</strong>,</p>
        <p style="color:#8899a6;line-height:1.7;">Your account request for <strong style="color:#f0f4f8;">Nexus Exchange</strong> has been reviewed and approved by our admin team.</p>
        <p style="color:#8899a6;line-height:1.7;">You can now log in with your username and password that you set during signup.</p>
        <div style="text-align:center;margin:28px 0;">
          <a href="{settings.SITE_URL}" style="background:linear-gradient(135deg,#00d4aa,#6366f1);color:white;padding:14px 32px;border-radius:10px;text-decoration:none;font-weight:700;font-size:15px;display:inline-block;">Login to Nexus Exchange</a>
        </div>
        <hr style="border:none;border-top:1px solid #1e2a45;margin:20px 0;">
        <p style="color:#8899a6;font-size:13px;text-align:center;margin:0;">A product of <a href="https://patienceai.in" style="color:#00d4aa;">Patience AI</a></p>
      </div>
    </div>
    """
    return send_email(to_email, subject, html)


def send_rejection_email(username: str, to_email: str) -> bool:
    subject = "Your Nexus Exchange Account Request Status"
    html = f"""
    <div style="font-family:'Plus Jakarta Sans',Arial,sans-serif;max-width:560px;margin:0 auto;background:#0a0e17;color:#f0f4f8;padding:40px;border-radius:16px;">
      <div style="text-align:center;margin-bottom:32px;">
        <h1 style="background:linear-gradient(135deg,#00d4aa,#6366f1);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:28px;margin:0;">Nexus Exchange</h1>
      </div>
      <div style="background:#1a2035;border-radius:12px;padding:28px;border:1px solid #1e2a45;">
        <h2 style="color:#ef4444;margin-top:0;">Account Request Update</h2>
        <p style="color:#8899a6;line-height:1.7;">Hi <strong style="color:#f0f4f8;">{username}</strong>,</p>
        <p style="color:#8899a6;line-height:1.7;">After review, your access request for Nexus Exchange has not been approved at this time.</p>
        <p style="color:#8899a6;line-height:1.7;">If you believe this is an error, please contact us at <a href="mailto:{settings.CONTACT_TO_EMAIL}" style="color:#00d4aa;">{settings.CONTACT_TO_EMAIL}</a>.</p>
        <hr style="border:none;border-top:1px solid #1e2a45;margin:20px 0;">
        <p style="color:#8899a6;font-size:13px;text-align:center;margin:0;">A product of <a href="https://patienceai.in" style="color:#00d4aa;">Patience AI</a></p>
      </div>
    </div>
    """
    return send_email(to_email, subject, html)


def send_signup_notification_to_admin(username: str, admin_email: str) -> bool:
    subject = f"New Signup Request: {username}"
    html = f"""
    <div style="font-family:'Plus Jakarta Sans',Arial,sans-serif;max-width:560px;margin:0 auto;background:#0a0e17;color:#f0f4f8;padding:40px;border-radius:16px;">
      <div style="background:#1a2035;border-radius:12px;padding:28px;border:1px solid #1e2a45;">
        <h2 style="color:#f59e0b;margin-top:0;">🔔 New Signup Request</h2>
        <p style="color:#8899a6;line-height:1.7;">A new user has requested access to Nexus Exchange:</p>
        <p style="color:#f0f4f8;font-size:18px;font-weight:700;text-align:center;padding:16px;background:#0a0e17;border-radius:8px;">{username}</p>
        <div style="text-align:center;margin:28px 0;">
          <a href="{settings.SITE_URL}/admin" style="background:linear-gradient(135deg,#00d4aa,#6366f1);color:white;padding:14px 32px;border-radius:10px;text-decoration:none;font-weight:700;font-size:15px;display:inline-block;">Review in Admin Panel</a>
        </div>
      </div>
    </div>
    """
    return send_email(admin_email, subject, html)

def send_role_update_email(username: str, to_email: str, new_role: str) -> bool:
    subject = "Your Nexus Exchange Account Role Has Been Updated"
    html = f"""
    <div style="font-family:'Plus Jakarta Sans',Arial,sans-serif;max-width:560px;margin:0 auto;background:#0a0e17;color:#f0f4f8;padding:40px;border-radius:16px;">
      <div style="text-align:center;margin-bottom:32px;">
        <h1 style="background:linear-gradient(135deg,#00d4aa,#6366f1);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:28px;margin:0;">Nexus Exchange</h1>
      </div>
      <div style="background:#1a2035;border-radius:12px;padding:28px;border:1px solid #1e2a45;">
        <h2 style="color:#00d4aa;margin-top:0;">Account Role Updated</h2>
        <p style="color:#8899a6;line-height:1.7;">Hi <strong style="color:#f0f4f8;">{username}</strong>,</p>
        <p style="color:#8899a6;line-height:1.7;">Your account role has been successfully updated by an administrator.</p>
        <p style="color:#8899a6;line-height:1.7;">Your new role is: <strong style="color:#f0f4f8;text-transform:uppercase;">{new_role}</strong></p>
        <div style="text-align:center;margin:28px 0;">
          <a href="{settings.SITE_URL}" style="background:linear-gradient(135deg,#00d4aa,#6366f1);color:white;padding:14px 32px;border-radius:10px;text-decoration:none;font-weight:700;font-size:15px;display:inline-block;">Login to Nexus Exchange</a>
        </div>
        <hr style="border:none;border-top:1px solid #1e2a45;margin:20px 0;">
        <p style="color:#8899a6;font-size:13px;text-align:center;margin:0;">A product of <a href="https://patienceai.in" style="color:#00d4aa;">Patience AI</a></p>
      </div>
    </div>
    """
    return send_email(to_email, subject, html)


def send_support_notification_to_admin(username: str, user_email: str, subject_text: str, message: str, admin_email: str) -> bool:
    subject = f"Support Request Received: {subject_text}"
    html = f"""
    <div style=\"font-family:Arial,sans-serif;max-width:560px;margin:0 auto;background:#0a0e17;color:#f0f4f8;padding:24px;border-radius:12px;\">
      <h2 style=\"color:#00d4aa;\">New Support Request</h2>
      <p><strong>User:</strong> {username or 'Anonymous'}</p>
      <p><strong>Email:</strong> {user_email or 'Not provided'}</p>
      <p><strong>Subject:</strong> {subject_text}</p>
      <p><strong>Message:</strong></p>
      <div style=\"background:#1a2035;padding:12px;border-radius:8px;white-space:pre-wrap;\">{message}</div>
      <hr style=\"border:none;border-top:1px solid #1e2a45;margin:16px 0;\">
      <p style=\"font-size:13px;\">support@patienceai.in</p>
    </div>
    """
    return send_email(admin_email, subject, html)
