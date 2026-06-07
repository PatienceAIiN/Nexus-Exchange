import logging
import httpx
from config import settings

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def send_email(to: str, subject: str, html_body: str) -> bool:
    """Send email via Brevo HTTP API. Returns True on success."""
    if not settings.BREVO_API_KEY:
        logger.warning(f"BREVO_API_KEY not set, skipping email to {to}")
        return False

    sender_email = settings.BREVO_SENDER_EMAIL or settings.SMTP_FROM_EMAIL
    if not sender_email:
        logger.warning(f"BREVO_SENDER_EMAIL not set, skipping email to {to}")
        return False

    payload = {
        "sender": {"name": settings.BREVO_SENDER_NAME, "email": sender_email},
        "to": [{"email": to}],
        "subject": subject,
        "htmlContent": html_body,
    }
    headers = {
        "api-key": settings.BREVO_API_KEY,
        "content-type": "application/json",
        "accept": "application/json",
    }

    try:
        logger.info(f"Sending email via Brevo API to {to}: {subject}")
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(BREVO_API_URL, json=payload, headers=headers)
        if resp.status_code in (200, 201, 202):
            logger.info(f"Email successfully sent to {to}: {subject} (messageId={resp.json().get('messageId')})")
            return True
        logger.error(f"CRITICAL: Brevo API send failed to {to}. Status={resp.status_code} Body={resp.text}")
        return False
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
