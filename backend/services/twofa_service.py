"""
Two-Factor Authentication Service
Supports TOTP (Google Authenticator) and backup codes
"""

import pyotp
import qrcode
import secrets
import hashlib
from io import BytesIO
from datetime import datetime
from typing import List, Tuple, Optional
import base64


class TwoFAService:
    """Service for managing two-factor authentication"""
    
    def __init__(self, db):
        self.db = db
    
    async def generate_totp_secret(self, user_id: int) -> Tuple[str, str]:
        """
        Generate a new TOTP secret for a user
        
        Returns:
            Tuple of (secret, provisioning_uri)
        """
        # Get user email
        user = await self.db.fetchrow(
            "SELECT email, full_name FROM users WHERE id = $1",
            user_id
        )
        
        if not user:
            raise ValueError("User not found")
        
        # Generate random secret
        secret = pyotp.random_base32()
        
        # Create TOTP object
        totp = pyotp.TOTP(secret)
        
        # Generate provisioning URI for QR code
        provisioning_uri = totp.provisioning_uri(
            name=user['email'],
            issuer_name="ORGON"
        )
        
        return secret, provisioning_uri
    
    def generate_qr_code(self, provisioning_uri: str) -> str:
        """
        Generate QR code as base64 data URL
        
        Args:
            provisioning_uri: The otpauth:// URI from TOTP
            
        Returns:
            Base64 data URL of QR code image
        """
        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        # Generate image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_base64}"
    
    async def generate_backup_codes(self, user_id: int, count: int = 10) -> List[str]:
        """
        Generate backup codes for user
        
        Args:
            user_id: User ID
            count: Number of codes to generate (default 10)
            
        Returns:
            List of backup codes
        """
        codes = []
        
        for _ in range(count):
            # Generate 8-character alphanumeric code
            code = secrets.token_hex(4).upper()
            codes.append(code)
            
            # Hash and store in database
            code_hash = hashlib.sha256(code.encode()).hexdigest()
            
            await self.db.execute(
                """
                INSERT INTO twofa_backup_codes (user_id, code_hash, created_at)
                VALUES ($1, $2, $3)
                """,
                user_id, code_hash, datetime.utcnow()
            )
        
        return codes
    
    async def enable_totp(self, user_id: int, secret: str, verification_code: str) -> bool:
        """
        Enable TOTP for user after verifying the code
        
        Args:
            user_id: User ID
            secret: TOTP secret
            verification_code: 6-digit code from authenticator app
            
        Returns:
            True if enabled successfully
        """
        # Verify the code
        totp = pyotp.TOTP(secret)
        if not totp.verify(verification_code, valid_window=1):
            return False
        
        # Store secret in database
        await self.db.execute(
            """
            UPDATE users 
            SET totp_secret = $1, 
                totp_enabled = true,
                updated_at = $2
            WHERE id = $3
            """,
            secret, datetime.utcnow(), user_id
        )
        
        return True
    
    async def disable_totp(self, user_id: int) -> None:
        """Disable TOTP for user"""
        await self.db.execute(
            """
            UPDATE users 
            SET totp_secret = NULL, 
                totp_enabled = false,
                updated_at = $1
            WHERE id = $2
            """,
            datetime.utcnow(), user_id
        )
        
        # Delete all backup codes
        await self.db.execute(
            "DELETE FROM twofa_backup_codes WHERE user_id = $1",
            user_id
        )
    
    async def verify_totp(self, user_id: int, code: str) -> bool:
        """
        Verify TOTP code
        
        Args:
            user_id: User ID
            code: 6-digit code from authenticator app
            
        Returns:
            True if code is valid
        """
        # Get user's TOTP secret
        user = await self.db.fetchrow(
            "SELECT totp_secret, totp_enabled FROM users WHERE id = $1",
            user_id
        )
        
        if not user or not user['totp_enabled'] or not user['totp_secret']:
            return False
        
        # Verify code
        totp = pyotp.TOTP(user['totp_secret'])
        return totp.verify(code, valid_window=1)
    
    async def verify_backup_code(self, user_id: int, code: str) -> bool:
        """
        Verify and consume backup code
        
        Args:
            user_id: User ID
            code: Backup code
            
        Returns:
            True if code is valid
        """
        # Hash the code
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        
        # Check if code exists and not used
        backup_code = await self.db.fetchrow(
            """
            SELECT id FROM twofa_backup_codes
            WHERE user_id = $1 AND code_hash = $2 AND used_at IS NULL
            """,
            user_id, code_hash
        )
        
        if not backup_code:
            return False
        
        # Mark code as used
        await self.db.execute(
            """
            UPDATE twofa_backup_codes
            SET used_at = $1
            WHERE id = $2
            """,
            datetime.utcnow(), backup_code['id']
        )
        
        return True
    
    async def check_2fa_required(self, user_id: int) -> bool:
        """Check if user has 2FA enabled"""
        user = await self.db.fetchrow(
            "SELECT totp_enabled FROM users WHERE id = $1",
            user_id
        )
        return bool(user and user['totp_enabled'])
    
    async def get_backup_codes_count(self, user_id: int) -> Tuple[int, int]:
        """
        Get count of backup codes (total, remaining)
        
        Returns:
            Tuple of (total_count, remaining_count)
        """
        result = await self.db.fetchrow(
            """
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE used_at IS NULL) as remaining
            FROM twofa_backup_codes
            WHERE user_id = $1
            """,
            user_id
        )
        
        return result['total'], result['remaining']
