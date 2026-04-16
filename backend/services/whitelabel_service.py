"""White Label Service — Branding, Custom Domains, Email Templates."""
import asyncpg
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
import secrets

class WhiteLabelService:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
    
    # ==================== Branding ====================
    
    async def get_branding(self, org_id: UUID) -> Optional[Dict]:
        """Get organization branding."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM organization_branding WHERE organization_id = $1
            """, org_id)
            return dict(row) if row else None
    
    async def create_or_update_branding(self, org_id: UUID, branding_data: Dict) -> Dict:
        """Create or update organization branding."""
        async with self.pool.acquire() as conn:
            # Check if branding exists
            existing = await conn.fetchrow(
                "SELECT id FROM organization_branding WHERE organization_id = $1", org_id
            )
            
            if existing:
                # Update
                row = await conn.fetchrow("""
                    UPDATE organization_branding
                    SET logo_url = COALESCE($2, logo_url),
                        logo_dark_url = COALESCE($3, logo_dark_url),
                        favicon_url = COALESCE($4, favicon_url),
                        color_primary = COALESCE($5, color_primary),
                        color_secondary = COALESCE($6, color_secondary),
                        color_accent = COALESCE($7, color_accent),
                        platform_name = COALESCE($8, platform_name),
                        tagline = COALESCE($9, tagline),
                        support_email = COALESCE($10, support_email),
                        social_links = COALESCE($11, social_links),
                        updated_at = $12
                    WHERE organization_id = $1
                    RETURNING *
                """, org_id,
                    branding_data.get('logo_url'),
                    branding_data.get('logo_dark_url'),
                    branding_data.get('favicon_url'),
                    branding_data.get('color_primary'),
                    branding_data.get('color_secondary'),
                    branding_data.get('color_accent'),
                    branding_data.get('platform_name'),
                    branding_data.get('tagline'),
                    branding_data.get('support_email'),
                    branding_data.get('social_links'),
                    datetime.utcnow()
                )
            else:
                # Create
                row = await conn.fetchrow("""
                    INSERT INTO organization_branding (
                        organization_id, logo_url, logo_dark_url, favicon_url,
                        color_primary, color_secondary, color_accent,
                        platform_name, tagline, support_email, social_links
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    RETURNING *
                """, org_id,
                    branding_data.get('logo_url'),
                    branding_data.get('logo_dark_url'),
                    branding_data.get('favicon_url'),
                    branding_data.get('color_primary', '#3B82F6'),
                    branding_data.get('color_secondary', '#10B981'),
                    branding_data.get('color_accent', '#F59E0B'),
                    branding_data.get('platform_name', 'ORGON'),
                    branding_data.get('tagline'),
                    branding_data.get('support_email'),
                    branding_data.get('social_links', {})
                )
            
            return dict(row)
    
    # ==================== Email Templates ====================
    
    async def get_email_template(self, org_id: UUID, template_type: str) -> Optional[Dict]:
        """Get email template by type."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM email_templates
                WHERE organization_id = $1 AND template_type = $2 AND is_active = TRUE
            """, org_id, template_type)
            return dict(row) if row else None
    
    async def list_email_templates(self, org_id: UUID) -> List[Dict]:
        """List all email templates for organization."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM email_templates WHERE organization_id = $1
                ORDER BY template_type
            """, org_id)
            return [dict(r) for r in rows]
    
    async def create_or_update_email_template(self, org_id: UUID, template_type: str,
                                               subject: str, body_html: str,
                                               user_id: UUID) -> Dict:
        """Create or update email template."""
        async with self.pool.acquire() as conn:
            existing = await conn.fetchrow("""
                SELECT id FROM email_templates
                WHERE organization_id = $1 AND template_type = $2
            """, org_id, template_type)
            
            if existing:
                # Update
                row = await conn.fetchrow("""
                    UPDATE email_templates
                    SET subject = $3, body_html = $4, updated_at = $5
                    WHERE id = $6
                    RETURNING *
                """, org_id, template_type, subject, body_html,
                    datetime.utcnow(), existing['id'])
            else:
                # Create
                row = await conn.fetchrow("""
                    INSERT INTO email_templates (
                        organization_id, template_type, template_name,
                        subject, body_html, created_by
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING *
                """, org_id, template_type, template_type.replace('_', ' ').title(),
                    subject, body_html, user_id)
            
            return dict(row)
    
    # ==================== Custom Domains ====================
    
    async def create_custom_domain(self, org_id: UUID, domain: str) -> Dict:
        """Create custom domain verification record."""
        verification_token = secrets.token_urlsafe(16)
        verification_record = f"TXT _orgon-verify.{domain} {verification_token}"
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO custom_domains (
                    organization_id, domain, verification_token, verification_record
                ) VALUES ($1, $2, $3, $4)
                RETURNING *
            """, org_id, domain, verification_token, verification_record)
            return dict(row)
    
    async def verify_custom_domain(self, domain_id: UUID) -> Dict:
        """Verify custom domain (called after DNS check passes)."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                UPDATE custom_domains
                SET verified = TRUE, verified_at = $1, updated_at = $1
                WHERE id = $2
                RETURNING *
            """, datetime.utcnow(), domain_id)
            return dict(row) if row else None
    
    async def get_custom_domains(self, org_id: UUID) -> List[Dict]:
        """List custom domains for organization."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM custom_domains WHERE organization_id = $1
                ORDER BY is_primary DESC, created_at DESC
            """, org_id)
            return [dict(r) for r in rows]
    
    # ==================== Upload Assets ====================
    
    async def create_upload_asset(self, org_id: UUID, file_name: str, file_type: str,
                                   storage_url: str, asset_type: str, user_id: UUID) -> Dict:
        """Record uploaded asset."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO upload_assets (
                    organization_id, file_name, file_type, storage_url,
                    asset_type, uploaded_by
                ) VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING *
            """, org_id, file_name, file_type, storage_url, asset_type, user_id)
            return dict(row)
    
    async def get_assets(self, org_id: UUID, asset_type: Optional[str] = None) -> List[Dict]:
        """List uploaded assets."""
        async with self.pool.acquire() as conn:
            if asset_type:
                rows = await conn.fetch("""
                    SELECT * FROM upload_assets
                    WHERE organization_id = $1 AND asset_type = $2
                    ORDER BY uploaded_at DESC
                """, org_id, asset_type)
            else:
                rows = await conn.fetch("""
                    SELECT * FROM upload_assets WHERE organization_id = $1
                    ORDER BY uploaded_at DESC
                """, org_id)
            return [dict(r) for r in rows]
