from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import SupportRequest
from schemas import SupportRequestCreate
from config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/support", tags=["support"])


@router.post("")
async def submit_support_request(
    data: SupportRequestCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    record = SupportRequest(
        username=(data.username or "").strip() or None,
        email=(data.email or "").strip() or None,
        subject=data.subject.strip(),
        message=data.message.strip(),
    )
    db.add(record)
    await db.commit()

    admin_email = settings.ADMIN_EMAIL or settings.CONTACT_TO_EMAIL
    if admin_email:
        background_tasks.add_task(
            _send_support_notification,
            record.username or "Anonymous",
            record.email or "",
            record.subject,
            record.message,
            admin_email,
        )
    else:
        logger.warning("Support request saved but no ADMIN_EMAIL/CONTACT_TO_EMAIL configured")

    return {"message": "Support request submitted successfully"}


def _send_support_notification(username: str, email: str, subject: str, message: str, admin_email: str):
    try:
        from services.email_service import send_support_notification_to_admin
        send_support_notification_to_admin(username, email, subject, message, admin_email)
    except Exception as e:
        logger.error(f"Support notification email failed: {e}")
