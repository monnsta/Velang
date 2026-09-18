from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.features.content.service import site

router = APIRouter(prefix="/api/content")


@router.get("/site")
async def public_site(db: AsyncSession = Depends(get_db)):
	return await site(db)
