from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import User, SignupStatus, UserRole
from schemas import UserResponse
from auth import get_current_admin, get_password_hash
from typing import List, Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])


class UserUpdateRequest(BaseModel):
    signup_status: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    email: Optional[str] = None


@router.get("/pending-signups", response_model=List[UserResponse])
async def pending_signups(db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    result = await db.execute(select(User).where(User.signup_status == SignupStatus.PENDING).order_by(User.created_at.desc()))
    return result.scalars().all()


@router.get("/users", response_model=List[UserResponse])
async def list_users(db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return result.scalars().all()


@router.post("/approve/{user_id}")
async def approve_user(
    user_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.signup_status = SignupStatus.APPROVED
    user.is_active = True
    await db.commit()

    # Send approval email if user has email
    if user.email:
        background_tasks.add_task(_send_approval_email, user.username, user.email)
    else:
        logger.info(f"No email for user {user.username}, skipping approval email")

    return {"message": f"User {user.username} approved"}


@router.post("/reject/{user_id}")
async def reject_user(
    user_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.signup_status = SignupStatus.REJECTED
    await db.commit()

    if user.email:
        background_tasks.add_task(_send_rejection_email, user.username, user.email)

    return {"message": f"User {user.username} rejected"}


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    data: UserUpdateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    old_status = user.signup_status
    old_role = user.role

    if data.signup_status is not None:
        try:
            user.signup_status = SignupStatus(data.signup_status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {data.signup_status}")

    if data.role is not None:
        try:
            user.role = UserRole(data.role)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid role: {data.role}")

    if data.is_active is not None:
        user.is_active = data.is_active

    if data.email is not None:
        user.email = data.email

    await db.commit()

    # Send email if status changed to approved
    if data.signup_status and old_status != SignupStatus.APPROVED and user.signup_status == SignupStatus.APPROVED:
        if user.email:
            background_tasks.add_task(_send_approval_email, user.username, user.email)
    elif data.signup_status and old_status != SignupStatus.REJECTED and user.signup_status == SignupStatus.REJECTED:
        if user.email:
            background_tasks.add_task(_send_rejection_email, user.username, user.email)
            
    # Send email if role changed
    if data.role and old_role != user.role:
        user.token_version += 1
        if user.email:
            background_tasks.add_task(_send_role_update_email, user.username, user.email, user.role.value)

    await db.commit()

    return {"message": f"User {user.username} updated"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    await db.delete(user)
    await db.commit()
    return {"message": f"User {user.username} deleted"}


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    from sqlalchemy import func
    from models import FBILRate, ProcessedFile

    total_users = (await db.execute(select(func.count(User.id)))).scalar()
    pending = (await db.execute(select(func.count(User.id)).where(User.signup_status == SignupStatus.PENDING))).scalar()
    total_rates = (await db.execute(select(func.count(FBILRate.id)))).scalar()
    total_files = (await db.execute(select(func.count(ProcessedFile.id)))).scalar()

    return {
        "total_users": total_users,
        "pending_signups": pending,
        "total_rates": total_rates,
        "total_processed_files": total_files,
    }


def _send_approval_email(username: str, email: str):
    try:
        from services.email_service import send_approval_email
        send_approval_email(username, email)
    except Exception as e:
        logger.error(f"Approval email failed: {e}")


def _send_rejection_email(username: str, email: str):
    try:
        from services.email_service import send_rejection_email
        send_rejection_email(username, email)
    except Exception as e:
        logger.error(f"Rejection email failed: {e}")

def _send_role_update_email(username: str, email: str, new_role: str):
    try:
        from services.email_service import send_role_update_email
        send_role_update_email(username, email, new_role)
    except Exception as e:
        logger.error(f"Role update email failed: {e}")
