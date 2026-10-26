from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends

from app.auth.security import Identity, identity
from app.core.errors import AppError
from app.repositories.data import Repository


@dataclass
class Workspace:
    tenant_id: UUID
    actor: Identity
    role: str
    repo: Repository

    def require_write(self):
        if self.role not in ("admin", "agent"):
            raise AppError(403, "ROLE_DENIED", "This action requires an agent or administrator.")

    def require_admin(self):
        if self.role != "admin":
            raise AppError(403, "ROLE_DENIED", "This action requires a workspace administrator.")


async def workspace(tid: UUID, actor: Identity = Depends(identity)):
    repo = Repository(actor.token)
    try:
        rows = await repo.call(
            "GET",
            "memberships",
            {
                "tenant_id": f"eq.{tid}",
                "user_id": f"eq.{actor.principal.id}",
                "is_active": "eq.true",
                "select": "role",
            },
        )
        if not rows:
            raise AppError(403, "TENANT_ACCESS_DENIED", "You do not have access to this workspace.")
        yield Workspace(tid, actor, rows[0]["role"], repo)
    finally:
        await repo.close()
