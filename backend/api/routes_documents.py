"""Document token endpoints for OnlyOffice integration."""

import os
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from backend.rbac import require_roles

logger = logging.getLogger("orgon.documents")

router = APIRouter(prefix="/api/documents", tags=["documents"])

_AUTH_ANY = require_roles(
    "platform_admin", "company_admin", "company_operator", "company_auditor", "end_user",
)

ONLYOFFICE_SECRET = os.getenv("ONLYOFFICE_JWT_SECRET", "orgon-onlyoffice-2026")


class DocumentTokenRequest(BaseModel):
    file_url: str
    file_name: str
    file_type: str  # docx, xlsx, pptx, pdf
    mode: str = "view"  # view or edit
    user_id: Optional[str] = None
    user_name: Optional[str] = None


@router.post("/token")
async def generate_doc_token(
    payload: DocumentTokenRequest,
    request: Request,
    user: dict = Depends(_AUTH_ANY),
):
    """Generate JWT token for OnlyOffice document editor."""
    try:
        import jwt
    except ImportError:
        raise HTTPException(status_code=500, detail="PyJWT not installed")

    doc_type = "word"
    if payload.file_type in ("xls", "xlsx", "ods", "csv"):
        doc_type = "cell"
    elif payload.file_type in ("ppt", "pptx", "odp"):
        doc_type = "slide"

    token_payload = {
        "document": {
            "fileType": payload.file_type,
            "title": payload.file_name,
            "url": payload.file_url,
            "key": f"{payload.file_name}_{int(datetime.now(timezone.utc).timestamp())}",
        },
        "editorConfig": {
            "mode": payload.mode,
            "lang": "ru",
            "user": {
                "id": payload.user_id or "anonymous",
                "name": payload.user_name or "User",
            },
        },
        "documentType": doc_type,
    }

    token = jwt.encode(token_payload, ONLYOFFICE_SECRET, algorithm="HS256")
    return {"token": token, "config": token_payload}


@router.get("/supported-formats")
async def supported_formats(user: dict = Depends(_AUTH_ANY)):
    """List supported document formats."""
    return {
        "word": ["doc", "docx", "odt", "txt", "pdf", "rtf"],
        "cell": ["xls", "xlsx", "ods", "csv"],
        "slide": ["ppt", "pptx", "odp"],
    }
