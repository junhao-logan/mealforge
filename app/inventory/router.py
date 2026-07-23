# app/inventory/router.py
from __future__ import annotations

from fastapi import APIRouter, Depends,HTTPException

from datetime import date

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.users.models import User
from app.inventory import services
from app.inventory.schemas import InventoryItemCreate, InventoryItemRead, InventoryItemUpdate
from app.core.config import get_settings
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.post("", response_model=InventoryItemRead, status_code=201)
async def create_inventory_item(
    payload: InventoryItemCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InventoryItemRead:
    """入库一个批次。service 建 item + 流水(同事务), 这里统一 commit。"""
    item = await services.create_inventory_item(db, user.id, payload)
    await db.commit()       # ← 事务在这里落定: item + 流水 一起生效
    await db.refresh(item)  # 刷新拿 DB 生成的 created_at/updated_at 等
    return item

@router.get("", response_model=list[InventoryItemRead])
async def list_inventory(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[InventoryItemRead]:
    """列出我的库存(FEFO 序), 附带临期状态(I4, 查询时算)。"""
    items = await services.list_inventory_items(db, user.id)
    settings = get_settings()
    today = date.today()

    # ORM 对象 → Read schema, 并填入算出来的 expiry_status(非存储字段)
    return [
        InventoryItemRead.model_validate(item).model_copy(
            update={
                "expiry_status": services.compute_expiry_status(
                    item.expires_at, today, settings.inventory_expiry_warning_days
                )
            }
        )
        for item in items
    ]


@router.patch("/{item_id}", response_model=InventoryItemRead)
async def update_inventory_item(
    item_id: int,
    payload: InventoryItemUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InventoryItemRead:
    """手动修正批次(改量/补填过期日)。不记流水。"""
    item = await services.get_owned_item(db, user.id, item_id)
    if item is None:
        raise HTTPException(404, f"库存批次 id={item_id} 不存在")

    item = await services.update_inventory_item(db, item, payload)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_inventory_item(
    item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """删批次(录错/扔了一律直接删, 不记流水)。"""
    item = await services.get_owned_item(db, user.id, item_id)
    if item is None:
        raise HTTPException(404, f"库存批次 id={item_id} 不存在")

    await db.delete(item)
    await db.commit()