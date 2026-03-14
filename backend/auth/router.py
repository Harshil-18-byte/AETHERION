from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import List, Optional

from db.postgres import get_db, User as DBUser, SavedLayout as DBLayout
from auth.utils import verify_password, get_password_hash, create_access_token, SECRET_KEY, ALGORITHM
from jose import jwt, JWTError
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)

# Pydantic Models for Auth
class UserBase(BaseModel):
    email: EmailStr
    full_name: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: int

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

from config import DEV_MODE

# Dependency to get current user
async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
):
    # --- DEVELOPMENT BYPASS ---
    if DEV_MODE:
        user = db.query(DBUser).filter(DBUser.email == "dev@example.com").first()
        if not user:
            user = DBUser(email="dev@example.com", full_name="Mock User", hashed_password="mask_password")
            db.add(user)
            db.commit()
            db.refresh(user)
        return user
    
    if not token:
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # --------------------------

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    
    user = db.query(DBUser).filter(DBUser.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    return user

@router.post("/register", response_model=User)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(DBUser).filter(DBUser.email == user.email).first()
    if db_user:
        return db_user # Return existing user as per "any login is okay"
    
    hashed_password = get_password_hash(user.password)
    new_user = DBUser(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Making any login work as per user request
    user = db.query(DBUser).filter(DBUser.email == form_data.username).first()
    if not user:
        # Auto-register if user doesn't exist
        user = DBUser(
            email=form_data.username,
            hashed_password=get_password_hash(form_data.password),
            full_name="Auto User"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=User)
def read_users_me(current_user: DBUser = Depends(get_current_user)):
    return current_user
