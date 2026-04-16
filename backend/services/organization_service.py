"""Organization business logic with multi-tenancy support."""

import json
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from backend.database.db_postgres import AsyncDatabase
from backend.events.manager import get_event_manager, EventType
from backend.api.schemas import (
    OrganizationCreate,
    OrganizationUpdate,
    UserOrganizationCreate,
    UserOrganizationUpdate,
    OrganizationSettingsUpdate,
    OrganizationStatus,
    UserRole,
)

logger = logging.getLogger("orgon.services.organization")


class OrganizationService:
    """Service for managing organizations with multi-tenancy and RLS."""

    def __init__(self, db: AsyncDatabase):
        self._db = db

    # ============================================================
    # RLS Context Management
    # ============================================================

    async def set_tenant_context(self, organization_id) -> None:
        """
        Set RLS tenant context for the current session.
        
        Args:
            organization_id: Organization ID to set as current tenant
        """
        await self._db.execute(
            "SELECT set_tenant_context($1)",
            params=(str(organization_id),)
        )
        logger.debug("Set tenant context: org_id=%d", organization_id)

    async def clear_tenant_context(self) -> None:
        """Clear RLS tenant context."""
        await self._db.execute("SELECT clear_tenant_context()")
        logger.debug("Cleared tenant context")

    # ============================================================
    # Organization CRUD
    # ============================================================

    async def create_organization(
        self,
        data: OrganizationCreate,
        creator_user_id: int
    ) -> dict:
        """
        Create a new organization and assign creator as admin.
        
        Args:
            data: Organization creation data
            creator_user_id: User ID of the creator (will become admin)
            
        Returns:
            Created organization dictionary
        """
        now = datetime.now()  # Remove timezone for Postgres timestamp without time zone
        
        # Insert organization
        query = """
            INSERT INTO organizations (
                name, slug, license_type, status,
                address, city, country, phone, email,
                created_at, updated_at, created_by
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            RETURNING *
        """
        
        org = await self._db.fetchrow(
            query,
            params=(
                data.name,
                data.slug,
                data.license_type.value,
                OrganizationStatus.active.value,
                getattr(data, 'address', None),
                getattr(data, 'city', None),
                getattr(data, 'country', None),
                getattr(data, 'phone', None),
                getattr(data, 'email', None),
                now,
                now,
                creator_user_id,
            )
        )
        
        org_dict = dict(org)
        org_id = org_dict["id"]
        
        # Assign creator as admin
        await self._add_member(org_id, creator_user_id, UserRole.admin)
        
        # Create default settings
        await self._create_default_settings(org_id)
        
        logger.info(
            "Organization created: id=%d, name=%s, creator=%d",
            org_id, data.name, creator_user_id
        )
        
        # Emit event
        event_manager = get_event_manager()
        await event_manager.emit(EventType.WALLET_CREATED, {  # TODO: Add ORG_CREATED event type
            "organization_id": org_id,
            "name": data.name,
            "license_type": data.license_type.value,
            "creator_user_id": creator_user_id,
        })
        
        return org_dict

    async def list_organizations(
        self,
        user_id: Optional[int] = None,
        status: Optional[OrganizationStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[dict]:
        """
        List organizations with optional filters.
        
        Args:
            user_id: Filter by user membership (if provided)
            status: Filter by organization status
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            List of organization dictionaries
        """
        if user_id is not None:
            # Get organizations where user is a member
            query = """
                SELECT o.* FROM organizations o
                INNER JOIN user_organizations uo ON o.id = uo.organization_id
                WHERE uo.user_id = $1
            """
            params = [user_id]
            
            if status:
                query += " AND o.status = $2"
                params.append(status.value)
            
            query += " ORDER BY o.created_at DESC LIMIT $%d OFFSET $%d" % (
                len(params) + 1, len(params) + 2
            )
            params.extend([limit, offset])
            
            orgs = await self._db.fetch(query, params=tuple(params))
        else:
            # Get all organizations (admin view)
            query = "SELECT * FROM organizations"
            params = []
            
            if status:
                query += " WHERE status = $1"
                params.append(status.value)
            
            query += " ORDER BY created_at DESC LIMIT $%d OFFSET $%d" % (
                len(params) + 1, len(params) + 2
            )
            params.extend([limit, offset])
            
            orgs = await self._db.fetch(query, params=tuple(params))
        
        return [dict(org) for org in orgs]

    async def count_organizations(
        self,
        user_id: Optional[int] = None,
        status: Optional[OrganizationStatus] = None
    ) -> int:
        """Count organizations with filters."""
        if user_id is not None:
            query = """
                SELECT COUNT(*) FROM organizations o
                INNER JOIN user_organizations uo ON o.id = uo.organization_id
                WHERE uo.user_id = $1
            """
            params = [user_id]
            
            if status:
                query += " AND o.status = $2"
                params.append(status.value)
            
            result = await self._db.fetchrow(query, params=tuple(params))
        else:
            query = "SELECT COUNT(*) FROM organizations"
            params = []
            
            if status:
                query += " WHERE status = $1"
                params.append(status.value)
            
            result = await self._db.fetchrow(query, params=tuple(params) if params else None)
        
        return result["count"] if result else 0

    async def get_organization(self, org_id: int) -> Optional[dict]:
        """
        Get organization by ID.
        
        Args:
            org_id: Organization ID
            
        Returns:
            Organization dictionary or None if not found
        """
        org = await self._db.fetchrow(
            "SELECT * FROM organizations WHERE id = $1",
            params=(org_id,)
        )
        return dict(org) if org else None

    async def get_organization_by_slug(self, slug: str) -> Optional[dict]:
        """Get organization by slug."""
        org = await self._db.fetchrow(
            "SELECT * FROM organizations WHERE slug = $1",
            params=(slug,)
        )
        return dict(org) if org else None

    async def update_organization(
        self,
        org_id: int,
        data: OrganizationUpdate
    ) -> Optional[dict]:
        """
        Update organization details.
        
        Args:
            org_id: Organization ID
            data: Update data (only provided fields will be updated)
            
        Returns:
            Updated organization or None if not found
        """
        # Build dynamic UPDATE query for provided fields only
        update_fields = []
        params = []
        param_idx = 1
        
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if field == "license_type":
                value = value.value
            elif field == "status":
                value = value.value
            
            update_fields.append(f"{field} = ${param_idx}")
            params.append(value)
            param_idx += 1
        
        if not update_fields:
            # No fields to update
            return await self.get_organization(org_id)
        
        # Add updated_at
        update_fields.append(f"updated_at = ${param_idx}")
        params.append(datetime.now())
        param_idx += 1
        
        # Add org_id for WHERE clause
        params.append(org_id)
        
        query = f"""
            UPDATE organizations
            SET {', '.join(update_fields)}
            WHERE id = ${param_idx}
            RETURNING *
        """
        
        org = await self._db.fetchrow(query, params=tuple(params))
        
        if org:
            logger.info("Organization updated: id=%d, fields=%s", org_id, list(update_data.keys()))
            return dict(org)
        
        return None

    async def delete_organization(self, org_id: UUID) -> bool:
        """
        Delete organization (soft delete by setting status to cancelled).
        
        Args:
            org_id: Organization ID
            
        Returns:
            True if deleted, False if not found
        """
        result = await self._db.execute(
            """UPDATE organizations 
               SET status = $1, updated_at = $2 
               WHERE id = $3""",
            params=(OrganizationStatus.cancelled.value, datetime.now(), org_id)
        )
        
        # result is a string like "UPDATE 1" or "UPDATE 0"
        updated = result.startswith("UPDATE") and not result.endswith(" 0")
        
        if updated:
            logger.info("Organization deleted (soft): id=%s", org_id)
            return True
        
        return False

    # ============================================================
    # Organization Members Management
    # ============================================================

    async def list_members(
        self,
        org_id: int,
        limit: int = 100,
        offset: int = 0
    ) -> list[dict]:
        """
        List organization members with user details.
        
        Args:
            org_id: Organization ID
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            List of member dictionaries with user info
        """
        query = """
            SELECT 
                uo.organization_id, uo.user_id, uo.role,
                uo.created_at,
                u.email, u.full_name as name
            FROM user_organizations uo
            INNER JOIN users u ON uo.user_id = u.id
            WHERE uo.organization_id = $1
            ORDER BY uo.created_at ASC
            LIMIT $2 OFFSET $3
        """
        
        members = await self._db.fetch(query, params=(org_id, limit, offset))
        return [dict(m) for m in members]

    async def count_members(self, org_id: int) -> int:
        """Count organization members."""
        result = await self._db.fetchrow(
            "SELECT COUNT(*) FROM user_organizations WHERE organization_id = $1",
            params=(org_id,)
        )
        return result["count"] if result else 0

    async def add_member(
        self,
        org_id: int,
        data: UserOrganizationCreate
    ) -> dict:
        """
        Add user to organization.
        
        Args:
            org_id: Organization ID
            data: Member creation data
            
        Returns:
            Created membership dictionary
        """
        return await self._add_member(org_id, data.user_id, data.role)

    async def _add_member(
        self,
        org_id: int,
        user_id: int,
        role: UserRole
    ) -> dict:
        """Internal method to add member."""
        now = datetime.now()  # Remove timezone for Postgres timestamp without time zone
        
        query = """
            INSERT INTO user_organizations (organization_id, user_id, role, created_at)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id, organization_id) 
            DO UPDATE SET role = EXCLUDED.role
            RETURNING *
        """
        
        member = await self._db.fetchrow(
            query,
            params=(org_id, user_id, role.value, now)
        )
        
        logger.info("Member added: org_id=%d, user_id=%d, role=%s", org_id, user_id, role.value)
        
        return dict(member)

    async def update_member_role(
        self,
        org_id: int,
        user_id: int,
        data: UserOrganizationUpdate
    ) -> Optional[dict]:
        """
        Update member's role.
        
        Args:
            org_id: Organization ID
            user_id: User ID
            data: Update data with new role
            
        Returns:
            Updated membership or None if not found
        """
        query = """
            UPDATE user_organizations
            SET role = $1, updated_at = $2
            WHERE organization_id = $3 AND user_id = $4
            RETURNING *
        """
        
        member = await self._db.fetchrow(
            query,
            params=(data.role.value, datetime.now(), org_id, user_id)
        )
        
        if member:
            logger.info("Member role updated: org_id=%d, user_id=%d, role=%s", 
                       org_id, user_id, data.role.value)
            return dict(member)
        
        return None

    async def remove_member(self, org_id: int, user_id: int) -> bool:
        """
        Remove user from organization.
        
        Args:
            org_id: Organization ID
            user_id: User ID
            
        Returns:
            True if removed, False if not found
        """
        result = await self._db.execute(
            "DELETE FROM user_organizations WHERE organization_id = $1 AND user_id = $2",
            params=(org_id, user_id)
        )
        
        if result.rowcount > 0:
            logger.info("Member removed: org_id=%d, user_id=%d", org_id, user_id)
            return True
        
        return False

    async def get_user_role(self, org_id: int, user_id: int) -> Optional[UserRole]:
        """Get user's role in organization."""
        member = await self._db.fetchrow(
            "SELECT role FROM user_organizations WHERE organization_id = $1 AND user_id = $2",
            params=(org_id, user_id)
        )
        
        if member:
            return UserRole(member["role"])
        
        return None

    # ============================================================
    # Organization Settings Management
    # ============================================================

    async def get_settings(self, org_id: int) -> Optional[dict]:
        """
        Get organization settings.
        
        Args:
            org_id: Organization ID
            
        Returns:
            Settings dictionary or None if not found
        """
        settings = await self._db.fetchrow(
            "SELECT * FROM organization_settings WHERE organization_id = $1",
            params=(org_id,)
        )
        return dict(settings) if settings else None

    async def update_settings(
        self,
        org_id: int,
        data: OrganizationSettingsUpdate
    ) -> Optional[dict]:
        """
        Update organization settings.
        
        Args:
            org_id: Organization ID
            data: Settings update data
            
        Returns:
            Updated settings or None if not found
        """
        # Build dynamic UPDATE for JSONB fields
        update_fields = []
        params = []
        param_idx = 1
        
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            update_fields.append(f"{field} = ${param_idx}")
            params.append(value)
            param_idx += 1
        
        if not update_fields:
            return await self.get_settings(org_id)
        
        # Add updated_at
        update_fields.append(f"updated_at = ${param_idx}")
        params.append(datetime.now())
        param_idx += 1
        
        # Add org_id
        params.append(org_id)
        
        query = f"""
            UPDATE organization_settings
            SET {', '.join(update_fields)}
            WHERE organization_id = ${param_idx}
            RETURNING *
        """
        
        settings = await self._db.fetchrow(query, params=tuple(params))
        
        if settings:
            logger.info("Settings updated: org_id=%d, fields=%s", org_id, list(update_data.keys()))
            return dict(settings)
        
        return None

    async def _create_default_settings(self, org_id: int) -> dict:
        """Create default settings for new organization."""
        
        query = """
            INSERT INTO organization_settings (
                organization_id,
                billing_enabled,
                kyc_enabled,
                fiat_enabled,
                features,
                limits,
                branding,
                integrations
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
        """
        
        default_features = {
            "multi_sig": True,
            "scheduled_transactions": True,
            "api_access": False,
            "white_label": False
        }
        
        default_limits = {
            "max_wallets": 10,
            "max_monthly_volume": 50000.00,
            "max_transaction_size": 10000.00,
            "rate_limit_per_minute": 60
        }
        
        default_branding = {
            "logo_url": None,
            "primary_color": "#3B82F6",
            "custom_domain": None
        }
        
        default_integrations = {
            "webhook_url": None,
            "api_key": None,
            "enabled_integrations": []
        }
        
        settings = await self._db.fetchrow(
            query,
            params=(
                org_id,
                True,  # billing_enabled
                False,  # kyc_enabled
                False,  # fiat_enabled
                json.dumps(default_features),
                json.dumps(default_limits),
                json.dumps(default_branding),
                json.dumps(default_integrations),
            )
        )
        
        logger.info("Default settings created: org_id=%d", org_id)
        
        return dict(settings)
