"""FastAPI dependency wiring.

`IntentServiceDep` is an annotated type: any handler that declares a parameter of
this type gets the singleton service from the container — no globals, and easy to
override in tests.
"""

from typing import Annotated

from fastapi import Depends, Request

from app.services.intent_service import IntentClassificationService


def get_intent_service(request: Request) -> IntentClassificationService:
    return request.app.state.container.intent_service


IntentServiceDep = Annotated[IntentClassificationService, Depends(get_intent_service)]
