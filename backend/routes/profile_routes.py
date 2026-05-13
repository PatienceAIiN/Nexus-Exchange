from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import User
from auth import get_current_user
from schemas import AvatarUpdate, ProfileUpdate

router = APIRouter(prefix="/api/profile", tags=["profile"])

@router.get("")
async def get_profile(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "avatar_seed": current_user.avatar_seed or current_user.username,
        "created_at": str(current_user.created_at),
    }


@router.put("")
async def update_profile(
    data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    username = data.username.strip()
    email = data.email.strip() if data.email else None
    avatar_seed = data.avatar_seed.strip() if data.avatar_seed else username

    if not username:
        raise HTTPException(status_code=400, detail="Username is required")

    existing = await db.execute(select(User).where(User.username == username, User.id != current_user.id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")

    if email:
        email_existing = await db.execute(select(User).where(User.email == email, User.id != current_user.id))
        if email_existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already exists")

    current_user.username = username
    current_user.email = email
    current_user.avatar_seed = avatar_seed
    await db.commit()
    await db.refresh(current_user)

    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "avatar_seed": current_user.avatar_seed or current_user.username,
        "created_at": str(current_user.created_at),
    }


@router.put("/avatar")
async def update_avatar(
    data: AvatarUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.avatar_seed = data.avatar_seed
    await db.commit()
    return {"message": "Avatar updated", "avatar_seed": data.avatar_seed}
