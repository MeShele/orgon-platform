"""KYC verification middleware — @require_kyc_verified decorator."""
from fastapi import Depends, HTTPException, status
from backend.dependencies import get_current_user, get_db_pool
from uuid import UUID


def require_kyc_verified(*bypass_roles: str):
    """
    FastAPI dependency that requires KYC verification.
    Super_admin and platform_admin bypass KYC checks by default.
    Additional bypass roles can be specified.
    
    Usage:
        @router.post("/transactions")
        async def create_tx(user = Depends(require_kyc_verified())):
            ...
    """
    default_bypass = {"super_admin", "platform_admin"}
    all_bypass = default_bypass | set(bypass_roles)

    async def checker(
        current_user: dict = Depends(get_current_user),
        pool=Depends(get_db_pool)
    ):
        role = current_user.get("role", "")
        if role in all_bypass:
            return current_user

        user_id = current_user.get("id")
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT kyc_verified FROM users WHERE id = $1", user_id
            )

        if not row or not row['kyc_verified']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="KYC verification required. Please complete identity verification before proceeding.",
                headers={"X-KYC-Required": "true"}
            )

        return current_user

    return checker
