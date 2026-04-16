"""
Partner Address Book API
Saved addresses for B2B partners
"""

from fastapi import APIRouter, Request, HTTPException, status, Depends, Query
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

from backend.services.address_book_service import AddressBookService
from backend.api.middleware_b2b import get_partner_from_request


# Create router
router = APIRouter(prefix="/api/v1/partner/addresses", tags=["Partner API - Address Book"])


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

async def get_address_book_service(request: Request) -> AddressBookService:
    """Get AddressBookService instance from app state."""
    if not hasattr(request.app.state, "address_book_service"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "service_unavailable", "message": "Address book service not available"}
        )
    return request.app.state.address_book_service


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================

class AddressCreateRequest(BaseModel):
    """Create address request."""
    name: str = Field(..., description="Address name/label")
    address: str = Field(..., description="Blockchain address")
    network_id: int = Field(..., description="Network ID (5000=Tron mainnet, 5010=Tron Nile testnet)")
    label: Optional[str] = Field(None, description="Optional category label")
    notes: Optional[str] = Field(None, description="Optional notes")
    is_favorite: bool = Field(False, description="Mark as favorite")


class AddressUpdateRequest(BaseModel):
    """Update address request."""
    name: Optional[str] = Field(None, description="Address name/label")
    label: Optional[str] = Field(None, description="Category label")
    notes: Optional[str] = Field(None, description="Notes")
    is_favorite: Optional[bool] = Field(None, description="Favorite status")


class AddressResponse(BaseModel):
    """Address response."""
    id: str
    name: str
    address: str
    network_id: int
    label: Optional[str]
    notes: Optional[str]
    is_favorite: bool
    created_at: datetime
    updated_at: datetime


class AddressListResponse(BaseModel):
    """List of addresses."""
    addresses: List[AddressResponse]
    count: int


# ============================================================================
# ADDRESS BOOK ENDPOINTS
# ============================================================================

@router.post(
    "",
    response_model=AddressResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save Address",
    description="Save a blockchain address to address book."
)
async def create_address(
    request: Request,
    address_data: AddressCreateRequest,
    address_book_service: AddressBookService = Depends(get_address_book_service)
):
    """
    Save a blockchain address.
    
    **Authentication:** Requires valid API key + secret.
    
    **Request Body:**
    - `name`: Address name/label (e.g., "Salary Recipient")
    - `address`: Blockchain address
    - `network_id`: Network ID (5000=Tron mainnet, 5010=Tron Nile testnet)
    - `label`: Optional category (e.g., "Suppliers", "Employees")
    - `notes`: Optional notes
    - `is_favorite`: Mark as favorite
    
    **Returns:** Created address details.
    """
    partner = get_partner_from_request(request)
    
    # Validate address format based on network
    # TODO: Add network-specific address validation
    
    try:
        address_id = await address_book_service.create_address(
            name=address_data.name,
            address=address_data.address,
            network_id=address_data.network_id,
            label=address_data.label,
            notes=address_data.notes,
            is_favorite=address_data.is_favorite
        )
        
        # Fetch created address
        created_address = await address_book_service.get_address(address_id)
        
        if not created_address:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "creation_failed", "message": "Address saved but not found"}
            )
        
        return AddressResponse(
            id=str(created_address["id"]),
            name=created_address["name"],
            address=created_address["address"],
            network_id=created_address["network_id"],
            label=created_address.get("label"),
            notes=created_address.get("notes"),
            is_favorite=created_address.get("is_favorite", False),
            created_at=created_address["created_at"],
            updated_at=created_address["updated_at"]
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_request", "message": str(e)}
        )


@router.get(
    "",
    response_model=AddressListResponse,
    summary="List Addresses",
    description="Get all saved addresses for partner."
)
async def list_addresses(
    request: Request,
    network_id: Optional[int] = Query(None, description="Filter by network ID"),
    label: Optional[str] = Query(None, description="Filter by label"),
    favorites_only: bool = Query(False, description="Show only favorites"),
    search: Optional[str] = Query(None, description="Search by name or address"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    address_book_service: AddressBookService = Depends(get_address_book_service)
):
    """
    List saved addresses.
    
    **Authentication:** Requires valid API key + secret.
    
    **Query Parameters:**
    - `network_id`: Optional filter by network ID
    - `label`: Optional filter by label
    - `favorites_only`: Show only favorite addresses
    - `search`: Search by name or address (partial match)
    - `limit`: Max results per page (1-100, default 50)
    - `offset`: Pagination offset (default 0)
    
    **Returns:** List of saved addresses.
    """
    partner = get_partner_from_request(request)
    
    # Get addresses
    # TODO: Filter by partner_id
    addresses_data = await address_book_service.list_addresses(
        network_id=network_id,
        label=label,
        favorites_only=favorites_only,
        search=search,
        limit=limit,
        offset=offset
    )
    
    addresses = [
        AddressResponse(
            id=str(addr["id"]),
            name=addr["name"],
            address=addr["address"],
            network_id=addr["network_id"],
            label=addr.get("label"),
            notes=addr.get("notes"),
            is_favorite=addr.get("is_favorite", False),
            created_at=addr["created_at"],
            updated_at=addr["updated_at"]
        )
        for addr in addresses_data
    ]
    
    return AddressListResponse(
        addresses=addresses,
        count=len(addresses)
    )


@router.get(
    "/{address_id}",
    response_model=AddressResponse,
    summary="Get Address",
    description="Get details of a specific saved address."
)
async def get_address(
    request: Request,
    address_id: str,
    address_book_service: AddressBookService = Depends(get_address_book_service)
):
    """
    Get address details.
    
    **Authentication:** Requires valid API key + secret.
    
    **Path Parameters:**
    - `address_id`: Address ID
    
    **Returns:** Address details.
    """
    partner = get_partner_from_request(request)
    
    address = await address_book_service.get_address(address_id)
    
    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": f"Address {address_id} not found"}
        )
    
    # TODO: Verify partner owns this address
    
    return AddressResponse(
        id=str(address["id"]),
        name=address["name"],
        address=address["address"],
        network_id=address["network_id"],
        label=address.get("label"),
        notes=address.get("notes"),
        is_favorite=address.get("is_favorite", False),
        created_at=address["created_at"],
        updated_at=address["updated_at"]
    )


@router.put(
    "/{address_id}",
    response_model=AddressResponse,
    summary="Update Address",
    description="Update a saved address."
)
async def update_address(
    request: Request,
    address_id: str,
    update_data: AddressUpdateRequest,
    address_book_service: AddressBookService = Depends(get_address_book_service)
):
    """
    Update address details.
    
    **Authentication:** Requires valid API key + secret.
    
    **Path Parameters:**
    - `address_id`: Address ID
    
    **Request Body:**
    - `name`: Optional new name
    - `label`: Optional new label
    - `notes`: Optional new notes
    - `is_favorite`: Optional favorite status
    
    **Returns:** Updated address details.
    """
    partner = get_partner_from_request(request)
    
    # Get address first to verify ownership
    address = await address_book_service.get_address(address_id)
    
    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": f"Address {address_id} not found"}
        )
    
    # TODO: Verify partner owns this address
    
    # Update address
    success = await address_book_service.update_address(
        address_id=address_id,
        name=update_data.name,
        label=update_data.label,
        notes=update_data.notes,
        is_favorite=update_data.is_favorite
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "update_failed", "message": "Failed to update address"}
        )
    
    # Fetch updated address
    updated_address = await address_book_service.get_address(address_id)
    
    return AddressResponse(
        id=str(updated_address["id"]),
        name=updated_address["name"],
        address=updated_address["address"],
        network_id=updated_address["network_id"],
        label=updated_address.get("label"),
        notes=updated_address.get("notes"),
        is_favorite=updated_address.get("is_favorite", False),
        created_at=updated_address["created_at"],
        updated_at=updated_address["updated_at"]
    )


@router.delete(
    "/{address_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Address",
    description="Remove a saved address."
)
async def delete_address(
    request: Request,
    address_id: str,
    address_book_service: AddressBookService = Depends(get_address_book_service)
):
    """
    Delete a saved address.
    
    **Authentication:** Requires valid API key + secret.
    
    **Path Parameters:**
    - `address_id`: Address ID
    
    **Returns:** 204 No Content on success.
    """
    partner = get_partner_from_request(request)
    
    # Get address first to verify ownership
    address = await address_book_service.get_address(address_id)
    
    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": f"Address {address_id} not found"}
        )
    
    # TODO: Verify partner owns this address
    
    # Delete address
    success = await address_book_service.delete_address(address_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "deletion_failed", "message": "Failed to delete address"}
        )
