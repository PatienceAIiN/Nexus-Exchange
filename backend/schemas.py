from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date, datetime
from models import UserRole, SignupStatus

class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class ChangePassword(BaseModel):
    old_password: str
    new_password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
    user_id: int

class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: UserRole
    signup_status: SignupStatus
    avatar_seed: Optional[str] = "default"
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True

class FBILRateResponse(BaseModel):
    id: int
    date: date
    time: Optional[str]
    currency_pair: str
    rate: float
    comments: Optional[str]

    class Config:
        from_attributes = True

class ProcessedFileResponse(BaseModel):
    id: int
    original_filename: str
    processed_filename: str
    total_rows: int
    matched_rows: int
    unmatched_rows: int
    status: str
    processing_log: Optional[str]
    created_at: datetime
    r2_original_key: Optional[str]
    r2_processed_key: Optional[str]

    class Config:
        from_attributes = True

class AvatarUpdate(BaseModel):
    avatar_seed: str


class ProfileUpdate(BaseModel):
    username: str
    email: Optional[str] = None
    avatar_seed: Optional[str] = None


class DPDPConsentCreate(BaseModel):
    visitor_id: Optional[str] = None
    consent_given: bool
    policy_version: Optional[str] = "1.0"
    purposes: Optional[List[str]] = None


class DPDPConsentResponse(BaseModel):
    id: int
    consent_given: bool
    policy_version: str
    created_at: datetime

    class Config:
        from_attributes = True


class SupportRequestCreate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    subject: str
    message: str
