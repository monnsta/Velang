from app.db.session import get_db
from app.features.content.service import site
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/content")

GET_DB = Depends(get_db)


@router.get("/site")
async def public_site(db: AsyncSession = GET_DB):
	return await site(db)
