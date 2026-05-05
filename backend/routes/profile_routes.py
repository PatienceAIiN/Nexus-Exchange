from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import User
from auth import get_current_user
from schemas import AvatarUpdate

router = APIRouter(prefix="/api/profile", tags=["profile"])

@router.get("")
async def get_profile(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
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
