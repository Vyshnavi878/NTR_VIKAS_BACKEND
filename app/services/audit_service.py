import csv
import io
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.internship import AuditLog
from app.schemas.audit_log import PaginatedAuditLogResponse
from app.repositories.audit_log_repository import AuditLogRepository


class AuditService:
    """Centralized service for managing and logging immutable security & administrative audit trails."""

    @classmethod
    async def get_audit_logs(
        cls,
        db: AsyncSession,
        current_admin: User,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        action: Optional[str] = None,
        result: Optional[str] = None,
    ) -> PaginatedAuditLogResponse:
        """Fetch paginated audit log entries with authorization enforcement."""
        if current_admin.role not in ["ADMIN", "PLATFORM_ADMINISTRATOR", "Platform Administrator", "Super Admin", "SUPER_ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Platform Administrator authorization required to view security audit logs.",
            )

        items, total = await AuditLogRepository.get_audit_logs(
            db=db,
            page=page,
            page_size=page_size,
            search=search,
            action=action,
            result=result,
        )

        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        return PaginatedAuditLogResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @classmethod
    async def export_audit_csv(
        cls,
        db: AsyncSession,
        current_admin: User,
        search: Optional[str] = None,
        action: Optional[str] = None,
        result: Optional[str] = None,
    ) -> str:
        """Generate CSV string containing audit log records for export."""
        if current_admin.role not in ["ADMIN", "PLATFORM_ADMINISTRATOR", "Platform Administrator", "Super Admin", "SUPER_ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Platform Administrator authorization required to export audit logs.",
            )

        logs = await AuditLogRepository.get_all_for_export(
            db=db,
            search=search,
            action=action,
            result=result,
        )

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        # Write Header matching UI table specification
        writer.writerow(["Action", "Admin / User", "Target", "Date", "Time", "Result"])

        for log in logs:
            writer.writerow([
                log.action,
                log.admin or log.actor,
                log.target or log.entity or "System",
                log.date,
                log.time,
                log.result,
            ])

        return output.getvalue()

    @classmethod
    async def log_event(
        cls,
        db: AsyncSession,
        actor: str,
        action: str,
        entity: str,
        entity_id: str = "SYSTEM",
        target_name: Optional[str] = None,
        result: str = "SUCCESS",
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """Convenience method to record an audit log event from any module."""
        return await AuditLogRepository.create_log(
            db=db,
            actor=actor,
            action=action,
            entity=entity,
            entity_id=entity_id,
            target_name=target_name,
            result=result,
            metadata=metadata,
            ip_address=ip_address,
            user_agent=user_agent,
        )
