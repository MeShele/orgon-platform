"""
Two-Factor Authentication API Routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List
from datetime import datetime

from ..dependencies import get_db_pool
from ..services.twofa_service import TwoFAService
from .routes_auth import get_current_user

router = APIRouter(prefix="/api/2fa", tags=["2fa"])


# Request/Response Models
class EnableTOTPRequest(BaseModel):
    verification_code: str


class VerifyCodeRequest(BaseModel):
    code: str


class TOTPSetupResponse(BaseModel):
    secret: str
    qr_code: str  # Base64 data URL
    backup_codes: List[str]


class TOTPStatusResponse(BaseModel):
    enabled: bool
    backup_codes_total: int
    backup_codes_remaining: int


# Endpoints

@router.get("/status", response_model=TOTPStatusResponse)
async def get_2fa_status(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db_pool)
):
    """Get current 2FA status for user"""
    service = TwoFAService(db)
    
    # Check if 2FA is enabled
    enabled = await service.check_2fa_required(current_user['id'])
    
    # Get backup codes count
    total, remaining = await service.get_backup_codes_count(current_user['id'])
    
    return {
        "enabled": enabled,
        "backup_codes_total": total,
        "backup_codes_remaining": remaining
    }


@router.post("/totp/setup", response_model=TOTPSetupResponse)
async def setup_totp(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db_pool)
):
    """
    Initialize TOTP setup
    
    Returns secret, QR code, and backup codes
    User must verify with authenticator app before it's enabled
    """
    service = TwoFAService(db)
    
    # Generate TOTP secret
    secret, provisioning_uri = await service.generate_totp_secret(current_user['id'])
    
    # Generate QR code
    qr_code = service.generate_qr_code(provisioning_uri)
    
    # Generate backup codes
    backup_codes = await service.generate_backup_codes(current_user['id'])
    
    return {
        "secret": secret,
        "qr_code": qr_code,
        "backup_codes": backup_codes
    }


@router.post("/totp/enable")
async def enable_totp(
    request: EnableTOTPRequest,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db_pool)
):
    """
    Enable TOTP after verification
    
    User must provide valid code from authenticator app
    """
    service = TwoFAService(db)
    
    # Get the secret from user (should be stored temporarily in session/state)
    # For now, we'll need to pass it from frontend
    # In production, store in Redis or session
    
    # Note: This is simplified. In production, you'd:
    # 1. Store secret in Redis/session during setup
    # 2. Retrieve it here using user_id
    # 3. Verify and enable
    
    # For now, we'll just verify using database secret if exists
    user = await db.fetchrow(
        "SELECT totp_secret FROM users WHERE id = $1",
        current_user['id']
    )
    
    if not user or not user['totp_secret']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No TOTP setup found. Please run /totp/setup first."
        )
    
    success = await service.enable_totp(
        current_user['id'],
        user['totp_secret'],
        request.verification_code
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    return {"message": "2FA enabled successfully"}


@router.post("/totp/disable")
async def disable_totp(
    request: VerifyCodeRequest,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db_pool)
):
    """
    Disable TOTP
    
    Requires valid TOTP code for confirmation
    """
    service = TwoFAService(db)
    
    # Verify current code before disabling
    valid = await service.verify_totp(current_user['id'], request.code)
    
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    await service.disable_totp(current_user['id'])
    
    return {"message": "2FA disabled successfully"}


@router.post("/verify")
async def verify_2fa_code(
    request: VerifyCodeRequest,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db_pool)
):
    """
    Verify TOTP code or backup code
    
    Used during login flow
    """
    service = TwoFAService(db)
    
    # Try TOTP first
    valid = await service.verify_totp(current_user['id'], request.code)
    
    if valid:
        return {"valid": True, "type": "totp"}
    
    # Try backup code
    valid = await service.verify_backup_code(current_user['id'], request.code)
    
    if valid:
        return {"valid": True, "type": "backup"}
    
    return {"valid": False}


@router.post("/backup-codes/regenerate", response_model=dict)
async def regenerate_backup_codes(
    request: VerifyCodeRequest,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db_pool)
):
    """
    Regenerate backup codes
    
    Requires valid TOTP code for confirmation
    Deletes all old codes and generates new ones
    """
    service = TwoFAService(db)
    
    # Verify current TOTP code
    valid = await service.verify_totp(current_user['id'], request.code)
    
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    # Delete old backup codes
    await db.execute(
        "DELETE FROM twofa_backup_codes WHERE user_id = $1",
        current_user['id']
    )
    
    # Generate new codes
    backup_codes = await service.generate_backup_codes(current_user['id'])
    
    return {
        "backup_codes": backup_codes,
        "message": "Backup codes regenerated successfully"
    }
