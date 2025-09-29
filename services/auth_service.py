"""
Authentication Service for Multi-User Support
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from functools import wraps
from flask import request, jsonify, g
from jose import JWTError, jwt
import os

from services.database_service import db_service

logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"

def get_current_user():
    """Get current authenticated user"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None
    
    try:
        # Extract token from "Bearer <token>"
        token = auth_header.split(' ')[1]
        user = db_service.verify_token(token)
        return user
    except (IndexError, AttributeError):
        return None

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Add user to request context
        g.current_user = user
        return f(*args, **kwargs)
    
    return decorated_function

def require_admin(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        if not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        g.current_user = user
        return f(*args, **kwargs)
    
    return decorated_function

class AuthService:
    """Authentication service for multi-user support"""
    
    def __init__(self):
        self.db_service = db_service
    
    def register_user(self, username: str, email: str, password: str) -> dict:
        """Register new user"""
        try:
            from models.user import UserCreate
            
            user_data = UserCreate(
                username=username,
                email=email,
                password=password
            )
            
            user = self.db_service.create_user(user_data)
            
            if user:
                return {
                    'success': True,
                    'message': 'User registered successfully',
                    'user': user
                }
            else:
                return {
                    'success': False,
                    'error': 'Username or email already exists'
                }
                
        except Exception as e:
            logger.error(f"Error registering user: {e}")
            return {
                'success': False,
                'error': f'Registration failed: {str(e)}'
            }
    
    def login_user(self, username: str, password: str) -> dict:
        """Login user"""
        try:
            user = self.db_service.authenticate_user(username, password)
            
            if not user:
                return {
                    'success': False,
                    'error': 'Invalid credentials'
                }
            
            # Create session
            token = self.db_service.create_session(user.id)
            
            if not token:
                return {
                    'success': False,
                    'error': 'Failed to create session'
                }
            
            from models.user import UserResponse, TokenResponse
            
            return {
                'success': True,
                'message': 'Login successful',
                'access_token': token,
                'token_type': 'bearer',
                'expires_in': 1800,  # 30 minutes
                'user': UserResponse.from_orm(user)
            }
            
        except Exception as e:
            logger.error(f"Error logging in user: {e}")
            return {
                'success': False,
                'error': f'Login failed: {str(e)}'
            }
    
    def logout_user(self, token: str) -> dict:
        """Logout user"""
        try:
            success = self.db_service.logout_user(token)
            
            if success:
                return {
                    'success': True,
                    'message': 'Logout successful'
                }
            else:
                return {
                    'success': False,
                    'error': 'Invalid session'
                }
                
        except Exception as e:
            logger.error(f"Error logging out user: {e}")
            return {
                'success': False,
                'error': f'Logout failed: {str(e)}'
            }
    
    def get_user_profile(self, user_id: int) -> dict:
        """Get user profile"""
        try:
            user = self.db_service.get_user_by_id(user_id)
            
            if not user:
                return {
                    'success': False,
                    'error': 'User not found'
                }
            
            from models.user import UserResponse
            
            return {
                'success': True,
                'user': UserResponse.from_orm(user)
            }
            
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return {
                'success': False,
                'error': f'Failed to get profile: {str(e)}'
            }

# Global auth service instance
auth_service = AuthService()
