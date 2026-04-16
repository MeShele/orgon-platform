"""
Authentication service for user management and JWT tokens.
"""

import asyncpg
import bcrypt
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import jwt
from backend.config import settings

# JWT Configuration
JWT_SECRET = settings.SECRET_KEY
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7
PASSWORD_RESET_EXPIRE_HOURS = 1

# RBAC Roles and Permissions
# 6-role hierarchy matching frontend:
# SuperAdmin > PlatformAdmin > CompanyAdmin > CompanyOperator > CompanyAuditor > EndUser
ROLES = {
    "super_admin": ["read", "write", "delete", "sign", "manage_users", "view_audit", "manage_platform", "manage_billing", "manage_organizations"],
    "platform_admin": ["read", "write", "delete", "sign", "manage_users", "view_audit", "manage_platform"],
    "company_admin": ["read", "write", "delete", "sign", "manage_users", "view_audit"],
    "company_operator": ["read", "write", "sign"],
    "company_auditor": ["read", "view_audit"],
    "end_user": ["read"],
    # Legacy aliases for backward compatibility
    "admin": ["read", "write", "delete", "sign", "manage_users", "view_audit"],
    "signer": ["read", "write", "sign"],
    "viewer": ["read"]
}

ROLE_HIERARCHY = {
    "end_user": 0, "viewer": 0,
    "company_auditor": 1,
    "company_operator": 2, "signer": 2,
    "company_admin": 3, "admin": 3,
    "platform_admin": 4,
    "super_admin": 5
}

VALID_ROLES = ["super_admin", "platform_admin", "company_admin", "company_operator", "company_auditor", "end_user"]


class AuthService:
    """Service for authentication and user management."""
    
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
    
    # ==================== Password Hashing ====================
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt with salt rounds 12."""
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify password against bcrypt hash."""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    # ==================== JWT Token Generation ====================
    
    @staticmethod
    def create_access_token(user_id: int, email: str, role: str) -> str:
        """Create JWT access token (15 min expiry)."""
        payload = {
            "sub": str(user_id),
            "email": email,
            "role": role,
            "type": "access",
            "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    @staticmethod
    def create_refresh_token(user_id: int) -> str:
        """Create JWT refresh token (7 days expiry)."""
        payload = {
            "sub": str(user_id),
            "type": "refresh",
            "exp": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    @staticmethod
    def decode_token(token: str) -> Optional[Dict[str, Any]]:
        """Decode and validate JWT token."""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    # ==================== User Management ====================
    
    async def create_user(
        self, 
        email: str, 
        password: str, 
        full_name: str,
        role: str = "viewer"
    ) -> Optional[Dict[str, Any]]:
        """
        Create new user with hashed password.
        Returns user dict or None if email exists.
        """
        async with self.pool.acquire() as conn:
            # Check if email exists
            existing = await conn.fetchrow(
                "SELECT id FROM users WHERE email = $1",
                email
            )
            if existing:
                return None
            
            # Hash password and create user
            password_hash = self.hash_password(password)
            user = await conn.fetchrow(
                """
                INSERT INTO users (email, password_hash, full_name, role, is_active)
                VALUES ($1, $2, $3, $4, TRUE)
                RETURNING id, email, full_name, role, is_active, created_at
                """,
                email, password_hash, full_name, role
            )
            
            return dict(user) if user else None
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email (with password hash)."""
        async with self.pool.acquire() as conn:
            user = await conn.fetchrow(
                """
                SELECT id, email, password_hash, full_name, role, is_active, 
                       last_login_at, created_at, updated_at
                FROM users 
                WHERE email = $1
                """,
                email
            )
            return dict(user) if user else None
    
    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID (without password hash)."""
        async with self.pool.acquire() as conn:
            user = await conn.fetchrow(
                """
                SELECT id, email, full_name, role, is_active, 
                       last_login_at, created_at, updated_at
                FROM users 
                WHERE id = $1
                """,
                user_id
            )
            return dict(user) if user else None
    
    async def update_last_login_at(self, user_id: int) -> None:
        """Update user's last_login_at timestamp."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET last_login_at = NOW() WHERE id = $1",
                user_id
            )
    
    async def update_user(
        self,
        user_id: int,
        full_name: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Optional[Dict[str, Any]]:
        """Update user details (admin only)."""
        async with self.pool.acquire() as conn:
            updates = []
            params = []
            param_count = 1
            
            if full_name is not None:
                updates.append(f"full_name = ${param_count}")
                params.append(full_name)
                param_count += 1
            
            if role is not None:
                updates.append(f"role = ${param_count}")
                params.append(role)
                param_count += 1
            
            if is_active is not None:
                updates.append(f"is_active = ${param_count}")
                params.append(is_active)
                param_count += 1
            
            if not updates:
                return await self.get_user_by_id(user_id)
            
            updates.append("updated_at = NOW()")
            params.append(user_id)
            
            query = f"""
                UPDATE users 
                SET {', '.join(updates)}
                WHERE id = ${param_count}
                RETURNING id, email, full_name, role, is_active, 
                          last_login_at, created_at, updated_at
            """
            
            user = await conn.fetchrow(query, *params)
            return dict(user) if user else None
    
    async def change_password(self, user_id: int, new_password: str) -> bool:
        """Change user password."""
        password_hash = self.hash_password(new_password)
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE users 
                SET password_hash = $1, updated_at = NOW()
                WHERE id = $2
                """,
                password_hash, user_id
            )
            return result == "UPDATE 1"
    
    async def list_users(
        self,
        limit: int = 50,
        offset: int = 0,
        role: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Tuple[list, int]:
        """List users with pagination and filters."""
        async with self.pool.acquire() as conn:
            # Build filter conditions
            conditions = []
            params = []
            param_count = 1
            
            if role:
                conditions.append(f"role = ${param_count}")
                params.append(role)
                param_count += 1
            
            if is_active is not None:
                conditions.append(f"is_active = ${param_count}")
                params.append(is_active)
                param_count += 1
            
            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            
            # Get total count
            count_query = f"SELECT COUNT(*) FROM users {where_clause}"
            total = await conn.fetchval(count_query, *params)
            
            # Get users
            params.extend([limit, offset])
            query = f"""
                SELECT id, email, full_name, role, is_active, 
                       last_login_at, created_at, updated_at
                FROM users 
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_count} OFFSET ${param_count + 1}
            """
            
            rows = await conn.fetch(query, *params)
            users = [dict(row) for row in rows]
            
            return users, total
    
    # ==================== Session Management ====================
    
    async def create_session(
        self,
        user_id: int,
        refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> int:
        """Create new user session with refresh token."""
        async with self.pool.acquire() as conn:
            session_id = await conn.fetchval(
                """
                INSERT INTO user_sessions 
                (user_id, refresh_token, ip_address, user_agent, expires_at)
                VALUES ($1, $2, $3, $4, NOW() + INTERVAL '7 days')
                RETURNING id
                """,
                user_id, refresh_token, ip_address, user_agent
            )
            return session_id
    
    async def get_session_by_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Get session by refresh token."""
        async with self.pool.acquire() as conn:
            session = await conn.fetchrow(
                """
                SELECT id, user_id, refresh_token, ip_address, user_agent,
                       expires_at, created_at
                FROM user_sessions
                WHERE refresh_token = $1 AND expires_at > NOW()
                """,
                refresh_token
            )
            return dict(session) if session else None
    
    async def revoke_session(self, session_id: int) -> bool:
        """Revoke (delete) a session."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM user_sessions WHERE id = $1",
                session_id
            )
            return result == "DELETE 1"
    
    async def revoke_user_sessions(self, user_id: int) -> int:
        """Revoke all sessions for a user (e.g., on password change)."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM user_sessions WHERE user_id = $1",
                user_id
            )
            # Parse "DELETE N" to get count
            return int(result.split()[-1]) if result.startswith("DELETE") else 0
    
    async def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions (maintenance task)."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM user_sessions WHERE expires_at <= NOW()"
            )
            return int(result.split()[-1]) if result.startswith("DELETE") else 0
    
    # ==================== Password Reset ====================
    
    async def create_password_reset_token(self, email: str) -> Optional[str]:
        """
        Create password reset token for user.
        Returns token string or None if user not found.
        """
        async with self.pool.acquire() as conn:
            # Check if user exists
            user = await conn.fetchrow(
                "SELECT id FROM users WHERE email = $1 AND is_active = TRUE",
                email
            )
            if not user:
                return None
            
            # Generate secure token
            token = secrets.token_urlsafe(32)
            
            # Store token (expires in 1 hour)
            await conn.execute(
                """
                INSERT INTO password_reset_tokens (user_id, token, expires_at)
                VALUES ($1, $2, NOW() + INTERVAL '1 hour')
                """,
                user['id'], token
            )
            
            return token
    
    async def verify_password_reset_token(self, token: str) -> Optional[int]:
        """
        Verify password reset token.
        Returns user_id if valid, None otherwise.
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                SELECT user_id FROM password_reset_tokens
                WHERE token = $1 AND expires_at > NOW() AND used_at IS NULL
                """,
                token
            )
            return result['user_id'] if result else None
    
    async def use_password_reset_token(self, token: str, new_password: str) -> bool:
        """
        Use password reset token to change password.
        Returns True if successful.
        """
        async with self.pool.acquire() as conn:
            # Verify token
            user_id = await self.verify_password_reset_token(token)
            if not user_id:
                return False
            
            # Change password
            password_hash = self.hash_password(new_password)
            await conn.execute(
                "UPDATE users SET password_hash = $1, updated_at = NOW() WHERE id = $2",
                password_hash, user_id
            )
            
            # Mark token as used
            await conn.execute(
                "UPDATE password_reset_tokens SET used_at = NOW() WHERE token = $1",
                token
            )
            
            # Revoke all sessions (force re-login)
            await self.revoke_user_sessions(user_id)
            
            return True
    
    async def cleanup_expired_reset_tokens(self) -> int:
        """Remove expired password reset tokens (maintenance task)."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM password_reset_tokens WHERE expires_at <= NOW()"
            )
            return int(result.split()[-1]) if result.startswith("DELETE") else 0
    
    # ==================== RBAC ====================
    
    @staticmethod
    def check_permission(role: str, permission: str) -> bool:
        """Check if role has permission."""
        return permission in ROLES.get(role, [])
    
    @staticmethod
    def get_role_permissions(role: str) -> list:
        """Get all permissions for a role."""
        return ROLES.get(role, [])
    
    # ==================== Authentication Flow ====================
    
    async def authenticate(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate user with email and password.
        Returns user dict (without password) if successful.
        """
        user = await self.get_user_by_email(email)
        
        if not user:
            return None
        
        if not user['is_active']:
            return None
        
        if not self.verify_password(password, user['password_hash']):
            return None
        
        # Update last login
        await self.update_last_login_at(user['id'])
        
        # Remove password hash from response
        user.pop('password_hash', None)
        
        return user
    
    async def login(
        self,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Complete login flow: authenticate + check 2FA + create tokens.
        Returns dict with user and tokens, or requires_2fa flag.
        """
        user = await self.authenticate(email, password)
        if not user:
            return None
        
        # Check if 2FA is enabled
        async with self.pool.acquire() as conn:
            totp_enabled = await conn.fetchval(
                "SELECT totp_enabled FROM users WHERE id = $1",
                user['id']
            )
        
        # If 2FA enabled, return temporary token
        if totp_enabled:
            # Create temporary token valid for 5 minutes
            temp_token = jwt.encode(
                {
                    "sub": str(user['id']),
                    "email": user['email'],
                    "type": "2fa_pending",
                    "exp": datetime.utcnow() + timedelta(minutes=5),
                    "iat": datetime.utcnow(),
                    "ip": ip_address,
                    "ua": user_agent
                },
                JWT_SECRET,
                algorithm="HS256"
            )
            
            return {
                "requires_2fa": True,
                "temp_token": temp_token,
                "user_id": user['id']
            }
        
        # No 2FA - complete login normally
        access_token = self.create_access_token(user['id'], user['email'], user['role'])
        refresh_token = self.create_refresh_token(user['id'])
        
        # Create session
        session_id = await self.create_session(
            user['id'], 
            refresh_token, 
            ip_address, 
            user_agent
        )
        
        return {
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60  # seconds
        }
    
    async def verify_2fa_login(
        self,
        temp_token: str,
        code: str
    ) -> Optional[Dict[str, Any]]:
        """
        Complete login after 2FA verification.
        Verifies temp token + 2FA code, then creates full session.
        """
        # Decode temp token
        try:
            payload = jwt.decode(
                temp_token,
                JWT_SECRET,
                algorithms=["HS256"]
            )
        except jwt.InvalidTokenError:
            return None
        
        # Check token type
        if payload.get('type') != '2fa_pending':
            return None
        
        user_id = int(payload['sub'])
        ip_address = payload.get('ip')
        user_agent = payload.get('ua')
        
        # Verify 2FA code
        from ..services.twofa_service import TwoFAService
        twofa_service = TwoFAService(self.pool)
        
        # Try TOTP first
        valid = await twofa_service.verify_totp(user_id, code)
        
        # If TOTP failed, try backup code
        if not valid:
            valid = await twofa_service.verify_backup_code(user_id, code)
        
        if not valid:
            return None
        
        # Get user
        user = await self.get_user_by_id(user_id)
        if not user or not user['is_active']:
            return None
        
        # Update last login
        await self.update_last_login_at(user_id)
        
        # Create tokens
        access_token = self.create_access_token(user['id'], user['email'], user['role'])
        refresh_token = self.create_refresh_token(user['id'])
        
        # Create session
        session_id = await self.create_session(
            user['id'],
            refresh_token,
            ip_address,
            user_agent
        )
        
        return {
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    
    async def refresh_tokens(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Refresh access token using refresh token.
        Returns new access_token and refresh_token.
        """
        # Decode refresh token
        payload = self.decode_token(refresh_token)
        if not payload or payload.get('type') != 'refresh':
            return None
        
        user_id = int(payload['sub'])
        
        # Verify session exists
        session = await self.get_session_by_token(refresh_token)
        if not session or session['user_id'] != user_id:
            return None
        
        # Get user
        user = await self.get_user_by_id(user_id)
        if not user or not user['is_active']:
            return None
        
        # Create new tokens
        new_access_token = self.create_access_token(user['id'], user['email'], user['role'])
        new_refresh_token = self.create_refresh_token(user['id'])
        
        # Update session with new refresh token
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE user_sessions 
                SET refresh_token = $1, expires_at = NOW() + INTERVAL '7 days'
                WHERE id = $2
                """,
                new_refresh_token, session['id']
            )
        
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    
    async def logout(self, refresh_token: str) -> bool:
        """Logout by revoking session."""
        session = await self.get_session_by_token(refresh_token)
        if not session:
            return False
        
        return await self.revoke_session(session['id'])
