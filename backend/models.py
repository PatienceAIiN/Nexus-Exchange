from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, Text, Enum as SAEnum
from datetime import datetime
import enum
from database import Base

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"

class SignupStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=True, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.USER)
    signup_status = Column(SAEnum(SignupStatus), default=SignupStatus.PENDING)
    avatar_seed = Column(String(100), default="default")
    token_version = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class FBILRate(Base):
    __tablename__ = "fbil_rates"
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    time = Column(String(20))
    currency_pair = Column(String(50), nullable=False, index=True)
    rate = Column(Float, nullable=False)
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ProcessedFile(Base):
    __tablename__ = "processed_files"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    original_filename = Column(String(500), nullable=False)
    processed_filename = Column(String(500), nullable=False)
    r2_original_key = Column(String(500))
    r2_processed_key = Column(String(500))
    total_rows = Column(Integer, default=0)
    matched_rows = Column(Integer, default=0)
    unmatched_rows = Column(Integer, default=0)
    status = Column(String(50), default="processing")
    processing_log = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
