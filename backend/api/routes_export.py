"""
Export endpoints for transactions and data.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from backend.rbac import require_roles
from fastapi.responses import StreamingResponse
from datetime import datetime
from typing import Optional
import io
import csv
import logging

logger = logging.getLogger("orgon.api.export")

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/transactions/csv")
async def export_transactions_csv(
    user: dict = Depends(require_roles("company_admin", "company_auditor")),
    wallet: Optional[str] = Query(None, description="Filter by wallet name"),
    status: Optional[str] = Query(None, description="Filter by status"),
    network: Optional[str] = Query(None, description="Filter by network"),
    from_date: Optional[str] = Query(None, description="From date (ISO format)"),
    to_date: Optional[str] = Query(None, description="To date (ISO format)"),
    limit: int = Query(10000, description="Maximum number of transactions"),
):
    """
    Export transactions to CSV file.

    Filters:
    - wallet: Filter by wallet name
    - status: Filter by status (confirmed, pending, failed)
    - network: Filter by network ID
    - from_date: Start date (ISO format)
    - to_date: End date (ISO format)
    - limit: Maximum transactions (default: 10000)

    Returns:
        CSV file download
    """
    from backend.main import get_transaction_service

    service = get_transaction_service()
    if not service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        # Build filters
        filters = {}
        if wallet:
            filters["wallet_name"] = wallet
        if status:
            filters["status"] = status
        if network:
            filters["network"] = network
        if from_date:
            filters["from_date"] = from_date
        if to_date:
            filters["to_date"] = to_date

        # Fetch transactions
        transactions = await service.list_transactions(
            limit=limit,
            offset=0,
            filters=filters if filters else None
        )

        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow([
            "Transaction ID",
            "Wallet",
            "Token",
            "Amount",
            "From Address",
            "To Address",
            "Status",
            "Network",
            "Timestamp",
            "Description",
        ])

        # Write data rows
        for tx in transactions:
            writer.writerow([
                tx.get("tx_unid", ""),
                tx.get("wallet_name", ""),
                tx.get("token", ""),
                tx.get("value", ""),
                tx.get("from_addr", ""),
                tx.get("to_addr", ""),
                tx.get("status", ""),
                tx.get("network", ""),
                tx.get("timestamp", ""),
                tx.get("info", ""),
            ])

        # Prepare response
        csv_content = output.getvalue()
        output.close()

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"orgon_transactions_{timestamp}.csv"

        logger.info(f"Exported {len(transactions)} transactions to CSV")

        return StreamingResponse(
            io.BytesIO(csv_content.encode("utf-8")),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/wallets/csv")
async def export_wallets_csv(user: dict = Depends(require_roles("company_admin", "company_auditor"))):
    """
    Export wallets to CSV file.

    Returns:
        CSV file download with all wallets and their balances
    """
    from backend.main import get_wallet_service

    service = get_wallet_service()
    if not service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        # Fetch wallets
        wallets = await service.list_wallets()

        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow([
            "Wallet Name",
            "Address",
            "Token",
            "Balance",
            "Network",
        ])

        # Write data rows
        for wallet in wallets:
            wallet_name = wallet.get("name", "")
            address = wallet.get("address", "")
            
            balances = wallet.get("balances", [])
            if balances:
                for balance in balances:
                    writer.writerow([
                        wallet_name,
                        address,
                        balance.get("token_name", ""),
                        balance.get("balance", "0"),
                        balance.get("network", ""),
                    ])
            else:
                # Wallet with no balances
                writer.writerow([
                    wallet_name,
                    address,
                    "",
                    "0",
                    "",
                ])

        # Prepare response
        csv_content = output.getvalue()
        output.close()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"orgon_wallets_{timestamp}.csv"

        logger.info(f"Exported {len(wallets)} wallets to CSV")

        return StreamingResponse(
            io.BytesIO(csv_content.encode("utf-8")),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except Exception as e:
        logger.error(f"Wallets export failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
