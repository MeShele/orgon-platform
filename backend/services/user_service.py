"""User service for authentication and authorization."""

import logging
import os
import secrets
from typing import Optional, Dict
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from backend.database.db_postgres import AsyncDatabase

logger = logging.getLogger("orgon.services.user")

# JWT Configuration (should be in config/env)
JWT_SECRET = os.getenv("JWT_SECRET_KEY", "CHANGE_ME_IN_PRODUCTION")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


class UserService:
    """
    User management and authentication service.
    
    Features:
    - User registration
    - Password hashing (bcrypt)
    - JWT authentication (access + refresh tokens)
    - Role-based access control (RBAC)
    - Password reset
    - Session management
    """

    def __init__(self, db: AsyncDatabase):
        self._db = db

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

    def create_access_token(self, user_id: int, email: str, role: str) -> str:
        """Create a JWT access token."""
        expires = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "user_id": user_id,
            "email": email,
            "role": role,
            "exp": expires,
            "type": "access"
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    def create_refresh_token(self, user_id: int) -> str:
        """Create a JWT refresh token."""
        expires = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        payload = {
            "user_id": user_id,
            "exp": expires,
            "type": "refresh"
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None

    async def register_user(
        self,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        role: str = "viewer"
    ) -> Dict:
        """
        Register a new user.
        
        Args:
            email: User email (unique)
            password: Plain text password (will be hashed)
            full_name: Full name (optional)
            role: User role (admin/signer/viewer, default: viewer)
            
        Returns:
            User dictionary
        """
        # Check if user exists
        existing = await self._db.fetchrow(
            "SELECT id FROM users WHERE email = $1",
            params=(email,)
        )
        
        if existing:
            raise ValueError("User with this email already exists")

        # Validate role
        if role not in ('admin', 'signer', 'viewer'):
            raise ValueError(f"Invalid role: {role}")

        # Hash password
        password_hash = self.hash_password(password)

        # Insert user
        now = datetime.now(timezone.utc)
        
        query = """
            INSERT INTO users (email, password_hash, full_name, role, is_active, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id, email, full_name, role, is_active, created_at
        """
        
        row = await self._db.fetchrow(
            query,
            params=(email, password_hash, full_name, role, True, now, now)
        )

        logger.info(f"User registered: {email} (role: {role})")
        
        return {
            "id": row["id"],
            "email": row["email"],
            "full_name": row["full_name"],
            "role": row["role"],
            "is_active": row["is_active"],
            "created_at": row["created_at"].isoformat()
        }

    async def authenticate(self, email: str, password: str) -> Optional[Dict]:
        """
        Authenticate a user.
        
        Args:
            email: User email
            password: Plain text password
            
        Returns:
            User dictionary if authenticated, None otherwise
        """
        query = """
            SELECT id, email, password_hash, full_name, role, is_active
            FROM users
            WHERE email = $1
        """
        
        row = await self._db.fetchrow(query, params=(email,))
        
        if not row:
            logger.warning(f"Authentication failed: user not found ({email})")
            return None

        if not row["is_active"]:
            logger.warning(f"Authentication failed: user inactive ({email})")
            return None

        # Verify password
        if not self.verify_password(password, row["password_hash"]):
            logger.warning(f"Authentication failed: wrong password ({email})")
            return None

        # Update last login
        await self._db.execute(
            "UPDATE users SET last_login_at = $1 WHERE id = $2",
            params=(datetime.now(timezone.utc), row["id"])
        )

        logger.info(f"User authenticated: {email}")

        return {
            "id": row["id"],
            "email": row["email"],
            "full_name": row["full_name"],
            "role": row["role"],
            "is_active": row["is_active"]
        }

    async def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID."""
        query = """
            SELECT id, email, full_name, role, is_active, email_verified, created_at, last_login_at
            FROM users
            WHERE id = $1
        """
        
        row = await self._db.fetchrow(query, params=(user_id,))
        
        if not row:
            return None

        return {
            "id": row["id"],
            "email": row["email"],
            "full_name": row["full_name"],
            "role": row["role"],
            "is_active": row["is_active"],
            "email_verified": row["email_verified"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "last_login_at": row["last_login_at"].isoformat() if row["last_login_at"] else None
        }

    async def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email."""
        query = """
            SELECT id, email, full_name, role, is_active, email_verified, created_at
            FROM users
            WHERE email = $1
        """
        
        row = await self._db.fetchrow(query, params=(email,))
        
        if not row:
            return None

        return {
            "id": row["id"],
            "email": row["email"],
            "full_name": row["full_name"],
            "role": row["role"],
            "is_active": row["is_active"],
            "email_verified": row["email_verified"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None
        }

    async def save_refresh_token(
        self,
        user_id: int,
        refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> int:
        """Save a refresh token to the database."""
        expires = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        query = """
            INSERT INTO user_sessions (user_id, refresh_token, ip_address, user_agent, expires_at, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
        """
        
        row = await self._db.fetchrow(
            query,
            params=(user_id, refresh_token, ip_address, user_agent, expires, datetime.now(timezone.utc))
        )
        
        return row["id"] if row else 0

    async def verify_refresh_token(self, refresh_token: str) -> Optional[int]:
        """Verify a refresh token and return user_id."""
        query = """
            SELECT user_id FROM user_sessions
            WHERE refresh_token = $1 AND expires_at > $2
        """
        
        row = await self._db.fetchrow(
            query,
            params=(refresh_token, datetime.now(timezone.utc))
        )
        
        return row["user_id"] if row else None

    async def create_password_reset_token(self, email: str) -> Optional[str]:
        """Create a password reset token."""
        user = await self.get_user_by_email(email)
        if not user:
            return None

        # Generate secure token
        token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(hours=1)

        query = """
            INSERT INTO password_reset_tokens (user_id, token, expires_at, created_at)
            VALUES ($1, $2, $3, $4)
        """
        
        await self._db.execute(
            query,
            params=(user["id"], token, expires, datetime.now(timezone.utc))
        )

        logger.info(f"Password reset token created for {email}")
        return token

    async def reset_password(self, token: str, new_password: str) -> bool:
        """Reset password using a reset token."""
        query = """
            SELECT user_id FROM password_reset_tokens
            WHERE token = $1 AND expires_at > $2 AND used = FALSE
        """
        
        row = await self._db.fetchrow(
            query,
            params=(token, datetime.now(timezone.utc))
        )
        
        if not row:
            logger.warning("Password reset failed: invalid or expired token")
            return False

        user_id = row["user_id"]
        password_hash = self.hash_password(new_password)

        # Update password
        await self._db.execute(
            "UPDATE users SET password_hash = $1, updated_at = $2 WHERE id = $3",
            params=(password_hash, datetime.now(timezone.utc), user_id)
        )

        # Mark token as used
        await self._db.execute(
            "UPDATE password_reset_tokens SET used = TRUE WHERE token = $1",
            params=(token,)
        )

        logger.info(f"Password reset successful for user {user_id}")
        return True

    async def list_users(self, limit: int = 50, offset: int = 0) -> list[Dict]:
        """List all users."""
        query = """
            SELECT id, email, full_name, role, is_active, email_verified, created_at, last_login_at
            FROM users
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
        """
        
        rows = await self._db.fetch(query, params=(limit, offset))
        
        return [
            {
                "id": row["id"],
                "email": row["email"],
                "full_name": row["full_name"],
                "role": row["role"],
                "is_active": row["is_active"],
                "email_verified": row["email_verified"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "last_login_at": row["last_login_at"].isoformat() if row["last_login_at"] else None
            }
            for row in rows
        ]

    async def update_user(
        self,
        user_id: int,
        full_name: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Optional[Dict]:
        """Update user details."""
        updates = []
        params = []
        param_count = 0

        if full_name is not None:
            param_count += 1
            updates.append(f"full_name = ${param_count}")
            params.append(full_name)

        if role is not None:
            if role not in ('admin', 'signer', 'viewer'):
                raise ValueError(f"Invalid role: {role}")
            param_count += 1
            updates.append(f"role = ${param_count}")
            params.append(role)

        if is_active is not None:
            param_count += 1
            updates.append(f"is_active = ${param_count}")
            params.append(is_active)

        if not updates:
            return await self.get_user_by_id(user_id)

        param_count += 1
        params.append(user_id)

        query = f"UPDATE users SET {', '.join(updates)} WHERE id = ${param_count} RETURNING id"
        
        await self._db.execute(query, params=tuple(params))
        
        return await self.get_user_by_id(user_id)
