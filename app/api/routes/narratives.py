from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def placeholder():
    return {"detail": "narratives router alive"}
