"""API routes for address book (contacts)."""

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from typing import Optional

from backend.services.address_book_service import AddressBookService
from backend.rbac import require_roles

router = APIRouter(prefix="/api/contacts", tags=["contacts"])


# Dependency injection helper
def get_address_book_service(request: Request) -> AddressBookService:
    """Get AddressBookService from app state."""
    return request.app.state.address_book_service


# Pydantic models
class ContactCreate(BaseModel):
    """Request model for creating a contact."""
    name: str = Field(..., min_length=1, max_length=200)
    address: str = Field(..., min_length=1, max_length=200)
    network: Optional[str] = Field(None, max_length=50)
    category: Optional[str] = Field(None, pattern="^(personal|business|exchange|other)$")
    notes: Optional[str] = Field(None, max_length=1000)
    favorite: bool = False


class ContactUpdate(BaseModel):
    """Request model for updating a contact."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    address: Optional[str] = Field(None, min_length=1, max_length=200)
    network: Optional[str] = Field(None, max_length=50)
    category: Optional[str] = Field(None, pattern="^(personal|business|exchange|other)$")
    notes: Optional[str] = Field(None, max_length=1000)
    favorite: Optional[bool] = None


@router.get("")
async def get_contacts(
    limit: int = 50,
    offset: int = 0,
    category: Optional[str] = None,
    search: Optional[str] = None,
    favorites_only: bool = False,
    user: dict = Depends(require_roles("company_admin", "company_operator")), service: AddressBookService = Depends(get_address_book_service)
):
    """
    Get contacts with optional filtering.
    
    Query parameters:
    - limit: Maximum number of results (default: 50)
    - offset: Pagination offset (default: 0)
    - category: Filter by category (personal/business/exchange/other)
    - search: Search by name or address
    - favorites_only: Return only favorites (default: false)
    """
    
    try:
        contacts = await service.get_contacts(
            limit=limit,
            offset=offset,
            category=category,
            search=search,
            favorites_only=favorites_only
        )
        return contacts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_contacts(
    q: str, 
    limit: int = 10,
    user: dict = Depends(require_roles("company_admin", "company_operator")), service: AddressBookService = Depends(get_address_book_service)
):
    """
    Quick search contacts by name or address.
    
    Query parameters:
    - q: Search query
    - limit: Maximum results (default: 10)
    """
    
    try:
        contacts = await service.search_contacts(q, limit)
        return contacts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/favorites")
async def get_favorites(user: dict = Depends(require_roles("company_admin", "company_operator")), service: AddressBookService = Depends(get_address_book_service)):
    """Get all favorite contacts."""
    
    try:
        favorites = await service.get_favorites()
        return favorites
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_contact(
    contact: ContactCreate,
    user: dict = Depends(require_roles("company_admin", "company_operator")), service: AddressBookService = Depends(get_address_book_service)
):
    """
    Create a new contact.
    
    Request body:
    - name: Contact name (required)
    - address: Wallet address (required)
    - network: Network (optional)
    - category: Category - personal/business/exchange/other (optional)
    - notes: Additional notes (optional)
    - favorite: Mark as favorite (default: false)
    """
    
    try:
        new_contact = await service.create_contact(
            name=contact.name,
            address=contact.address,
            network=contact.network,
            category=contact.category,
            notes=contact.notes,
            favorite=contact.favorite
        )
        return new_contact
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{contact_id}")
async def get_contact(
    contact_id: int,
    user: dict = Depends(require_roles("company_admin", "company_operator")), service: AddressBookService = Depends(get_address_book_service)
):
    """Get a single contact by ID."""
    
    try:
        contact = await service.get_contact(contact_id)
        if not contact:
            raise HTTPException(status_code=404, detail=f"Contact {contact_id} not found")
        return contact
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{contact_id}")
async def update_contact(
    contact_id: int, 
    updates: ContactUpdate,
    user: dict = Depends(require_roles("company_admin", "company_operator")), service: AddressBookService = Depends(get_address_book_service)
):
    """
    Update a contact.
    
    Only provided fields will be updated.
    """
    
    try:
        updated = await service.update_contact(
            contact_id=contact_id,
            name=updates.name,
            address=updates.address,
            network=updates.network,
            category=updates.category,
            notes=updates.notes,
            favorite=updates.favorite
        )
        
        if not updated:
            raise HTTPException(status_code=404, detail=f"Contact {contact_id} not found")
        
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{contact_id}")
async def delete_contact(
    contact_id: int,
    user: dict = Depends(require_roles("company_admin", "company_operator")), service: AddressBookService = Depends(get_address_book_service)
):
    """Delete a contact."""
    
    try:
        deleted = await service.delete_contact(contact_id)
        
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Contact {contact_id} not found")
        
        return {"success": True, "message": f"Contact {contact_id} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{contact_id}/toggle-favorite")
async def toggle_favorite(
    contact_id: int,
    user: dict = Depends(require_roles("company_admin", "company_operator")), service: AddressBookService = Depends(get_address_book_service)
):
    """Toggle favorite status of a contact."""
    
    try:
        updated = await service.toggle_favorite(contact_id)
        
        if not updated:
            raise HTTPException(status_code=404, detail=f"Contact {contact_id} not found")
        
        return updated
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
