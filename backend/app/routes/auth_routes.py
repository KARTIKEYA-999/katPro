import os
import base64
import uuid
import re
import logging
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.config import BASE_DIR
from backend.app.database import get_db
from backend.app.models import User, Farmer, Official, Administrator
from backend.app.schemas import UserLogin, UserRegister, UserOut, AuthToken
from backend.app.auth import (
    verify_password, get_password_hash, create_access_token,
    get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
)

logger = logging.getLogger("sih_procurement.auth")

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

def _save_base64_image(image_data: str, prefix: str = "avatar") -> str:
    """
    Decodes and stores a base64 encoded user profile avatar into frontend/uploads/avatars/
    Returns the static URL path, e.g. /static/uploads/avatars/farmer_user123_abc123.png
    """
    if not image_data or not isinstance(image_data, str) or not image_data.strip():
        return None

    try:
        # Match data URI scheme e.g. data:image/jpeg;base64,...
        match = re.match(r"^data:image\/(jpeg|jpg|png|webp|gif);base64,(.+)$", image_data.strip(), re.IGNORECASE)
        if match:
            ext = match.group(1).lower()
            if ext == "jpeg":
                ext = "jpg"
            raw_b64 = match.group(2)
        else:
            ext = "png"
            raw_b64 = image_data.strip()

        decoded = base64.b64decode(raw_b64)
        if len(decoded) > 5 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Profile image exceeds the maximum allowed size of 5MB."
            )

        upload_dir = BASE_DIR / "frontend" / "uploads" / "avatars"
        upload_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{prefix}_{uuid.uuid4().hex[:10]}.{ext}"
        file_path = upload_dir / filename

        with open(file_path, "wb") as f:
            f.write(decoded)

        return f"/static/uploads/avatars/{filename}"
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving base64 profile image: {e}")
        return None

@router.post("/register", response_model=AuthToken)
def register(req: UserRegister, db: Session = Depends(get_db)):
    """Registers a new user (Farmer, Official, or Admin) and generates JWT"""
    # Check if username exists
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered. Please choose another username."
        )

    # Check phone
    if db.query(User).filter(User.phone == req.phone).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mobile phone number already registered."
        )

    # Process profile avatar if provided
    avatar_url = None
    if req.profile_image:
        avatar_url = _save_base64_image(req.profile_image, prefix=f"farmer_{req.username}")

    # Create User record
    hashed_pwd = get_password_hash(req.password)
    user = User(
        username=req.username,
        password_hash=hashed_pwd,
        role=req.role.upper(),
        full_name=req.full_name,
        phone=req.phone,
        email=req.email,
        language_pref=req.language_pref or "en",
        profile_image_url=avatar_url
    )
    db.add(user)
    db.flush()

    # Create role-specific profile
    if user.role == "FARMER":
        farmer_code = f"FAR-TS-{user.id:03d}"
        farmer = Farmer(
            user_id=user.id,
            farmer_code=farmer_code,
            village=req.village or "Kudakuda",
            mandal=req.mandal or "Chivvemla",
            district=req.district or "Suryapet",
            state=req.state or "Telangana",
            land_size_acres=req.land_size_acres or 3.0,
            primary_crop=req.primary_crop or "Paddy",
            bank_account_last4=req.bank_account_last4 or "1234",
            profile_image_url=avatar_url
        )
        db.add(farmer)
    elif user.role == "OFFICIAL":
        official = Official(
            user_id=user.id,
            center_id=1, # Default to Center 1
            employee_code=f"OFF-TS-{user.id:03d}",
            designation="Procurement Officer"
        )
        db.add(official)
    elif user.role == "ADMIN":
        admin = Administrator(
            user_id=user.id,
            admin_code=f"ADM-TS-{user.id:03d}",
            department="Civil Supplies & Procurement"
        )
        db.add(admin)

    db.commit()
    db.refresh(user)

    token = create_access_token(
        data={"sub": user.username, "role": user.role, "id": user.id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return AuthToken(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user)
    )

@router.post("/login", response_model=AuthToken)
def login(req: UserLogin, db: Session = Depends(get_db)):
    """Authenticates user and issues secure JWT token"""
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Role Synchronization Verification
    if req.role and req.role.strip():
        req_role = req.role.strip().upper()
        if user.role != req_role:
            role_map = {
                "FARMER": "Farmer",
                "OFFICIAL": "Center Official",
                "ADMIN": "Administrator"
            }
            selected_name = role_map.get(req_role, req_role)
            actual_name = role_map.get(user.role, user.role)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role mismatch: You selected '{selected_name}', but '{user.username}' is a {actual_name} account. Please change 'Select Your Role' to '{actual_name}'."
            )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact your center administrator."
        )

    token = create_access_token(
        data={"sub": user.username, "role": user.role, "id": user.id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return AuthToken(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user)
    )

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Returns profile information of authenticated user"""
    return UserOut.model_validate(current_user)

@router.post("/demo-login/{role}", response_model=AuthToken)
def demo_login(role: str, db: Session = Depends(get_db)):
    """
    SIH Presentation Quick Login helper:
    Instantly logs in with demo accounts: farmer1, official1, or admin1
    """
    role = role.lower()
    username_map = {
        "farmer": "farmer1",
        "official": "official1",
        "admin": "admin1"
    }
    username = username_map.get(role)
    if not username:
        raise HTTPException(status_code=400, detail="Invalid demo role. Choose farmer, official, or admin.")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"Demo user {username} not found in database.")

    token = create_access_token(
        data={"sub": user.username, "role": user.role, "id": user.id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return AuthToken(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user)
    )

@router.post("/logout")
def logout():
    """Client token disposal endpoint"""
    return {"message": "Successfully logged out"}
