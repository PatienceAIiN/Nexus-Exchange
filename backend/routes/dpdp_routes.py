import json
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from database import get_db
from models import DPDPConsent
from schemas import DPDPConsentCreate, DPDPConsentResponse

router = APIRouter(prefix="/api/dpdp", tags=["dpdp"])

POLICY_VERSION = "1.0"

POLICY = {
    "version": POLICY_VERSION,
    "title": "Notice under the Digital Personal Data Protection Act, 2023",
    "data_fiduciary": "Nexus Exchange (operated by PatienceAI)",
    "contact": "dpo@patienceai.in",
    "purposes": [
        "Authentication and account management",
        "Processing reference rate data you upload",
        "Service operations, security, audit logging",
        "Support communications you initiate",
    ],
    "categories": [
        "Account identifiers (username, email)",
        "Uploaded files and derived processed data",
        "Technical metadata (IP, user agent, timestamps)",
    ],
    "retention": "Personal data is retained for the lifetime of the account and up to 12 months thereafter, unless required by law.",
    "rights": [
        "Right to access and correction",
        "Right to erasure",
        "Right to grievance redressal",
        "Right to nominate",
        "Right to withdraw consent at any time",
    ],
    "grievance_officer": "Grievance Officer, Nexus Exchange — dpo@patienceai.in",
}


@router.get("/policy")
async def get_policy():
    return POLICY


@router.post("/consent", response_model=DPDPConsentResponse)
async def record_consent(
    data: DPDPConsentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")[:500]

    user_id = None
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        try:
            from jose import jwt
            from config import settings as _settings
            from models import User
            token = auth_header.split(" ", 1)[1]
            payload = jwt.decode(token, _settings.JWT_SECRET_KEY, algorithms=[_settings.JWT_ALGORITHM])
            uid = payload.get("sub")
            if uid is not None:
                result = await db.execute(select(User).where(User.id == int(uid)))
                u = result.scalar_one_or_none()
                if u:
                    user_id = u.id
        except Exception:
            user_id = None

    record = DPDPConsent(
        user_id=user_id,
        visitor_id=(data.visitor_id or "")[:100] or None,
        ip_address=client_ip,
        user_agent=user_agent,
        consent_given=bool(data.consent_given),
        policy_version=data.policy_version or POLICY_VERSION,
        purposes=json.dumps(data.purposes) if data.purposes else None,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.get("/consent/status")
async def consent_status(
    visitor_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    if not visitor_id:
        return {"consent_given": False, "policy_version": POLICY_VERSION}
    result = await db.execute(
        select(DPDPConsent)
        .where(DPDPConsent.visitor_id == visitor_id)
        .order_by(desc(DPDPConsent.created_at))
        .limit(1)
    )
    record = result.scalar_one_or_none()
    if not record:
        return {"consent_given": False, "policy_version": POLICY_VERSION}
    return {
        "consent_given": record.consent_given,
        "policy_version": record.policy_version,
        "created_at": record.created_at,
        "current_version": POLICY_VERSION,
        "needs_renewal": record.policy_version != POLICY_VERSION,
    }
