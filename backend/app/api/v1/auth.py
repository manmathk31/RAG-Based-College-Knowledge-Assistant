import re
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.core.security import verify_password, create_access_token, create_refresh_token, decode_token
from app.db.session import get_db
from app.db.auth_models import StudentModel

router = APIRouter()
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
class StudentOut(BaseModel):
    id: str
    email: str
    full_name: str

def student_out(s):
    return {"id":s.id,"email":s.email,"full_name":s.full_name}

@router.post("/login")
async def login(payload: LoginRequest, response: Response, request: Request, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    email = str(payload.email).strip().lower()
    result = await db.execute(select(StudentModel).where(StudentModel.email == email))
    student = result.scalar_one_or_none()
    # Same response for unknown users and wrong passwords prevents account enumeration.
    if not student or not student.is_active or not verify_password(payload.password, student.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    refresh = create_refresh_token(student.id)
    response.set_cookie(
        key="refresh_token", value=refresh, httponly=True, secure=settings.AUTH_COOKIE_SECURE,
        samesite="lax", max_age=settings.AUTH_REFRESH_TOKEN_DAYS*86400,
        path="/api/v1/auth"
    )
    return {"access_token":create_access_token(student.id),"token_type":"bearer","student":student_out(student)}

@router.post("/refresh")
async def refresh(response: Response, request: Request):
    # Guest visitors have no refresh cookie. Reject before opening a database session
    # so public chatbot access does not depend on Supabase being configured.
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No student session is active.")
    try:
        payload = decode_token(token, "refresh")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    async for db in get_db():
        result = await db.execute(select(StudentModel).where(StudentModel.id == payload["sub"]))
        student = result.scalar_one_or_none()
        if not student or not student.is_active:
            raise HTTPException(status_code=401, detail="Student account is inactive.")
        return {"access_token": create_access_token(student.id), "token_type": "bearer", "student": student_out(student)}
    raise HTTPException(status_code=503, detail="Student account service is unavailable.")

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("refresh_token", path="/api/v1/auth", httponly=True, samesite="lax")
    return {"message":"Signed out successfully."}

async def get_optional_student(request: Request):
    """Return the signed-in student when a bearer token is supplied; guests need no DB session."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    try:
        payload = decode_token(header[7:], "access")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid or expired access token.")
    async for db in get_db():
        result = await db.execute(select(StudentModel).where(StudentModel.id == payload["sub"]))
        student = result.scalar_one_or_none()
        if not student or not student.is_active:
            raise HTTPException(status_code=401, detail="Student account is inactive.")
        return student

get_current_student = get_optional_student

@router.get("/me")
async def me(student: StudentModel = Depends(get_optional_student)):
    if student is None:
        raise HTTPException(status_code=401, detail="Student sign-in is required for this endpoint.")
    return {"student": student_out(student)}
