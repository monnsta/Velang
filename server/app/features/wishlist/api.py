from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.features.auth.deps import require_user
from app.features.wishlist.service import products, toggle

router = APIRouter(prefix="/api/wishlist")


@router.get("")
async def get_wishlist(user=Depends(require_user), db: AsyncSession = Depends(get_db)):
	rows = await products(db, user.id)
	return {"items": [{"id": r.id, "slug": r.slug, "name": r.name} for r in rows]}


@router.post("/{product_id}/toggle")
async def toggle_item(product_id: int, user=Depends(require_user), db: AsyncSession = Depends(get_db)):
	return {"ok": True, "added": await toggle(db, user.id, product_id)}
