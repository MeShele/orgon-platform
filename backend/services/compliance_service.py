"""Compliance Service — KYC, AML, Regulatory Reports."""
import asyncpg
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID
import secrets

class ComplianceService:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
    
    # ==================== KYC ====================
    
    async def create_kyc_record(self, org_id: UUID, customer_name: str, customer_email: str,
                                 id_type: str, id_number: str, creator_user_id: UUID) -> Dict:
        """Create KYC record."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO kyc_records (organization_id, user_id, customer_name, customer_email,
                    id_type, id_number, verification_status, risk_level)
                VALUES ($1, $2, $3, $4, $5, $6, 'pending', 'unknown')
                RETURNING *
            """, org_id, creator_user_id, customer_name, customer_email, id_type, id_number)
            return dict(row)
    
    async def get_kyc_records(self, org_id: UUID, status: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get KYC records for organization."""
        async with self.pool.acquire() as conn:
            query = """
                SELECT * FROM kyc_records WHERE organization_id = $1
                AND ($2::text IS NULL OR verification_status = $2)
                ORDER BY created_at DESC LIMIT $3
            """
            rows = await conn.fetch(query, org_id, status, limit)
            return [dict(r) for r in rows]
    
    async def update_kyc_status(self, kyc_id: UUID, status: str, verified_by: UUID,
                                 risk_level: Optional[str] = None) -> Dict:
        """Approve/reject KYC."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                UPDATE kyc_records
                SET verification_status = $1, verified_by = $2, verified_at = $3,
                    risk_level = COALESCE($4, risk_level), updated_at = $3
                WHERE id = $5 RETURNING *
            """, status, verified_by, datetime.utcnow(), risk_level, kyc_id)
            return dict(row) if row else None
    
    # ==================== AML ====================
    
    async def create_aml_alert(self, org_id: UUID, alert_type: str, severity: str,
                                description: str, details: Dict, transaction_id: Optional[UUID] = None) -> Dict:
        """Create AML alert."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO aml_alerts (organization_id, alert_type, severity, description,
                    details, transaction_id, status)
                VALUES ($1, $2, $3, $4, $5, $6, 'open')
                RETURNING *
            """, org_id, alert_type, severity, description, details, transaction_id)
            return dict(row)
    
    async def get_aml_alerts(self, org_id: UUID, status: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get AML alerts."""
        async with self.pool.acquire() as conn:
            query = """
                SELECT * FROM aml_alerts WHERE organization_id = $1
                AND ($2::text IS NULL OR status = $2)
                ORDER BY created_at DESC LIMIT $3
            """
            rows = await conn.fetch(query, org_id, status, limit)
            return [dict(r) for r in rows]
    
    async def update_aml_alert_status(self, alert_id: UUID, status: str, resolution: Optional[str] = None,
                                       investigated_by: Optional[UUID] = None) -> Dict:
        """Resolve AML alert."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                UPDATE aml_alerts
                SET status = $1, resolution = $2, investigated_by = $3,
                    investigated_at = $4, updated_at = $4
                WHERE id = $5 RETURNING *
            """, status, resolution, investigated_by, datetime.utcnow(), alert_id)
            return dict(row) if row else None
    
    # ==================== Reports ====================
    
    async def generate_monthly_report(self, org_id: UUID, year: int, month: int, generated_by: UUID) -> Dict:
        """Auto-generate monthly compliance report."""
        async with self.pool.acquire() as conn:
            period_start = datetime(year, month, 1).date()
            if month == 12:
                period_end = datetime(year + 1, 1, 1).date()
            else:
                period_end = datetime(year, month + 1, 1).date()
            
            # Aggregate data
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) AS total_transactions,
                    COALESCE(SUM(amount), 0) AS total_volume
                FROM transactions
                WHERE organization_id = $1 AND created_at >= $2 AND created_at < $3
            """, org_id, period_start, period_end)
            
            kyc_stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) FILTER (WHERE verification_status = 'approved') AS kyc_approved,
                    COUNT(*) FILTER (WHERE verification_status = 'pending') AS kyc_pending
                FROM kyc_records WHERE organization_id = $1
            """, org_id)
            
            aml_stats = await conn.fetchrow("""
                SELECT COUNT(*) AS aml_alerts
                FROM aml_alerts WHERE organization_id = $1 AND created_at >= $2 AND created_at < $3
            """, org_id, period_start, period_end)
            
            report_data = {
                "period": {"start": str(period_start), "end": str(period_end)},
                "transactions": {"total": stats['total_transactions'], "volume": float(stats['total_volume'])},
                "kyc": {"approved": kyc_stats['kyc_approved'], "pending": kyc_stats['kyc_pending']},
                "aml": {"alerts": aml_stats['aml_alerts']}
            }
            
            row = await conn.fetchrow("""
                INSERT INTO compliance_reports (organization_id, report_type, period_start, period_end,
                    title, report_data, generated_by, status)
                VALUES ($1, 'monthly_transactions', $2, $3, $4, $5, $6, 'final')
                RETURNING *
            """, org_id, period_start, period_end, 
                f"Monthly Report {year}-{month:02d}", report_data, generated_by)
            return dict(row)
    
    async def get_reports(self, org_id: UUID, limit: int = 50) -> List[Dict]:
        """Get compliance reports."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM compliance_reports WHERE organization_id = $1
                ORDER BY period_end DESC LIMIT $2
            """, org_id, limit)
            return [dict(r) for r in rows]
    
    # ==================== Monitoring ====================
    
    async def check_transaction_against_rules(self, org_id: UUID, transaction: Dict) -> List[Dict]:
        """Check transaction against AML rules, return triggered alerts."""
        alerts = []
        async with self.pool.acquire() as conn:
            rules = await conn.fetch("""
                SELECT * FROM transaction_monitoring_rules
                WHERE (organization_id = $1 OR organization_id IS NULL) AND is_active = TRUE
            """, org_id)
            
            for rule in rules:
                triggered = False
                rule_config = rule['rule_config']
                
                if rule['rule_type'] == 'threshold':
                    threshold = rule_config.get('threshold_usd', 10000)
                    if float(transaction.get('amount', 0)) > threshold:
                        triggered = True
                
                if triggered:
                    alert = await self.create_aml_alert(
                        org_id, rule['rule_type'], rule['severity'],
                        f"Rule triggered: {rule['rule_name']}",
                        {"rule_id": str(rule['id']), "transaction": transaction},
                        UUID(str(transaction['id']))
                    )
                    alerts.append(alert)
        
        return alerts
