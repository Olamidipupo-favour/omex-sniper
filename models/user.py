"""
User and Authentication Models
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import hashlib
import secrets

Base = declarative_base()

class User(Base):
    """User model for multi-wallet support"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Relationships
    wallets = relationship("UserWallet", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

class UserWallet(Base):
    """User wallet model"""
    __tablename__ = "user_wallets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    wallet_name = Column(String(100), nullable=False)  # User-friendly name
    wallet_address = Column(String(44), unique=True, index=True, nullable=False)
    encrypted_private_key = Column(Text, nullable=False)  # Encrypted private key
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="wallets")
    positions = relationship("UserPosition", back_populates="wallet", cascade="all, delete-orphan")

class UserSession(Base):
    """User session model for JWT tokens"""
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(255), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="sessions")

class UserPosition(Base):
    """User position model for tracking trades"""
    __tablename__ = "user_positions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    wallet_id = Column(Integer, ForeignKey("user_wallets.id"), nullable=False)
    token_address = Column(String(44), nullable=False)
    token_symbol = Column(String(20))
    token_name = Column(String(100))
    buy_price = Column(Float)
    buy_amount = Column(Float)
    current_price = Column(Float)
    current_value = Column(Float)
    pnl = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    wallet = relationship("UserWallet", back_populates="positions")

# Pydantic schemas for API
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True

class WalletCreate(BaseModel):
    wallet_name: str
    private_key: str

class WalletResponse(BaseModel):
    id: int
    wallet_name: str
    wallet_address: str
    is_active: bool
    created_at: datetime
    last_used: Optional[datetime]
    
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: UserResponse

class PositionResponse(BaseModel):
    id: int
    token_address: str
    token_symbol: Optional[str]
    token_name: Optional[str]
    buy_price: Optional[float]
    buy_amount: Optional[float]
    current_price: Optional[float]
    current_value: Optional[float]
    pnl: float
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
