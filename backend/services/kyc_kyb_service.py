"""KYC/KYB Submission Service — user-facing verification flows."""
import asyncpg
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
import json


class KycKybService:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    # ==================== KYC ====================

    async def submit_kyc(self, user_id: int, data: Dict) -> Dict:
        """User submits KYC documents."""
        async with self.pool.acquire() as conn:
            # Check if user already has pending/approved KYC
            existing = await conn.fetchrow("""
                SELECT id, status FROM kyc_submissions
                WHERE user_id = $1 AND status IN ('pending', 'in_review', 'approved')
                ORDER BY created_at DESC LIMIT 1
            """, user_id)
            if existing:
                if existing['status'] == 'approved':
                    return {"error": "KYC already approved", "submission_id": str(existing['id'])}
                if existing['status'] in ('pending', 'in_review'):
                    return {"error": "KYC submission already pending", "submission_id": str(existing['id'])}

            row = await conn.fetchrow("""
                INSERT INTO kyc_submissions (
                    user_id, organization_id, full_name, date_of_birth,
                    nationality, address, phone, documents, status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'pending')
                RETURNING *
            """,
                user_id,
                data.get('organization_id'),
                data['full_name'],
                data.get('date_of_birth'),
                data.get('nationality'),
                data.get('address'),
                data.get('phone'),
                json.dumps(data.get('documents', []))
            )
            return dict(row)

    async def get_kyc_status(self, user_id: int) -> Optional[Dict]:
        """Get current KYC status for user."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, status, risk_level, review_comment, submitted_at, reviewed_at
                FROM kyc_submissions
                WHERE user_id = $1
                ORDER BY created_at DESC LIMIT 1
            """, user_id)
            return dict(row) if row else None

    async def get_kyc_submissions(self, status_filter: Optional[str] = None,
                                   limit: int = 50, offset: int = 0) -> List[Dict]:
        """Admin: list KYC submissions."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT s.*, u.email as user_email
                FROM kyc_submissions s
                JOIN users u ON s.user_id = u.id
                WHERE ($1::text IS NULL OR s.status = $1)
                ORDER BY s.created_at DESC
                LIMIT $2 OFFSET $3
            """, status_filter, limit, offset)
            return [dict(r) for r in rows]

    async def review_kyc(self, submission_id: UUID, reviewer_id: int,
                          decision: str, comment: Optional[str] = None,
                          risk_level: Optional[str] = None) -> Optional[Dict]:
        """Admin reviews KYC submission."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow("""
                    UPDATE kyc_submissions
                    SET status = $1, reviewer_id = $2, reviewed_at = $3,
                        review_comment = $4, risk_level = COALESCE($5, risk_level)
                    WHERE id = $6 RETURNING *
                """, decision, reviewer_id, datetime.utcnow(), comment, risk_level, submission_id)

                if not row:
                    return None

                # If approved, mark user as kyc_verified
                if decision == 'approved':
                    await conn.execute("""
                        UPDATE users SET kyc_verified = TRUE, kyc_verified_at = $1
                        WHERE id = $2
                    """, datetime.utcnow(), row['user_id'])

                # If rejected, ensure user is not verified
                if decision == 'rejected':
                    await conn.execute("""
                        UPDATE users SET kyc_verified = FALSE, kyc_verified_at = NULL
                        WHERE id = $1
                    """, row['user_id'])

                return dict(row)

    # ==================== KYB ====================

    async def submit_kyb(self, org_id: UUID, submitted_by: int, data: Dict) -> Dict:
        """Company admin submits KYB documents."""
        async with self.pool.acquire() as conn:
            existing = await conn.fetchrow("""
                SELECT id, status FROM kyb_submissions
                WHERE organization_id = $1 AND status IN ('pending', 'in_review', 'approved')
                ORDER BY created_at DESC LIMIT 1
            """, org_id)
            if existing:
                if existing['status'] == 'approved':
                    return {"error": "KYB already approved", "submission_id": str(existing['id'])}
                if existing['status'] in ('pending', 'in_review'):
                    return {"error": "KYB submission already pending", "submission_id": str(existing['id'])}

            row = await conn.fetchrow("""
                INSERT INTO kyb_submissions (
                    organization_id, submitted_by, company_name, registration_number,
                    tax_id, legal_address, country, documents, beneficiaries, status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'pending')
                RETURNING *
            """,
                org_id, submitted_by,
                data['company_name'],
                data.get('registration_number'),
                data.get('tax_id'),
                data.get('legal_address'),
                data.get('country'),
                json.dumps(data.get('documents', [])),
                json.dumps(data.get('beneficiaries', []))
            )
            return dict(row)

    async def get_kyb_status(self, org_id: UUID) -> Optional[Dict]:
        """Get KYB status for organization."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, status, risk_level, review_comment, submitted_at, reviewed_at
                FROM kyb_submissions
                WHERE organization_id = $1
                ORDER BY created_at DESC LIMIT 1
            """, org_id)
            return dict(row) if row else None

    async def get_kyb_submissions(self, status_filter: Optional[str] = None,
                                   limit: int = 50, offset: int = 0) -> List[Dict]:
        """Admin: list KYB submissions."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT s.*, o.name as org_name
                FROM kyb_submissions s
                JOIN organizations o ON s.organization_id = o.id
                WHERE ($1::text IS NULL OR s.status = $1)
                ORDER BY s.created_at DESC
                LIMIT $2 OFFSET $3
            """, status_filter, limit, offset)
            return [dict(r) for r in rows]

    async def review_kyb(self, submission_id: UUID, reviewer_id: int,
                          decision: str, comment: Optional[str] = None,
                          risk_level: Optional[str] = None) -> Optional[Dict]:
        """Admin reviews KYB submission."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow("""
                    UPDATE kyb_submissions
                    SET status = $1, reviewer_id = $2, reviewed_at = $3,
                        review_comment = $4, risk_level = COALESCE($5, risk_level)
                    WHERE id = $6 RETURNING *
                """, decision, reviewer_id, datetime.utcnow(), comment, risk_level, submission_id)

                if not row:
                    return None

                if decision == 'approved':
                    await conn.execute("""
                        UPDATE organizations SET kyb_verified = TRUE, kyb_verified_at = $1
                        WHERE id = $2
                    """, datetime.utcnow(), row['organization_id'])

                if decision == 'rejected':
                    await conn.execute("""
                        UPDATE organizations SET kyb_verified = FALSE, kyb_verified_at = NULL
                        WHERE id = $1
                    """, row['organization_id'])

                return dict(row)

    # ==================== Verification checks ====================

    async def is_user_kyc_verified(self, user_id: int) -> bool:
        """Check if user has passed KYC."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT kyc_verified FROM users WHERE id = $1", user_id
            )
            return bool(row and row['kyc_verified'])

    async def is_org_kyb_verified(self, org_id: UUID) -> bool:
        """Check if organization has passed KYB."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT kyb_verified FROM organizations WHERE id = $1", org_id
            )
            return bool(row and row['kyb_verified'])
