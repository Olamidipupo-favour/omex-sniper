"""
Database Service for Multi-User Support
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext
from jose import JWTError, jwt
import secrets
import hashlib
import base64
from cryptography.fernet import Fernet
import os

from models.user import User, UserWallet, UserSession, UserPosition, UserCreate, UserLogin, UserResponse, WalletCreate, WalletResponse, TokenResponse, PositionResponse

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sniper_bot.db")
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Encryption for private keys
def get_encryption_key():
    """Get or create encryption key for private keys"""
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        key = Fernet.generate_key()
        logger.warning("ENCRYPTION_KEY not set, using generated key. Set this in production!")
    return key

encryption_key = get_encryption_key()
cipher_suite = Fernet(encryption_key)

class DatabaseService:
    """Database service for multi-user support"""
    
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.create_tables()
    
    def create_tables(self):
        """Create database tables"""
        try:
            from models.user import Base
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
    
    def get_db(self) -> Session:
        """Get database session"""
        db = self.SessionLocal()
        try:
            return db
        finally:
            pass
    
    def close_db(self, db: Session):
        """Close database session"""
        db.close()
    
    # User Management
    def create_user(self, user_data: UserCreate) -> Optional[UserResponse]:
        """Create new user"""
        db = self.get_db()
        try:
            # Check if user already exists
            existing_user = db.query(User).filter(
                (User.username == user_data.username) | (User.email == user_data.email)
            ).first()
            
            if existing_user:
                logger.warning(f"User already exists: {user_data.username}")
                return None
            
            # Hash password
            hashed_password = pwd_context.hash(user_data.password)
            
            # Create user
            user = User(
                username=user_data.username,
                email=user_data.email,
                hashed_password=hashed_password
            )
            
            db.add(user)
            db.commit()
            db.refresh(user)
            
            logger.info(f"User created: {user.username}")
            return UserResponse.from_orm(user)
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            db.rollback()
            return None
        finally:
            self.close_db(db)
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user"""
        db = self.get_db()
        try:
            user = db.query(User).filter(User.username == username).first()
            if not user:
                return None
            
            if not pwd_context.verify(password, user.hashed_password):
                return None
            
            # Update last login
            user.last_login = datetime.utcnow()
            db.commit()
            
            return user
            
        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return None
        finally:
            self.close_db(db)
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        db = self.get_db()
        try:
            return db.query(User).filter(User.id == user_id).first()
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
        finally:
            self.close_db(db)
    
    # Wallet Management
    def create_wallet(self, user_id: int, wallet_data: WalletCreate) -> Optional[WalletResponse]:
        """Create user wallet"""
        db = self.get_db()
        try:
            # Encrypt private key
            encrypted_key = cipher_suite.encrypt(wallet_data.private_key.encode())
            encrypted_key_b64 = base64.b64encode(encrypted_key).decode()
            
            # Get wallet address from private key
            import base58
            from solders.keypair import Keypair
            
            try:
                decoded_key = base58.b58decode(wallet_data.private_key)
                keypair = Keypair.from_bytes(decoded_key)
                wallet_address = str(keypair.pubkey())
            except Exception as e:
                logger.error(f"Invalid private key: {e}")
                return None
            
            # Check if wallet already exists
            existing_wallet = db.query(UserWallet).filter(
                UserWallet.wallet_address == wallet_address
            ).first()
            
            if existing_wallet:
                logger.warning(f"Wallet already exists: {wallet_address}")
                return None
            
            # Create wallet
            wallet = UserWallet(
                user_id=user_id,
                wallet_name=wallet_data.wallet_name,
                wallet_address=wallet_address,
                encrypted_private_key=encrypted_key_b64
            )
            
            db.add(wallet)
            db.commit()
            db.refresh(wallet)
            
            logger.info(f"Wallet created for user {user_id}: {wallet_address}")
            return WalletResponse.from_orm(wallet)
            
        except Exception as e:
            logger.error(f"Error creating wallet: {e}")
            db.rollback()
            return None
        finally:
            self.close_db(db)
    
    def get_user_wallets(self, user_id: int) -> List[WalletResponse]:
        """Get user wallets"""
        db = self.get_db()
        try:
            wallets = db.query(UserWallet).filter(
                UserWallet.user_id == user_id,
                UserWallet.is_active == True
            ).all()
            
            return [WalletResponse.from_orm(wallet) for wallet in wallets]
            
        except Exception as e:
            logger.error(f"Error getting user wallets: {e}")
            return []
        finally:
            self.close_db(db)
    
    def get_wallet_private_key(self, user_id: int, wallet_id: int) -> Optional[str]:
        """Get decrypted private key for wallet"""
        db = self.get_db()
        try:
            wallet = db.query(UserWallet).filter(
                UserWallet.id == wallet_id,
                UserWallet.user_id == user_id,
                UserWallet.is_active == True
            ).first()
            
            if not wallet:
                return None
            
            # Decrypt private key
            encrypted_key = base64.b64decode(wallet.encrypted_private_key.encode())
            decrypted_key = cipher_suite.decrypt(encrypted_key)
            
            return decrypted_key.decode()
            
        except Exception as e:
            logger.error(f"Error getting wallet private key: {e}")
            return None
        finally:
            self.close_db(db)
    
    # Session Management
    def create_session(self, user_id: int) -> str:
        """Create user session"""
        db = self.get_db()
        try:
            # Generate token
            token_data = {
                "user_id": user_id,
                "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            }
            token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
            
            # Hash token for storage
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            
            # Create session
            session = UserSession(
                user_id=user_id,
                token_hash=token_hash,
                expires_at=datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            )
            
            db.add(session)
            db.commit()
            
            return token
            
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return None
        finally:
            self.close_db(db)
    
    def verify_token(self, token: str) -> Optional[User]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("user_id")
            
            if not user_id:
                return None
            
            # Check if session exists and is active
            db = self.get_db()
            try:
                token_hash = hashlib.sha256(token.encode()).hexdigest()
                session = db.query(UserSession).filter(
                    UserSession.token_hash == token_hash,
                    UserSession.is_active == True,
                    UserSession.expires_at > datetime.utcnow()
                ).first()
                
                if not session:
                    return None
                
                # Update last used
                session.last_used = datetime.utcnow()
                db.commit()
                
                # Get user
                user = db.query(User).filter(User.id == user_id).first()
                return user
                
            finally:
                self.close_db(db)
                
        except JWTError:
            return None
        except Exception as e:
            logger.error(f"Error verifying token: {e}")
            return None
    
    def logout_user(self, token: str) -> bool:
        """Logout user (invalidate session)"""
        try:
            db = self.get_db()
            try:
                token_hash = hashlib.sha256(token.encode()).hexdigest()
                session = db.query(UserSession).filter(
                    UserSession.token_hash == token_hash
                ).first()
                
                if session:
                    session.is_active = False
                    db.commit()
                    return True
                
                return False
                
            finally:
                self.close_db(db)
                
        except Exception as e:
            logger.error(f"Error logging out user: {e}")
            return False

# Global database service instance
db_service = DatabaseService()
