from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def placeholder():
    return {"detail": "review_queue router alive"}
