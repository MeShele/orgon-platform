"""Address Book service for contact management."""

import logging
from typing import Optional
from datetime import datetime, timezone

from backend.database.db_postgres import AsyncDatabase

logger = logging.getLogger("orgon.services.address_book")


class AddressBookService:
    """
    Contact management for frequent recipients.
    
    Features:
    - CRUD operations for contacts
    - Search by name or address
    - Category filtering
    - Favorite contacts
    """

    def __init__(self, db: AsyncDatabase):
        self._db = db

    async def get_contacts(
        self,
        limit: int = 50,
        offset: int = 0,
        category: Optional[str] = None,
        search: Optional[str] = None,
        favorites_only: bool = False
    ) -> list[dict]:
        """
        Get contacts with optional filtering.
        
        Args:
            limit: Maximum number of contacts to return
            offset: Number of contacts to skip (pagination)
            category: Filter by category (personal/business/exchange/other)
            search: Search by name or address (case-insensitive)
            favorites_only: Return only favorite contacts
            
        Returns:
            List of contact dictionaries
        """
        query_parts = ["SELECT * FROM address_book WHERE 1=1"]
        params = []
        param_count = 0

        if category:
            param_count += 1
            query_parts.append(f"AND category = ${param_count}")
            params.append(category)

        if search:
            param_count += 1
            query_parts.append(f"AND (name ILIKE ${param_count} OR address ILIKE ${param_count})")
            params.append(f"%{search}%")

        if favorites_only:
            query_parts.append("AND favorite = TRUE")

        # Order: favorites first, then by name
        query_parts.append("ORDER BY favorite DESC, name ASC")
        
        param_count += 1
        query_parts.append(f"LIMIT ${param_count}")
        params.append(limit)
        
        param_count += 1
        query_parts.append(f"OFFSET ${param_count}")
        params.append(offset)

        query = " ".join(query_parts)
        
        rows = await self._db.fetch(query, tuple(params))
        return [dict(row) for row in rows]

    async def get_contact(self, contact_id: int) -> Optional[dict]:
        """
        Get a single contact by ID.
        
        Args:
            contact_id: Contact ID
            
        Returns:
            Contact dictionary or None if not found
        """
        row = await self._db.fetchrow(
            "SELECT * FROM address_book WHERE id = $1",
            params=(contact_id,)
        )
        return dict(row) if row else None

    async def create_contact(
        self,
        name: str,
        address: str,
        network: Optional[str] = None,
        category: Optional[str] = None,
        notes: Optional[str] = None,
        favorite: bool = False
    ) -> dict:
        """
        Create a new contact.
        
        Args:
            name: Contact name
            address: Wallet address
            network: Network (ethereum/polygon/etc)
            category: Category (personal/business/exchange/other)
            notes: Additional notes
            favorite: Mark as favorite
            
        Returns:
            Created contact dictionary
        """
        # Validate category
        if category and category not in ('personal', 'business', 'exchange', 'other'):
            raise ValueError(f"Invalid category: {category}. Must be one of: personal, business, exchange, other")

        now = datetime.now(timezone.utc)
        
        row = await self._db.fetchrow(
            """INSERT INTO address_book (name, address, network, category, notes, favorite, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
               RETURNING *""",
            params=(name, address, network, category, notes, favorite, now, now)
        )
        
        logger.info("Created contact: %s (%s)", name, address)
        return dict(row)

    async def update_contact(
        self,
        contact_id: int,
        name: Optional[str] = None,
        address: Optional[str] = None,
        network: Optional[str] = None,
        category: Optional[str] = None,
        notes: Optional[str] = None,
        favorite: Optional[bool] = None
    ) -> Optional[dict]:
        """
        Update a contact.
        
        Args:
            contact_id: Contact ID
            name: New name (optional)
            address: New address (optional)
            network: New network (optional)
            category: New category (optional)
            notes: New notes (optional)
            favorite: New favorite status (optional)
            
        Returns:
            Updated contact dictionary or None if not found
        """
        # Validate category
        if category and category not in ('personal', 'business', 'exchange', 'other'):
            raise ValueError(f"Invalid category: {category}")

        # Build dynamic UPDATE query
        updates = []
        params = []
        param_count = 0

        if name is not None:
            param_count += 1
            updates.append(f"name = ${param_count}")
            params.append(name)

        if address is not None:
            param_count += 1
            updates.append(f"address = ${param_count}")
            params.append(address)

        if network is not None:
            param_count += 1
            updates.append(f"network = ${param_count}")
            params.append(network)

        if category is not None:
            param_count += 1
            updates.append(f"category = ${param_count}")
            params.append(category)

        if notes is not None:
            param_count += 1
            updates.append(f"notes = ${param_count}")
            params.append(notes)

        if favorite is not None:
            param_count += 1
            updates.append(f"favorite = ${param_count}")
            params.append(favorite)

        if not updates:
            # Nothing to update
            return await self.get_contact(contact_id)

        # updated_at will be set by trigger
        param_count += 1
        params.append(contact_id)

        query = f"UPDATE address_book SET {', '.join(updates)} WHERE id = ${param_count} RETURNING *"
        
        row = await self._db.fetchrow(query, tuple(params))
        
        if row:
            logger.info("Updated contact ID %d", contact_id)
            return dict(row)
        return None

    async def delete_contact(self, contact_id: int) -> bool:
        """
        Delete a contact.
        
        Args:
            contact_id: Contact ID
            
        Returns:
            True if deleted, False if not found
        """
        result = await self._db.execute(
            "DELETE FROM address_book WHERE id = $1",
            params=(contact_id,)
        )
        
        # Check if any rows were affected
        deleted = result.split()[-1] != '0'
        
        if deleted:
            logger.info("Deleted contact ID %d", contact_id)
        
        return deleted

    async def search_contacts(self, query: str, limit: int = 10) -> list[dict]:
        """
        Quick search contacts by name or address.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of matching contacts
        """
        return await self.get_contacts(limit=limit, search=query)

    async def get_favorites(self) -> list[dict]:
        """
        Get all favorite contacts.
        
        Returns:
            List of favorite contacts
        """
        return await self.get_contacts(favorites_only=True, limit=100)

    async def toggle_favorite(self, contact_id: int) -> Optional[dict]:
        """
        Toggle favorite status of a contact.
        
        Args:
            contact_id: Contact ID
            
        Returns:
            Updated contact or None if not found
        """
        contact = await self.get_contact(contact_id)
        if not contact:
            return None
        
        return await self.update_contact(contact_id, favorite=not contact['favorite'])
