from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import User, UserRole, SignupStatus
from schemas import UserCreate, UserLogin, Token, ChangePassword
from auth import verify_password, get_password_hash, create_access_token, get_current_user
from config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup")
async def signup(data: UserCreate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")

    if hasattr(data, "email") and data.email:
        email_result = await db.execute(select(User).where(User.email == data.email))
        if email_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        username=data.username,
        email=getattr(data, "email", None),
        password_hash=get_password_hash(data.password),
        signup_status=SignupStatus.PENDING,
        role=UserRole.USER,
        avatar_seed=data.username,
    )
    db.add(user)
    await db.commit()

    # Notify admin about new signup
    admin_notification_email = settings.ADMIN_EMAIL or settings.CONTACT_TO_EMAIL
    if admin_notification_email:
        background_tasks.add_task(
            _send_admin_notification,
            data.username,
            admin_notification_email,
        )
    else:
        logger.warning("No ADMIN_EMAIL/CONTACT_TO_EMAIL configured; signup notification email skipped")

    return {"message": "Signup request submitted. Awaiting admin approval."}


def _send_admin_notification(username: str, admin_email: str):
    try:
        from services.email_service import send_signup_notification_to_admin
        send_signup_notification_to_admin(username, admin_email)
    except Exception as e:
        logger.error(f"Admin notification email failed: {e}")


@router.post("/login", response_model=Token)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.signup_status == SignupStatus.PENDING:
        raise HTTPException(status_code=403, detail="Your account is pending admin approval")
    if user.signup_status == SignupStatus.REJECTED:
        raise HTTPException(status_code=403, detail="Your account request was rejected")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token = create_access_token({"sub": str(user.id), "role": user.role, "tv": user.token_version})
    return Token(access_token=token, role=user.role, username=user.username, user_id=user.id)


@router.post("/change-password")
async def change_password(
    data: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not verify_password(data.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    current_user.password_hash = get_password_hash(data.new_password)
    current_user.token_version = (current_user.token_version or 0) + 1
    await db.commit()
    return {"message": "Password changed successfully. Please log in again."}
