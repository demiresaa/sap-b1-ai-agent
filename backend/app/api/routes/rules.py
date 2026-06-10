"""Onay/Fiyatlandırma kural editörü — ApprovalRule CRUD.

Admin ve manager'lar kural oluşturabilir, düzenleyebilir, devre dışı bırakabilir.
Kurallar ApprovalAgent tarafından her belge işlenirken okunur.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.api.deps import DbSession, require_roles
from app.db.base import new_uuid, utcnow
from app.db.models import UserRole
from app.db.models.approval import ApprovalAction, ApprovalRule

router = APIRouter(
    tags=["rules"],
    dependencies=[Depends(require_roles(UserRole.MANAGER, UserRole.ADMIN))],
)

VALID_FIELDS = {
    "discount_pct", "doc_total", "confidence", "item_count", "new_customer"
}
VALID_OPERATORS = {"gt", "lt", "gte", "lte", "eq", "neq"}


class RuleIn(BaseModel):
    name: str
    field: str
    operator: str
    threshold: float
    action: ApprovalAction = ApprovalAction.REQUIRE_APPROVAL
    required_role: str = "manager"
    sla_hours: int = 24
    priority: int = 100
    is_active: bool = True
    description: str | None = None


class RuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    field: str
    operator: str
    threshold: float
    action: ApprovalAction
    required_role: str
    sla_hours: int
    priority: int
    is_active: bool
    description: str | None


@router.get("", response_model=list[RuleOut])
async def list_rules(db: DbSession) -> list[RuleOut]:
    """Tüm aktif ve pasif kuralları döner (priority sıralı)."""
    result = await db.execute(
        select(ApprovalRule).order_by(ApprovalRule.priority, ApprovalRule.created_at)
    )
    return [RuleOut.model_validate(r) for r in result.scalars()]


@router.post("", response_model=RuleOut, status_code=status.HTTP_201_CREATED)
async def create_rule(body: RuleIn, db: DbSession) -> RuleOut:
    """Yeni onay kuralı oluşturur."""
    _validate_rule(body)
    now = utcnow()
    rule = ApprovalRule(
        id=new_uuid(),
        **body.model_dump(),
        created_at=now,
        updated_at=now,
    )
    db.add(rule)
    await db.flush()
    return RuleOut.model_validate(rule)


@router.get("/{rule_id}", response_model=RuleOut)
async def get_rule(rule_id: str, db: DbSession) -> RuleOut:
    rule = await _fetch_or_404(db, rule_id)
    return RuleOut.model_validate(rule)


@router.patch("/{rule_id}", response_model=RuleOut)
async def update_rule(rule_id: str, body: RuleIn, db: DbSession) -> RuleOut:
    """Kuralı günceller."""
    _validate_rule(body)
    rule = await _fetch_or_404(db, rule_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    rule.updated_at = utcnow()
    await db.flush()
    return RuleOut.model_validate(rule)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(rule_id: str, db: DbSession) -> None:
    """Kuralı siler (soft delete değil — gerçek silme)."""
    rule = await _fetch_or_404(db, rule_id)
    await db.delete(rule)
    await db.flush()


async def _fetch_or_404(db: DbSession, rule_id: str) -> ApprovalRule:
    result = await db.execute(select(ApprovalRule).where(ApprovalRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Kural bulunamadı: {rule_id}")
    return rule


def _validate_rule(body: RuleIn) -> None:
    if body.field not in VALID_FIELDS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Geçersiz field: {body.field!r}. Geçerli değerler: {sorted(VALID_FIELDS)}",
        )
    if body.operator not in VALID_OPERATORS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Geçersiz operator: {body.operator!r}. Geçerli değerler: {sorted(VALID_OPERATORS)}",
        )
    if body.required_role not in {"operator", "manager", "admin"}:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Geçersiz required_role: {body.required_role!r}",
        )
