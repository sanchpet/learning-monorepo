from fastapi import APIRouter

from app.api.dependencies import IntentServiceDep
from app.schemas.intent import ClassifyRequest, ClassifyResponse

router = APIRouter(tags=["intent"])


@router.post("/classify", response_model=ClassifyResponse)
async def classify(payload: ClassifyRequest, service: IntentServiceDep) -> ClassifyResponse:
    return await service.classify(payload)
